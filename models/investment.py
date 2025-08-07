from dateutil.relativedelta import relativedelta
from datetime import timedelta, date
from odoo import models, fields, api, _
from .base_model import AmanatBaseModel
from collections import defaultdict
from odoo.exceptions import UserError
import logging
import pytz
from datetime import datetime

_logger = logging.getLogger(__name__)

class Investment(models.Model, AmanatBaseModel):
    _name = 'amanat.investment'
    _description = 'Инвестиции'
    _inherit = ['amanat.base.model', 'mail.thread', 'mail.activity.mixin']

    # Основные данные
    name = fields.Char(
        string='ID', readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('amanat.investment.sequence')
    )
    status = fields.Selection([
        ('open', 'Открыта'),
        ('close', 'Закрыта'),
        ('archive', 'Архив')
    ], string='Статус', default='open', tracking=True)

    date = fields.Date(string='Дата', default=fields.Date.today, tracking=True)

    date_close = fields.Date(string='Дата закрытия', tracking=True)

    sender = fields.Many2one('amanat.contragent', string='Отправитель', tracking=True)
    payer_sender = fields.Many2one(
        'amanat.payer', string='Плательщик отправитель', tracking=True,
        domain="[('contragents_ids','in',sender)]"
    )
    receiver = fields.Many2one('amanat.contragent', string='Получатель', tracking=True)
    payer_receiver = fields.Many2one(
        'amanat.payer', string='Плательщик получатель', tracking=True,
        domain="[('contragents_ids','in',receiver)]"
    )

    percent = fields.Float(string='Процент', default=0.0, tracking=True)
    fixed_amount = fields.Float(string='Фикс сумма', tracking=True)
    period = fields.Selection([
        ('calendar_day', 'Календарный день'),
        ('calendar_month', 'Календарный месяц'),
        ('calendar_year', 'Календарный год'),
        ('work_day', 'Рабочий день'),
    ], string='Период', tracking=True)

    amount = fields.Float(string='Сумма', tracking=True)
    currency = fields.Selection([
        ('RUB', 'RUB'), ('RUB_cash', 'RUB КЭШ'),
        ('USD', 'USD'), ('USD_cash', 'USD КЭШ'),
        ('USDT', 'USDT'),
        ('EURO', 'EURO'), ('EURO_cash', 'EURO КЭШ'),
        ('CNY', 'CNY'), ('CNY_cash', 'CNY КЭШ'),
        ('AED', 'AED'), ('AED_cash', 'AED КЭШ'),
        ('THB', 'THB'), ('THB_cash', 'THB КЭШ'),
    ], string='Валюта', tracking=True)

    # комментарий
    comment = fields.Text(string='Комментарий', tracking=True)

    # Флаги автоматизации
    create_action = fields.Boolean(string='Создать', tracking=True)
    to_delete = fields.Boolean(string='Удалить', tracking=True)
    post = fields.Boolean(string='Провести', tracking=True)
    # repost = fields.Boolean(string='Перепровести', tracking=True)
    close_investment = fields.Boolean(string='Закрытие инвестиций', tracking=True)
    accrue = fields.Boolean(string='Начислить', tracking=True) 

    # Роялти
    has_royalty = fields.Boolean(string='Есть роялти?', tracking=True)
    royalty_post = fields.Boolean(string='Создать роялти', tracking=True)
    royalty_recipient_1 = fields.Many2one('amanat.contragent', string='Получатель роялти 1', tracking=True)
    royalty_recipient_2 = fields.Many2one('amanat.contragent', string='Получатель роялти 2', tracking=True)
    royalty_recipient_3 = fields.Many2one('amanat.contragent', string='Получатель роялти 3', tracking=True)
    royalty_recipient_4 = fields.Many2one('amanat.contragent', string='Получатель роялти 4', tracking=True)
    royalty_recipient_5 = fields.Many2one('amanat.contragent', string='Получатель роялти 5', tracking=True)

    percent_1 = fields.Float(string='Процент роялти 1', tracking=True, digits=(16, 8))
    percent_2 = fields.Float(string='Процент роялти 2', tracking=True, digits=(16, 8))
    percent_3 = fields.Float(string='Процент роялти 3', tracking=True, digits=(16, 8))
    percent_4 = fields.Float(string='Процент роялти 4', tracking=True, digits=(16, 8))
    percent_5 = fields.Float(string='Процент роялти 5', tracking=True, digits=(16, 8))

    # Отношения
    orders = fields.Many2many('amanat.order', 'amanat_order_investment_rel', 'investment_id', 'order_id', string='Ордеры', tracking=True)
    write_offs = fields.Many2many('amanat.writeoff', 'amanat_investment_writeoff_rel', 'investment_id', 'writeoff_id', string='Списания', tracking=True)
    # Новое вычисляемое поле для предпросмотра первых 10 списаний
    write_offs_preview = fields.Many2many(
        'amanat.writeoff',
        compute='_compute_write_offs_preview',
        string='Списания (первые 10)',
        store=False
    )

    # Вычисляемые поля
    principal = fields.Float(
        string='Тело долга', 
        compute='_compute_principal', 
        store=True, 
        tracking=True,
        readonly=False,
    )
    calendar_days = fields.Integer(
        string='Календарных дней',
        compute='_compute_calendar_and_work_days',
        store=False,
        tracking=True,
        readonly=False,
    )
    work_days = fields.Integer(
        string='Рабочих дней',
        compute='_compute_calendar_and_work_days',
        store=False,
        tracking=True,
        readonly=False,
    )
    today_date = fields.Date(
        string='Дата сегодня',
        compute='_compute_calendar_and_work_days',
        store=False,
        tracking=True,
        readonly=False,
    )
    rollup_write_offs = fields.Float(
        string='Роллап списания', 
        compute='_compute_rollup_write_offs', 
        store=True, 
        tracking=True,
        readonly=False,
    )
    rollup_amount = fields.Float(string='Сумма роллап списания', tracking=True)
    rollup_amount_total = fields.Float(string='Сумма RollUp (from Погасить)', tracking=True)

    royalty_amount_1 = fields.Float(string='Сумма роялти 1', compute='_compute_royalty_amounts', digits=(16, 6), store=True, tracking=True, readonly=False)
    royalty_amount_2 = fields.Float(string='Сумма роялти 2', compute='_compute_royalty_amounts', digits=(16, 6), store=True, tracking=True, readonly=False)
    royalty_amount_3 = fields.Float(string='Сумма роялти 3', compute='_compute_royalty_amounts', digits=(16, 6), store=True, tracking=True, readonly=False)
    royalty_amount_4 = fields.Float(string='Сумма роялти 4', compute='_compute_royalty_amounts', digits=(16, 6), store=True, tracking=True, readonly=False)
    royalty_amount_5 = fields.Float(string='Сумма роялти 5', compute='_compute_royalty_amounts', digits=(16, 6), store=True, tracking=True, readonly=False)

    @api.onchange('sender')
    def _onchange_sender(self):
        """Автоматически подтягивает плательщика отправителя при выборе отправителя"""
        if self.sender:
            # Ищем плательщика, связанного с отправителем
            payer = self.env['amanat.payer'].search([
                ('contragents_ids', 'in', self.sender.id)
            ], limit=1)
            if payer:
                self.payer_sender = payer
            else:
                self.payer_sender = False
        else:
            self.payer_sender = False

    @api.onchange('receiver')
    def _onchange_receiver(self):
        """Автоматически подтягивает плательщика получателя при выборе получателя"""
        if self.receiver:
            # Ищем плательщика, связанного с получателем
            payer = self.env['amanat.payer'].search([
                ('contragents_ids', 'in', self.receiver.id)
            ], limit=1)
            if payer:
                self.payer_receiver = payer
            else:
                self.payer_receiver = False
        else:
            self.payer_receiver = False

    def action_create_writeoff(self):
        self.ensure_one()
        return {
            "name": _("Списание по инвестиции"),
            "type": "ir.actions.act_window",
            "res_model": "amanat.writeoff",
            "view_mode": "form",
            "target": "current",
            "context": dict(self.env.context, **{
                "default_investment_ids": [self.id],
                "default_writeoff_investment": True,
            }),
        }

    @api.depends('amount', 'rollup_write_offs')
    def _compute_principal(self):
        for rec in self:
            rec.principal = (rec.amount or 0.0) - (rec.rollup_write_offs or 0.0)

    def _group_by_month(writeoffs):
        monthly = defaultdict(list)
        for w in writeoffs:
            if isinstance(w.date, str):
                date_obj = fields.Date.from_string(w.date)
            else:
                date_obj = w.date
            key = (date_obj.year, date_obj.month)
            monthly[key].append(w)
        return monthly

    def _get_currency_fields(self, currency, amount):
        mapping = {
            'RUB': 'rub',       'RUB_cash': 'rub_cash',
            'USD': 'usd',       'USD_cash': 'usd_cash',
            'USDT': 'usdt',     'EURO': 'euro',      'EURO_cash': 'euro_cash',
            'CNY': 'cny',       'CNY_cash': 'cny_cash',
            'AED': 'aed',       'AED_cash': 'aed_cash',
            'THB': 'thb',       'THB_cash': 'thb_cash',
        }
        code = mapping.get(currency, 'rub')
        return {f'sum_{code}': amount}

    @api.depends('date')
    def _compute_calendar_and_work_days(self):
        for rec in self:
            today = fields.Date.context_today(self)
            if rec.date:
                days = (today - rec.date).days + 1
                wd = 0
                for i in range(days):
                    d = rec.date + timedelta(days=i)
                    holidays = self.get_holidays(d.year)
                    if d.weekday() < 5 and d not in holidays:
                        wd += 1
                rec.calendar_days = days
                rec.work_days = wd
            else:
                rec.calendar_days = rec.work_days = 0
            rec.today_date = today

    @api.depends('orders.rollup_write_off')
    def _compute_rollup_write_offs(self):
        for rec in self:
            # Суммируем rollup_write_off всех связанных ордеров (как rollup в Airtable)
            rec.rollup_write_offs = sum(
                float(o.rollup_write_off or 0.0) for o in rec.orders
            )

    @api.depends('amount', 'percent_1', 'percent_2', 'percent_3', 'percent_4', 'percent_5')
    def _compute_royalty_amounts(self):
        for rec in self:
            # Суммы роялти считаем как процент от суммы (делим на 100)
            rec.royalty_amount_1 = (rec.amount or 0.0) * (rec.percent_1 or 0.0) / 100.0
            rec.royalty_amount_2 = (rec.amount or 0.0) * (rec.percent_2 or 0.0) / 100.0
            rec.royalty_amount_3 = (rec.amount or 0.0) * (rec.percent_3 or 0.0) / 100.0
            rec.royalty_amount_4 = (rec.amount or 0.0) * (rec.percent_4 or 0.0) / 100.0
            rec.royalty_amount_5 = (rec.amount or 0.0) * (rec.percent_5 or 0.0) / 100.0

    def action_create_writeoffs(self):
        """
        Создаём помесячные списания по principal только за полностью прошедшие месяцы.
        Удаляем предыдущие записи principal и создаём новые для каждого месяца до текущего.
        """
        Writeoff = self.env['amanat.writeoff']
        for inv in self:
            # --- 1) Удаляем старые списания principal (не проценты/роялти) ---
            old_principals = inv.write_offs.filtered(
                lambda w: not w.money_id.percent and not w.money_id.royalty
            )
            if old_principals:
                Writeoff.browse(old_principals.ids).unlink()

            # --- 2) Запускаем цикл от месяца запуска до начала текущего ---
            if not inv.date:
                continue
            # начало месяца инвестирования
            cur_date = inv.date.replace(day=1)
            # начало текущего месяца (по test_date или today)
            today = fields.Date.context_today(self)
            current_month_start = today.replace(day=1)

            while cur_date <= current_month_start:
                for order in inv.orders:
                    # только principal-контейнеры
                    principal_conts = order.money_ids.filtered(
                        lambda m: not m.percent and not m.royalty
                    )
                    for money in principal_conts:
                        Writeoff.create({
                            'date': cur_date,
                            'amount': money.amount,
                            'money_id': money.id,
                            'investment_ids': [(4, inv.id)],
                        })
                cur_date += relativedelta(months=1)


    
    def action_post(self):
        for inv in self:
            # 1) Синхронизируем ордер и контейнеры
            # inv.action_sync_airtable()
            # 2) Создаём principal-списания
            # inv.action_create_writeoffs()
            # 3) Создаём записи сверки
            inv.action_sync_reconciliation()
            # 4) Сбрасываем флаг
            inv.post = False
        return True


    def parse_date_from_string(self, date_str):
        """Парсим дату формата dd.mm.yyyy в datetime.date или возвращаем None"""
        if not isinstance(date_str, str):
            _logger.debug(f"parse_date_from_string: дата не строка: {date_str}")
            return None
        parts = date_str.split('.')
        if len(parts) != 3:
            _logger.debug(f"parse_date_from_string: неправильный формат даты: {date_str}")
            return None
        try:
            day, month, year = map(int, parts)
            dt = fields.Date.to_date(f'{year:04d}-{month:02d}-{day:02d}')
            return dt
        except Exception:
            _logger.debug(f"parse_date_from_string: не удалось распарсить: {date_str}")
            return None

    def days_between(self, d1, d2):
        if not d1 or not d2:
            return 0
        return (d2 - d1).days

    def is_same_day(self, d1, d2):
        if not d1 or not d2:
            return False
        return d1 == d2

    def get_period_days(self, period_name, start_date):
        if not start_date:
            return 1
        d = start_date
        if period_name == "Календарный день":
            return 1
        elif period_name == "Календарный месяц":
            nxt = (d + relativedelta(months=1))
            # корреткция дня в месяце
            day = min(d.day, (nxt - relativedelta(days=nxt.day)).day)
            nxt_corrected = d.replace(day=day) + relativedelta(months=1)
            return (nxt_corrected - d).days
        elif period_name == "Календарный год":
            nxt_year = d.replace(year=d.year+1)
            # Корректируем к дню месяца
            while nxt_year.month != d.month:
                nxt_year -= timedelta(days=1)
            return (nxt_year - d).days
        elif period_name == "Рабочий день":
            return 1
        else:
            return 1

    def get_month_days(self, date):
        # Количество дней в месяце date
        y = date.year
        m = date.month
        nxt_month = m + 1 if m < 12 else 1
        nxt_year = y if m < 12 else y + 1
        first_next = fields.Date.to_date(f'{nxt_year}-{nxt_month:02d}-01')
        last_day = first_next - timedelta(days=1)
        return last_day.day

    def _batch_create_writeoffs(self, writeoffs_vals):
        """Создаём writeoffs пакетно, партиями по 50"""
        Writeoff = self.env['amanat.writeoff']
        chunk_size = 50
        for i in range(0, len(writeoffs_vals), chunk_size):
            chunk = writeoffs_vals[i:i + chunk_size]
            Writeoff.create(chunk)

    @staticmethod
    def _days_between(d1, d2):
        return (d2 - d1).days if d1 and d2 else 0

    @staticmethod
    def _get_period_days(period, start_date):
        if not start_date:
            return 1
        if period == 'calendar_day':
            return 1
        if period == 'calendar_month':
            nxt = start_date + relativedelta(months=1)
            return (nxt - start_date).days
        if period == 'calendar_year':
            nxt = start_date + relativedelta(years=1)
            return (nxt - start_date).days
        return 1  # work_day == 1

    def _get_month_days(self, d):
        nxt = d + relativedelta(months=1)
        return (date(nxt.year, nxt.month, 1) - date(d.year, d.month, 1)).days
    
    def action_sync_reconciliation(self):
        """
        Полная реализация автоматизации сверки на уровне Odoo,
        аналог скрипта в Airtable:
        1) Удаляем старые записи сверки по первому ордеру.
        2) Получаем контейнеры money и связанные writeoff'ы.
        3) Для principal-контейнеров создаем одну запись на дату инвестирования.
        4) Для процентных/роялти-контейнеров группируем списания по месяцам
           и создаем записи сверки по последней дате в месяце.
        """
        Reconciliation = self.env['amanat.reconciliation']
        Writeoff = self.env['amanat.writeoff']
        Money = self.env['amanat.money']
        Payer = self.env['amanat.payer']
        Wallet = self.env['amanat.wallet']
        Contr = self.env['amanat.contragent']

        wallet = Wallet.search([('name', '=', 'Инвестиции')], limit=1)
        if not wallet:
            raise UserError(_('Кошелёк "Инвестиции" не найден'))

        royal_payer = Payer.search([('name', '=', 'Роялти')], limit=1)
        if not royal_payer:
            royal_payer = Payer.create({'name': 'Роялти'})
        royal_partner = Contr.search([('name', '=', 'Роялти')], limit=1)
        if not royal_partner:
            royal_partner = Contr.create({'name': 'Роялти'})

        for inv in self:
            if not inv.orders:
                continue
            order = inv.orders[0]

            # 1) Удалить старые записи сверки
            Reconciliation.search([('order_id', 'in', order.id)]).unlink()

            # 2) Собираем контейнеры и writeoff-ы
            containers = order.money_ids
            monthly = defaultdict(lambda: {'amount': 0.0, 'last_date': False, 'cont_id': False})

            for cont in containers:
                if cont.percent or cont.royalty:
                    for wf in Writeoff.browse(cont.writeoff_ids.ids):
                        key = (wf.date.year, wf.date.month, cont.id)
                        monthly[key]['amount'] += wf.amount
                        if not monthly[key]['last_date'] or wf.date > monthly[key]['last_date']:
                            monthly[key]['last_date'] = wf.date
                            monthly[key]['cont_id'] = cont.id

            # 3) Создаем записи по процентам и роялти
            for (y, m, cont_id), data in sorted(monthly.items()):
                total = data['amount']
                if not total:
                    continue
                last_date = data['last_date']
                cont = Money.browse(cont_id)
                inv_currency = inv.currency.lower()
                # ПРОЦЕНТНЫЕ
                if cont.percent:
                    vals = {
                        'date': last_date,
                        'partner_id': cont.partner_id.id,
                        'currency': inv_currency,
                        'sum': -total,
                        f'sum_{inv_currency}': -total,
                        'wallet_id': wallet.id,
                        'order_id': [(4, order.id)],
                        'sender_id': [(4, inv.payer_sender.id)] if inv.payer_sender else False,
                        'receiver_id': [(4, inv.payer_receiver.id)] if inv.payer_receiver else False,
                    }
                    Reconciliation.create(vals)
                # РОЯЛТИ — только 1 запись: отправитель=Роялти, получатель=контрагент получателя роялти
                elif cont.royalty:
                    # Найти payer для получателя роялти
                    payer_receiver = Payer.search([('contragents_ids', 'in', cont.partner_id.id)], limit=1)
                    vals = {
                        'date': last_date,
                        'partner_id': cont.partner_id.id,  # Получатель роялти (человек)
                        'currency': inv_currency,
                        'sum': -total,
                        f'sum_{inv_currency}': -total,
                        'wallet_id': wallet.id,
                        'order_id': [(4, order.id)],
                        'sender_id': [(4, royal_payer.id)],
                        'receiver_id': [(4, payer_receiver.id)] if payer_receiver else False,
                    }
                    Reconciliation.create(vals)

            # 4) Обработка principal-контейнеров
            for cont in containers.filtered(lambda m: not m.percent and not m.royalty):
                Reconciliation.create({
                    'date': inv.date,
                    'partner_id': cont.partner_id.id,
                    'currency': inv.currency.lower(),
                    'sum': cont.amount,
                    f'sum_{inv.currency.lower()}': cont.amount,
                    'wallet_id': wallet.id,
                    'order_id': [(4, order.id)],
                    'sender_id': [(4, inv.payer_sender.id)] if inv.payer_sender else False,
                    'receiver_id': [(4, inv.payer_receiver.id)] if inv.payer_receiver else False,
                })
        return True


    def action_sync_airtable(self):
        Money = self.env['amanat.money']
        Order = self.env['amanat.order']
        Writeoff = self.env['amanat.writeoff']
        Reconc = self.env['amanat.reconciliation']
        Wallet = self.env['amanat.wallet']
        Payer = self.env['amanat.payer']

        # Найти кошелек "Инвестиции"
        wallet = Wallet.search([('name', '=', 'Инвестиции')], limit=1)
        if not wallet:
            raise UserError(_('Кошелёк "Инвестиции" не найден'))

        # Маппинг валют
        mapping = {
            'RUB': 'rub', 'RUB_cash': 'rub_cash',
            'USD': 'usd', 'USD_cash': 'usd_cash',
            'USDT': 'usdt',
            'EURO': 'euro', 'EURO_cash': 'euro_cash',
            'CNY': 'cny', 'CNY_cash': 'cny_cash',
            'AED': 'aed', 'AED_cash': 'aed_cash',
            'THB': 'thb', 'THB_cash': 'thb_cash',
        }

        # Плательщик и контрагент "Роялти"
        royal_payer = Payer.search([('name', '=', 'Роялти')], limit=1)
        if not royal_payer:
            royal_payer = Payer.create({'name': 'Роялти'})
        royal_partner = self.env['amanat.contragent'].search([('name', '=', 'Роялти')], limit=1)
        if not royal_partner:
            royal_partner = self.env['amanat.contragent'].create({'name': 'Роялти'})
        if royal_partner.id not in royal_payer.contragents_ids.ids:
            royal_payer.write({'contragents_ids': [(4, royal_partner.id)]})

        for inv in self:
            # 1) Удаление старых ордеров и всё связанное
            for ord in inv.orders:
                Reconc.search([('order_id', '=', ord.id)]).unlink()
                ord.money_ids.unlink()
                ord.unlink()
            inv.orders = [(5, 0, 0)]  # Очистка many2many

            # забираем словарь вариантов поля period
            period_selection = dict(inv.fields_get(['period'])['period']['selection'])
            # получаем человекочитаемый текст
            period_label = period_selection.get(inv.period, inv.period)

            # 2) Создание нового ордера
            # Формируем комментарий: автоматический + комментарий из поля
            auto_comment = _('Сделка Инвестиция %s %s%%') % (period_label or '', inv.percent * 100)
            
            # Объединяем комментарии согласно требованиям
            if inv.comment:
                final_comment = _('Инвестиция: %s; %s') % (auto_comment, inv.comment)
            else:
                final_comment = _('Инвестиция: %s') % auto_comment
            
            order_vals = {
                'date': inv.date,
                'type': 'transfer',  # предполагается, что есть тип 'transfer'
                'partner_1_id': inv.sender.id,
                'partner_2_id': inv.receiver.id,
                'currency': mapping.get(inv.currency),
                'amount': inv.amount,
                'wallet_1_id': wallet.id,
                'wallet_2_id': wallet.id,
                'comment': final_comment,
            }
            # Плательщики (если есть), выбираем первый подходящий
            payer_1 = Payer.search([('contragents_ids', 'in', inv.sender.id)], limit=1)
            payer_2 = Payer.search([('contragents_ids', 'in', inv.receiver.id)], limit=1)
            if payer_1:
                order_vals['payer_1_id'] = payer_1.id
            if payer_2:
                order_vals['payer_2_id'] = payer_2.id

            new_ord = Order.create(order_vals)
            inv.orders = [(4, new_ord.id)]

            # 3) Функция для создания контейнеров
            def mk(holder, amt, debt=False, perc=False, roy=False, state=None):
                data = {
                    'date': inv.date,
                    'wallet_id': wallet.id,
                    'partner_id': holder.id,
                    'currency': mapping.get(inv.currency),
                    'amount': amt,
                    'state': state if state is not None else ('debt' if debt else 'positive'),
                    'percent': perc,
                    'royalty': roy,
                    'order_id': new_ord.id,
                }
                code = mapping.get(inv.currency)
                if code:
                    data[f'sum_{code}'] = amt
                    data[f'remains_{code}'] = amt
                data['remains'] = amt
                return Money.create(data)

            # 4) Создаем контейнеры: долг и положительный контейнер
            mk(inv.sender, -inv.amount, debt=True)
            mk(inv.receiver, inv.amount)

            # 5) Создаем процентные или фиксированные контейнеры
            if inv.create_action:
                mk(inv.sender,  0.0, perc=True, state='empty')
                mk(inv.receiver, 0.0, perc=True, state='empty')
            else:
                if inv.percent > 0:
                    mk(inv.sender, -inv.amount * inv.percent, debt=True, perc=True)
                    mk(inv.receiver,  inv.amount * inv.percent,      perc=True)
                elif inv.fixed_amount > 0:
                    mk(inv.sender, -inv.fixed_amount, debt=True, perc=True)
                    mk(inv.receiver, inv.fixed_amount,              perc=True)
                # иначе не создаём проценты/фикс вовсе

            # 7) Создаем помесячные списания и сверки — вызываем ваши методы
            # inv.action_create_writeoffs()
            inv.action_sync_reconciliation()

            # 7.1) Создаём роялти-контейнеры, если есть хотя бы один получатель
            inv.action_create_royalty_containers()

            # 8) Создаем записи сверки по месяцам для процентных и роялти контейнеров
            cur = inv.date.replace(day=1)
            today = fields.Date.context_today(self)
            while cur <= today:
                end = (cur + relativedelta(months=1, day=1)) - timedelta(days=1)
                if cur.month == today.month and cur.year == today.year:
                    end = today
                for cont in new_ord.money_ids.filtered(lambda m: m.percent or m.royalty):
                    total = sum(Writeoff.search([('id', 'in', cont.writeoff_ids.ids), ('date', '>=', cur), ('date', '<=', end)]).mapped('amount'))
                    if total == 0:
                        continue
                    recon_vals = {
                        'date': end,
                        'partner_id': cont.partner_id.id,
                        'currency': mapping.get(inv.currency),
                        'sum': total,
                        f"sum_{mapping.get(inv.currency)}": total,
                        'wallet_id': wallet.id,
                        'order_id': [(4, new_ord.id)],
                    }
                    if cont.royalty:
                        recon_vals['sender_id'] = [(4, royal_payer.id)]
                        recon_vals['sender_contragent'] = [(4, royal_partner.id)]
                    else:
                        if inv.payer_sender:
                            recon_vals['sender_id'] = [(4, inv.payer_sender.id)]
                        recon_vals['sender_contragent'] = [(4, inv.sender.id)]
                        pay_rec = Payer.search([('contragents_ids', 'in', cont.partner_id.id)], limit=1)
                        if pay_rec:
                            recon_vals['receiver_id'] = [(4, pay_rec.id)]
                        recon_vals['receiver_contragent'] = [(4, cont.partner_id.id)]
                    Reconc.create(recon_vals)
                cur += relativedelta(months=1)
            return True


    def action_delete(self):
        # Money = self.env['amanat.money'] 
        # Order = self.env['amanat.order']
        Writeoff = self.env['amanat.writeoff'] 
        Reconc = self.env['amanat.reconciliation']
        for inv in self:
            for ord in inv.orders:
                Reconc.search([('order_id','in',ord.id)]).unlink()
                for c in ord.money_ids:
                    Writeoff.search([('id','in',c.writeoff_ids.ids)]).unlink()
                ord.money_ids.unlink()
                ord.unlink()
            inv.orders=[(5,0,0)] 
            inv.status='archive'
            inv.to_delete=False
        return True

    def action_close_investment(self):
        """Закрытие инвестиции: создание списаний по первому ордеру и долговых контейнеров."""
        Writeoff = self.env['amanat.writeoff']
        Money = self.env['amanat.money']

        for inv in self:
            # 1) Пропускаем уже закрытые
            if inv.status == 'close':
                _logger.info("Инвестиция %s уже закрыта, пропускаем", inv.id)
                continue

            # 2) Меняем статус и дату закрытия
            inv.status = 'close'
            inv.date_close = fields.Date.context_today(self)

            # 3) Берём только первый связанный ордер 
            if not inv.orders:
                _logger.warning("Инвестиция %s не имеет ордеров для закрытия", inv.id)
                continue
            linked_order = inv.orders[0]

            # 4) Для каждого контейнера денег в ордере
            for money in linked_order.money_ids:
                initial = money.amount or 0.0
                if not initial: 
                    continue
                
                # а) основное списание
                Writeoff.create({
                    'date':        inv.date_close or inv.date,
                    'amount':      initial,
                    'money_id':    money.id,
                    'investment_ids': [(4, inv.id)],
                })
                _logger.info("Создали списание %s для контейнера %s", initial, money.id)
                
                # б) проверяем остаток
                used = sum(w.amount for w in money.writeoff_ids)
                new_remains = (money.amount or 0.0) - used
                if new_remains < 0:
                    # создаём долговой контейнер
                    debt = new_remains
                    Money.create({
                        'date':       inv.date_close or inv.date,
                        'state':      'debt',
                        'partner_id': money.partner_id.id,
                        'currency':   money.currency,
                        'amount':     debt,
                        'sum':        debt,
                        'wallet_id':  money.wallet_id.id,
                        'order_id':   linked_order.id,
                    })
                    _logger.info("Создан контейнер-долг %s, сумма %s", money.id, debt)

                    # дополнительное списание, чтобы привести основной контейнер к нулю
                    Writeoff.create({
                        'date':        inv.date_close or inv.date,
                        'amount':      debt,
                        'money_id':    money.id,
                        'investment_ids': [(4, inv.id)],
                    })
                    _logger.info("Доп. списание %s для контейнера %s", debt, money.id)

            # 5) сбрасываем флаг
            inv.close_investment = False


        return True

    def action_create_royalty_containers(self):
        Money = self.env['amanat.money']
        Wallet = self.env['amanat.wallet'].search(
            [('name', '=', 'Инвестиции')], limit=1)
        if not Wallet:
            raise UserError(_('Кошелёк "Инвестиции" не найден'))

        for inv in self:
            # Проверяем, есть ли хотя бы один реально заполненный получатель роялти
            has_any_recipient = any(
                getattr(inv, f'royalty_recipient_{i}', False) and hasattr(getattr(inv, f'royalty_recipient_{i}'), 'id') and getattr(inv, f'royalty_recipient_{i}').id and (getattr(inv, f'percent_{i}', 0.0) or 0.0) > 0
                for i in range(1, 10)
            )
            if not has_any_recipient:
                continue
            # берём первый ордер, если их несколько
            order = inv.orders and inv.orders[0] or None
            for i in range(1, 10):
                recv = getattr(inv, f'royalty_recipient_{i}', False)
                pct  = getattr(inv, f'percent_{i}', 0.0) or 0.0
                # Проверяем, что получатель реально выбран и процент > 0
                if not recv or not hasattr(recv, 'id') or not recv.id or pct <= 0:
                    continue
                # соберём поля валют
                currency_vals = inv._get_currency_fields(inv.currency, 0.0)
                vals = {
                    'date':        inv.date,
                    'state':       'debt',
                    'partner_id':  recv.id,
                    'currency':    inv.currency.lower(),
                    'amount':      inv.amount * pct / 100.0,
                    'wallet_id':   Wallet.id,
                    'royalty':     True,
                    **currency_vals,
                }
                if order and hasattr(order, 'id'):
                    vals['order_id'] = order.id
                Money.create(vals)
        return True
    

    @staticmethod
    def get_holidays(year):
        """Возвращает set с праздничными и дополнительными выходными днями для заданного года, учитывая переносы для 2025 года"""
        holidays = {
            date(year, 1, 1), date(year, 1, 2), date(year, 1, 3), date(year, 1, 4), date(year, 1, 5),
            date(year, 1, 6), date(year, 1, 7), date(year, 1, 8), date(year, 2, 23), date(year, 3, 8),
            date(year, 5, 1), date(year, 5, 9), date(year, 6, 12), date(year, 11, 4)
        }
        # Для 2025 года учитываем переносы
        if year == 2025:
            # Исключаем 4 и 5 января из праздников (они рабочие)
            holidays.discard(date(2025, 1, 4))
            holidays.discard(date(2025, 1, 5))
            # Добавляем дополнительные выходные по переносам
            holidays.update({
                date(2025, 5, 2),   # пятница
                date(2025, 12, 31), # среда
                date(2025, 5, 8),   # четверг
                date(2025, 6, 13),  # пятница
                date(2025, 11, 3),  # понедельник
            })
        return holidays

    def write(self, vals):
        # Автоматически обновляем плательщиков при изменении отправителя/получателя
        if 'sender' in vals and not vals.get('payer_sender'):
            if vals['sender']:
                payer = self.env['amanat.payer'].search([
                    ('contragents_ids', 'in', vals['sender'])
                ], limit=1)
                if payer:
                    vals['payer_sender'] = payer.id
            else:
                vals['payer_sender'] = False
        
        if 'receiver' in vals and not vals.get('payer_receiver'):
            if vals['receiver']:
                payer = self.env['amanat.payer'].search([
                    ('contragents_ids', 'in', vals['receiver'])
                ], limit=1)
                if payer:
                    vals['payer_receiver'] = payer.id
            else:
                vals['payer_receiver'] = False
        
        res = super().write(vals)
        if vals.get('create_action'):
            for r in self.filtered('create_action'):
                r.action_sync_airtable()
                r.action_sync_reconciliation()
                r.create_action = False
        if vals.get('to_delete'):
            for r in self.filtered('to_delete'):
                r.action_delete()
        if vals.get('post'):
            for r in self.filtered('post'):
                r.action_post()
        if vals.get('close_investment'):
            for r in self.filtered('close_investment'):
                r.action_close_investment()
        if vals.get('accrue', False):
            for inv in self.filtered(lambda r: r.accrue):
                inv.accrue_interest()
                inv.accrue = False  # Сбрасываем флаг после выполнения
        return res

    @api.model
    def create(self, vals):
        # Автоматически подтягиваем плательщиков при создании
        if vals.get('sender') and not vals.get('payer_sender'):
            payer = self.env['amanat.payer'].search([
                ('contragents_ids', 'in', vals['sender'])
            ], limit=1)
            if payer:
                vals['payer_sender'] = payer.id
        
        if vals.get('receiver') and not vals.get('payer_receiver'):
            payer = self.env['amanat.payer'].search([
                ('contragents_ids', 'in', vals['receiver'])
            ], limit=1)
            if payer:
                vals['payer_receiver'] = payer.id
        
        rec = super().create(vals)
        if rec.create_action:
            rec.action_sync_airtable()
            rec.action_sync_reconciliation()
            rec.create_action = False
        if rec.to_delete:
            rec.action_delete()
        if rec.close_investment:
            rec.action_close_investment()
        if vals.get('accrue', False):
            rec.accrue_interest()
            rec.accrue = False
        return rec

    @api.model
    def _cron_accrue_interest(self):
        """Cron: ежедневный запуск начисления"""
        self.search([('status', '=', 'open')]).accrue_interest()
        return True

    def accrue_interest(self):
        """Ежедневное начисление процентов и роялти по открытым инвестициям"""
        Money = self.env['amanat.money']
        Writeoff = self.env['amanat.writeoff']
        today = fields.Date.context_today(self)
        
        # Получаем текущее время по Москве
        moscow_tz = pytz.timezone('Europe/Moscow')
        moscow_time = datetime.now(moscow_tz)
        moscow_hour = moscow_time.hour
        
        # Определяем дату для начисления: если время до 20:00, то не начисляем на сегодня
        accrual_date = today
        if moscow_hour < 20:
            # Если время до 20:00, начисляем до вчерашнего дня включительно
            accrual_date = today - timedelta(days=1)
        
        _logger.info(f"🕐 Время по Москве: {moscow_time.strftime('%H:%M:%S')} (час: {moscow_hour})")
        _logger.info(f"📅 Дата начисления: {accrual_date} (сегодня: {today})")
        
        HOLIDAYS = {
            date(2024,1,1), date(2024,1,2), date(2024,1,3), date(2024,1,4), date(2024,1,5),
            date(2024,1,6), date(2024,1,7), date(2024,1,8), date(2024,2,23), date(2024,3,8),
            date(2024,5,1), date(2024,5,9), date(2024,6,12), date(2024,11,4)
        }

        for inv in self.search([('status', '=', 'open')]):
            raw_date = inv.date
            if not raw_date or not inv.percent or not inv.orders:
                continue
            first_date = raw_date + timedelta(days=1)
            if accrual_date < first_date:
                continue

            order = inv.orders[0]
            principal_cont = Money.search([('order_id','=',order.id), ('percent','=',False), ('royalty','=',False)], limit=1)
            if not principal_cont:
                continue

            # Собираем все writeoff'ы, отсортированные по дате
            writeoffs = principal_cont.writeoff_ids.sorted(lambda w: w.date)

            # Считаем сумму списаний до первого дня начисления (чтобы понять стартовое тело)
            initial_off = sum(w.amount for w in writeoffs if w.date < first_date)
            initial_principal = inv.amount - initial_off

            interest_send = Money.search([('order_id','=',order.id), ('percent','=',True), ('partner_id','=',inv.sender.id)], limit=1)
            interest_recv = Money.search([('order_id','=',order.id), ('percent','=',True), ('partner_id','=',inv.receiver.id)], limit=1)
            royalty_conts = Money.search([('order_id','=',order.id), ('royalty','=',True)])
            if not (interest_send and interest_recv):
                continue

            write_vals = []
            period_days = self._get_period_days(inv.period, raw_date)
            day_cursor = first_date

            while day_cursor <= accrual_date:
                # Приведение day_cursor к типу date для корректного сравнения с праздниками
                day_cursor_date = day_cursor
                if isinstance(day_cursor_date, fields.Date):
                    day_cursor_date = fields.Date.to_date(day_cursor_date)
                elif hasattr(day_cursor_date, 'date'):
                    day_cursor_date = day_cursor_date.date()
                holidays = self.get_holidays(day_cursor_date.year)
                if inv.period == 'work_day' and (day_cursor_date.weekday() >= 5 or day_cursor_date in holidays):
                    day_cursor += timedelta(days=1)
                    continue

                # Считаем сумму списаний на текущую дату
                total_writeoffs = sum(w.amount for w in writeoffs if w.date <= day_cursor)

                # Универсальная логика: если суммы writeoff'ов отрицательные — добавляем, если положительные — вычитаем
                if total_writeoffs < 0:
                    principal = initial_principal + total_writeoffs
                else:
                    principal = initial_principal - total_writeoffs

                if principal <= 0:
                    day_cursor += timedelta(days=1)
                    continue

                if inv.period == 'calendar_month':
                    daily_rate = inv.percent / self._get_month_days(day_cursor)
                elif inv.period == 'calendar_year':
                    daily_rate = inv.percent / period_days
                else:
                    daily_rate = inv.percent

                interest = principal * daily_rate

                if interest_send.state == 'empty':
                    interest_send.write({'state': 'debt'})
                if interest_recv.state == 'empty':
                    interest_recv.write({'state': 'positive'})

                if interest:
                    write_vals.append({
                        'date': day_cursor,
                        'amount': interest,
                        'money_id': interest_send.id if interest_send else False,
                        'investment_ids': [(4, inv.id)],
                    })
                    write_vals.append({
                        'date': day_cursor,
                        'amount': -interest,
                        'money_id': interest_recv.id if interest_recv else False,
                        'investment_ids': [(4, inv.id)],
                    })

                # Роялти
                if inv.has_royalty:
                    for j in range(1, 10):
                        pct = getattr(inv, f'percent_{j}', 0)
                        recv = getattr(inv, f'royalty_recipient_{j}', False)
                        if not (recv and pct):
                            continue
                        cont = royalty_conts.filtered(lambda m: m.partner_id.id == recv.id)
                        if cont:
                            divisor = 1
                            if inv.period == 'calendar_month':
                                divisor = self._get_month_days(day_cursor)
                            elif inv.period == 'calendar_year':
                                divisor = period_days
                            roy = interest * (pct / 100.0) / divisor
                            write_vals.append({
                                'date': day_cursor,
                                'amount': roy,
                                'money_id': cont[0].id,
                                'investment_ids': [(4, inv.id)],
                            })

                day_cursor += timedelta(days=1)

            # Удаляем старые списания процентов и роялти за период
            ids_to_del = Writeoff.search([
                ('money_id', 'in', interest_send.ids + [interest_recv.id] + royalty_conts.ids),
                ('date', '>=', first_date),
                ('date', '<=', accrual_date),
            ]).ids
            if ids_to_del:
                Writeoff.browse(ids_to_del).unlink()

            # Создаём новые списания пакетно
            for i in range(0, len(write_vals), 50):
                # Удаляем некорректные записи без money_id
                batch = [w for w in write_vals[i:i+50] if w.get('money_id')]
                if batch:
                    Writeoff.create(batch)
            
            # Обновляем amount у процентных контейнеров
            for cont in [interest_send, interest_recv]:
                if cont:
                    cont.amount = sum(w.amount for w in cont.writeoff_ids)
            
            _logger.info(f"💰 Начисление для инвестиции {inv.name}: создано {len(write_vals)} списаний до {accrual_date}")

    def action_update_rollup_amount(self):
        """
        Ручной пересчёт суммы rollup_amount: суммирует rollup_write_off всех связанных ордеров
        """
        for rec in self:
            rec.rollup_amount = sum(order.rollup_write_off for order in rec.orders)
        return True

    # Кнопка для ручного обновления суммы rollup_amount
    def button_update_rollup_amount(self):
        self.ensure_one()
        self.action_update_rollup_amount()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Rollup обновлён'),
                'message': _('Сумма роллап списания успешно пересчитана.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def test_moscow_time_logic(self):
        """Тестовый метод для проверки логики времени по Москве"""
        self.ensure_one()
        
        # Получаем текущее время по Москве
        moscow_tz = pytz.timezone('Europe/Moscow')
        moscow_time = datetime.now(moscow_tz)
        moscow_hour = moscow_time.hour
        
        today = fields.Date.context_today(self)
        
        # Определяем дату для начисления
        accrual_date = today
        if moscow_hour < 20:
            accrual_date = today - timedelta(days=1)
        
        result = {
            'moscow_time': moscow_time.strftime('%Y-%m-%d %H:%M:%S'),
            'moscow_hour': moscow_hour,
            'today': today.strftime('%Y-%m-%d'),
            'accrual_date': accrual_date.strftime('%Y-%m-%d'),
            'will_accrue_today': moscow_hour >= 20,
            'message': f"Время по Москве: {moscow_time.strftime('%H:%M:%S')}, начисляем до: {accrual_date.strftime('%Y-%m-%d')}"
        }
        
        _logger.info(f"🧪 Тест времени: {result}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Тест времени по Москве'),
                'message': result['message'],
                'type': 'info',
                'sticky': True,
            }
        }

    @api.depends('write_offs')
    def _compute_write_offs_preview(self):
        for rec in self:
            # Сортируем по дате (или id) и берём первые 10
            writeoffs = rec.write_offs.sorted(lambda w: (w.date, w.id))[:10]
            rec.write_offs_preview = writeoffs

    def action_show_all_writeoffs(self):
        """
        Открывает act_window со всеми списаниями, связанными с данной инвестицией
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Все списания',
            'res_model': 'amanat.writeoff',
            'view_mode': 'list,form',
            # 'view_id': self.env.ref('amanat.writeoff_list_view').id,  # убрано для совместимости
            'domain': [('investment_ids', 'in', self.id)],
            'target': 'current',
            'context': dict(self.env.context),
        }

    @api.onchange('sender', 'receiver', 'date')
    def _onchange_partners_auto_royalty(self):
        """Автоматическое заполнение роялти на основе прайс-листа роялти для инвестиций"""
        if not self.sender or not self.receiver or not self.date:
            return

        # Ищем подходящие записи в прайс-листе роялти
        domain = [
            ('operation_type', '=', 'investment'),  # Тип операции = Инвестиции
            '|', '|',  # Три условия через ИЛИ
            # 1. Тип участника = "Отправитель" И контрагент = отправитель инвестиций
            '&', ('participant_type', '=', 'sender'), ('contragent_id', '=', self.sender.id),
            # 2. Тип участника = "Получатель" И контрагент = получатель инвестиций  
            '&', ('participant_type', '=', 'recipient'), ('contragent_id', '=', self.receiver.id),
            # 3. Тип участника = "Отправитель или получатель" И контрагент = любой из участников
            '&', ('participant_type', '=', 'both'), 
            '|', ('contragent_id', '=', self.sender.id), ('contragent_id', '=', self.receiver.id)
        ]

        # Добавляем фильтрацию по датам (если указаны)
        date_domain = []
        date_domain.append('|')
        date_domain.append('&')
        date_domain.append('&')
        date_domain.append(('date_from', '!=', False))
        date_domain.append(('date_to', '!=', False))
        date_domain.append('&')
        date_domain.append(('date_from', '<=', self.date))
        date_domain.append(('date_to', '>=', self.date))
        date_domain.append('|')
        date_domain.append(('date_from', '=', False))
        date_domain.append(('date_to', '=', False))

        full_domain = domain + date_domain

        royalty_records = self.env['amanat.price_list_royalty'].search(full_domain)

        # Логирование для отладки
        _logger.info(f"Автоматизация роялти для инвестиций: отправитель={self.sender.name}, получатель={self.receiver.name}, дата={self.date}")
        _logger.info(f"Найдено записей в прайс-листе роялти: {len(royalty_records)}")
        
        if royalty_records:
            # Очищаем старые значения роялти (инвестиции поддерживают только 3 роялти)
            for i in range(1, 4):
                setattr(self, f'royalty_recipient_{i}', False)

            # Заполняем новые значения роялти (максимум 3)
            for index, record in enumerate(royalty_records[:3], 1):
                setattr(self, f'royalty_recipient_{index}', record.royalty_recipient_id.id)
                _logger.info(f"Инвестиции роялти {index}: получатель {record.royalty_recipient_id.name} (тип участника: {record.participant_type})")
        else:
            # Очищаем поля роялти если ничего не найдено
            for i in range(1, 4):
                setattr(self, f'royalty_recipient_{i}', False)
            _logger.info("Подходящие записи роялти для инвестиций не найдены, поля очищены")

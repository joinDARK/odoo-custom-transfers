from dateutil.relativedelta import relativedelta
from datetime import timedelta, date
from odoo import models, fields, api, _
from .base_model import AmanatBaseModel
from collections import defaultdict
from odoo.exceptions import UserError
import logging

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
    ], string='Статус', default='close', tracking=True)

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

    # Флаги автоматизации
    create_action = fields.Boolean(string='Создать', tracking=True)
    to_delete = fields.Boolean(string='Удалить', tracking=True)
    post = fields.Boolean(string='Провести', tracking=True)
    repost = fields.Boolean(string='Перепровести', tracking=True)
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
    royalty_recipient_6 = fields.Many2one('amanat.contragent', string='Получтель роялти 6', tracking=True)
    royalty_recipient_7 = fields.Many2one('amanat.contragent', string='Получатель роялти 7', tracking=True)
    royalty_recipient_8 = fields.Many2one('amanat.contragent', string='Получатель роялти 8', tracking=True)
    royalty_recipient_9 = fields.Many2one('amanat.contragent', string='Получатель роялти 9', tracking=True)

    percent_1 = fields.Float(string='% первого', tracking=True)
    percent_2 = fields.Float(string='% второго', tracking=True)
    percent_3 = fields.Float(string='% третьего', tracking=True)
    percent_4 = fields.Float(string='% четвертого', tracking=True)
    percent_5 = fields.Float(string='% пятого', tracking=True)
    percent_6 = fields.Float(string='% шестого', tracking=True)
    percent_7 = fields.Float(string='% седьмого', tracking=True)
    percent_8 = fields.Float(string='% восьмого', tracking=True)
    percent_9 = fields.Float(string='% девятого', tracking=True)

    # Отношения
    orders = fields.Many2many('amanat.order', 'amanat_order_investment_rel', 'investment_id', 'order_id', string='Ордеры', tracking=True)
    write_offs = fields.Many2many('amanat.writeoff', 'amanat_investment_writeoff_rel', 'investment_id', 'writeoff_id', string='Списания', tracking=True)

    # Вычисляемые поля
    principal = fields.Float(string='Тело долга', compute='_compute_principal', store=True, tracking=True)
    calendar_days = fields.Integer(
        string='Календарных дней',
        compute='_compute_calendar_and_work_days',
        store=False,
        tracking=True,
    )
    work_days = fields.Integer(
        string='Рабочих дней',
        compute='_compute_calendar_and_work_days',
        store=False,
        tracking=True,
    )
    today_date = fields.Date(
        string='Дата сегодня',
        compute='_compute_calendar_and_work_days',
        store=False,
        tracking=True,
    )
    rollup_write_offs = fields.Float(string='Роллап списания', compute='_compute_rollup_write_offs', store=True, tracking=True)
    rollup_amount = fields.Float(string='Сумма роллап списания', tracking=True)
    rollup_amount_total = fields.Float(string='Сумма RollUp (from Погасить)', tracking=True)

    royalty_amount_1 = fields.Float(string='Сумма роялти 1', compute='_compute_royalty_amounts', store=True, tracking=True)
    royalty_amount_2 = fields.Float(string='Сумма роялти 2', compute='_compute_royalty_amounts', store=True, tracking=True)
    royalty_amount_3 = fields.Float(string='Сумма роялти 3', compute='_compute_royalty_amounts', store=True, tracking=True)
    royalty_amount_4 = fields.Float(string='Сумма роялти 4', compute='_compute_royalty_amounts', store=True, tracking=True)
    royalty_amount_5 = fields.Float(string='Сумма роялти 5', compute='_compute_royalty_amounts', store=True, tracking=True)
    royalty_amount_6 = fields.Float(string='Сумма роялти 6', compute='_compute_royalty_amounts', store=True, tracking=True)
    royalty_amount_7 = fields.Float(string='Сумма роялти 7', compute='_compute_royalty_amounts', store=True, tracking=True)
    royalty_amount_8 = fields.Float(string='Сумма роялти 8', compute='_compute_royalty_amounts', store=True, tracking=True)
    royalty_amount_9 = fields.Float(string='Сумма роялти 9', compute='_compute_royalty_amounts', store=True, tracking=True)

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
        # вычисляем календарные и рабочие дни с учётом праздников
        HOLIDAYS = {  # набор дат
            date(2024,1,1),date(2024,1,2),date(2024,1,3),date(2024,1,4),date(2024,1,5),
            date(2024,1,6),date(2024,1,7),date(2024,1,8),date(2024,2,23),date(2024,3,8),
            date(2024,5,1),date(2024,5,9),date(2024,6,12),date(2024,11,4)
        }
        for rec in self:
            today = fields.Date.context_today(self)
            if rec.date:
                days = (today - rec.date).days + 1
                wd = 0
                for i in range(days):
                    d = rec.date + timedelta(days=i)
                    if d.weekday() < 5 and d not in HOLIDAYS:
                        wd += 1
                rec.calendar_days = days
                rec.work_days = wd
            else:
                rec.calendar_days = rec.work_days = 0
            rec.today_date = today

    @api.depends('orders.rollup_write_off')
    def _compute_rollup_write_offs(self):
        for rec in self:
            rec.rollup_write_offs = sum(o.rollup_write_off for o in rec.orders)

    @api.depends('amount', 'percent_1', 'percent_2', 'percent_3', 'percent_4', 'percent_5', 'percent_6', 'percent_7', 'percent_8', 'percent_9')
    def _compute_royalty_amounts(self):
        for rec in self:
            # Суммы роялти считаем как процент от суммы (делим на 100)
            rec.royalty_amount_1 = (rec.amount or 0.0) * (rec.percent_1 or 0.0) / 100.0
            rec.royalty_amount_2 = (rec.amount or 0.0) * (rec.percent_2 or 0.0) / 100.0
            rec.royalty_amount_3 = (rec.amount or 0.0) * (rec.percent_3 or 0.0) / 100.0
            rec.royalty_amount_4 = (rec.amount or 0.0) * (rec.percent_4 or 0.0) / 100.0
            rec.royalty_amount_5 = (rec.amount or 0.0) * (rec.percent_5 or 0.0) / 100.0
            rec.royalty_amount_6 = (rec.amount or 0.0) * (rec.percent_6 or 0.0) / 100.0
            rec.royalty_amount_7 = (rec.amount or 0.0) * (rec.percent_7 or 0.0) / 100.0
            rec.royalty_amount_8 = (rec.amount or 0.0) * (rec.percent_8 or 0.0) / 100.0
            rec.royalty_amount_9 = (rec.amount or 0.0) * (rec.percent_9 or 0.0) / 100.0

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
        """Метод для кнопки 'Провести'"""
        for inv in self:
            # Сначала создаем списания
            inv.action_create_writeoffs()
            # Затем синхронизируем с Airtable и сверкой
            inv.action_sync_airtable()
            inv.action_sync_reconciliation()
            inv.post = False  # Сброс флага после выполнения


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

    def _get_month_days(d):
        nxt = d + relativedelta(months=1)
        return (date(nxt.year, nxt.month, 1) - date(d.year, d.month, 1)).day
    
    def action_sync_reconciliation(self):
        Reconc = self.env['amanat.reconciliation']
        Wallet = self.env['amanat.wallet']
        Payer = self.env['amanat.payer']
        Writeoff = self.env['amanat.writeoff']

        # Основной кошелек
        wallet = Wallet.search([('name', '=', 'Инвестиции')], limit=1)
        if not wallet:
            raise UserError(_('Кошелёк "Инвестиции" не найден'))

        # Настройка роялти
        royal_payer = Payer.search([('name', '=', 'Роялти')], limit=1)
        if not royal_payer:
            royal_payer = Payer.create({'name': 'Роялти'})
        royal_partner = self.env['amanat.contragent'].search([('name', '=', 'Роялти')], limit=1)
        if not royal_partner:
            royal_partner = self.env['amanat.contragent'].create({'name': 'Роялти'})

        for inv in self:
            if not inv.orders:
                continue
            order = inv.orders[0]
            # Удалить старые записи сверки
            Reconc.search([('order_id', '=', order.id)]).unlink()

            # Собираем контейнеры и связанные writeoff'ы
            containers = order.money_ids
            wf_ids = set()
            for cont in containers:
                if cont.percent or cont.royalty:
                    wf_ids |= set(cont.writeoff_ids.ids)
            wf_records = Writeoff.browse(list(wf_ids))

            # Проходим по каждому контейнеру
            for cont in containers:
                base_vals = {
                    'order_id': [(4, order.id)],
                    'wallet_id': wallet.id,
                    'currency': inv.currency.lower(),
                }
                # Principal-контейнеры
                if not cont.percent and not cont.royalty:
                    total = cont.amount or 0.0
                    date_val = inv.date
                    vals = {
                        'date': date_val,
                        'partner_id': cont.partner_id.id,
                        **base_vals,
                        'sum': total,
                        **self._get_currency_fields(inv.currency, total),
                        'sender_id': [(4, inv.payer_sender.id)] if inv.payer_sender else False,
                        'receiver_id': [(4, inv.payer_receiver.id)] if inv.payer_receiver else False,
                    }
                    Reconc.create(vals)
                    continue

                # Процентные/роялти-контейнеры: группировка по месяцам
                monthly = defaultdict(lambda: {'sum': 0.0, 'last_date': False})
                for wf in wf_records.filtered(lambda w: w.money_id.id == cont.id):
                    key = (wf.date.year, wf.date.month)
                    monthly[key]['sum'] += wf.amount
                    if not monthly[key]['last_date'] or wf.date > monthly[key]['last_date']:
                        monthly[key]['last_date'] = wf.date

                for (y, m), data in sorted(monthly.items()):
                    total = data['sum']
                    if total == 0.0:
                        continue
                    rec_date = data['last_date']
                    inverted = -total
                    vals = {
                        'date': rec_date,
                        'partner_id': cont.partner_id.id,
                        **base_vals,
                        'sum': inverted,
                        **self._get_currency_fields(inv.currency, inverted),
                    }
                    # Запись для держателя
                    Reconc.create({
                        **vals,
                        'sender_id': [(4, inv.payer_sender.id)] if inv.payer_sender else False,
                        'receiver_id': [(4, inv.payer_receiver.id)] if inv.payer_receiver else False,
                    })
                    # Запись для роялти
                    if cont.royalty:
                        Reconc.create({
                            **vals,
                            'partner_id': royal_partner.id,
                            'sender_id': [(4, royal_payer.id)],
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

            # 2) Создание нового ордера
            order_vals = {
                'date': inv.date,
                'type': 'transfer',  # предполагается, что есть тип 'transfer'
                'partner_1_id': inv.sender.id,
                'partner_2_id': inv.receiver.id,
                'currency': mapping.get(inv.currency),
                'amount': inv.amount,
                'wallet_1_id': wallet.id,
                'wallet_2_id': wallet.id,
                'comment': _('Сделка Инвестиция %s %s%%') % (inv.period or '', inv.percent * 100),
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

            # 6) Роялти-контейнеры
            if inv.has_royalty:
                for i in range(1, 10):
                    recv = getattr(inv, f'royalty_recipient_{i}', False)
                    pct = getattr(inv, f'percent_{i}', 0.0)
                    if recv and pct:
                        amt = (inv.amount or 0.0) * pct / 100.0
                        mk(recv, amt, roy=True)

            # 7) Создаем помесячные списания и сверки — вызываем ваши методы
            # inv.action_create_writeoffs()
            inv.action_sync_reconciliation()

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

        for inv in self.filtered('has_royalty'):
            # берём первый ордер, если их несколько
            order = inv.orders and inv.orders[0] or None
            for i in range(1, 10):
                recv = getattr(inv, f'royalty_recipient_{i}')
                pct  = getattr(inv, f'percent_{i}') or 0.0
                if not recv or not pct:
                    continue

                # соберём поля валют
                currency_vals = inv._get_currency_fields(inv.currency, 0.0)

                vals = {
                    'date':        inv.date,
                    'state':       'debt',
                    'partner_id':  recv.id,
                    'currency':    inv.currency.lower(),
                    'amount':      0.0,
                    'wallet_id':   Wallet.id,
                    'royalty':     True,
                    **currency_vals,
                }
                if order:
                    vals['order_id'] = order.id

                Money.create(vals)

        return True
    

    @staticmethod
    def _get_month_days(d):
        nxt = d + relativedelta(months=1)
        return (date(nxt.year, nxt.month, 1) - date(d.year, d.month, 1)).days

    def _batch_create_writeoffs(self, vals_list):
        Writeoff = self.env['amanat.writeoff']
        for i in range(0, len(vals_list), 50):
            Writeoff.create(vals_list[i:i+50])

    def accrue_daily_interest(self):
        """Ежедневное начисление процентов и роялти по открытым инвестициям"""
        Money = self.env['amanat.money']
        Writeoff = self.env['amanat.writeoff']
        today = fields.Date.context_today(self)
        for inv in self.search([('status', '=', 'open')]):
            # стартовые проверки
            # start_date = inv.date or today
            if not inv.date or not inv.percent or not inv.orders:
                continue
            # находим контейнеры
            order = inv.orders[0]
            principal_cont = Money.search([
                ('order_id', '=', order.id), ('percent', '=', False), ('royalty', '=', False)
            ], limit=1)
            interest_send = Money.search([
                ('order_id', '=', order.id), ('percent', '=', True), ('partner_id','=',inv.sender.id)
            ], limit=1)
            interest_recv = Money.search([
                ('order_id', '=', order.id), ('percent', '=', True), ('partner_id','=',inv.receiver.id)
            ], limit=1)

            if interest_recv:
                interest_recv.write({'state': 'positive'})
            
            if interest_send:
                interest_send.write({'state': 'debt'})                

            if not (principal_cont and interest_send and interest_recv):
                continue
            royalty_conts = Money.search([
                ('order_id', '=', order.id), ('royalty', '=', True)
            ])

            delete_start = principal_cont.date + timedelta(days=1)
            delete_end = today

            # удаляем старые
            old_ids = Writeoff.search([
                ('money_id', 'in', [principal_cont.id, interest_send.id, interest_recv.id] + [rc.id for rc in royalty_conts]),
                ('date', '>=', delete_start),
                ('date', '<=', delete_end),
            ]).ids
            for rc in royalty_conts:
                old_ids += rc.writeoff_ids.ids
            if old_ids:
                Writeoff.browse(old_ids).unlink()
            # расчёт: явно проходим по каждому полному дню (skip creation date, include today)
            days_diff = (today - principal_cont.date).days
            writeoffs = []
            if days_diff > 0:
                # для i=1..days_diff: дни с principal_cont.date + i
                for i in range(1, days_diff + 1):
                    day = principal_cont.date + timedelta(days=i)
                    # principal с учётом списаний
                    used = sum(w.amount for w in principal_cont.writeoff_ids if w.date <= day)
                    principal = (inv.amount or 0.0) - used
                    if principal <= 0:
                        continue
                    # процент
                    rate = inv.percent
                    if inv.period == 'calendar_month':
                        rate /= self._get_month_days(day)
                    elif inv.period == 'calendar_year':
                        # длина периода в днях от даты создания
                        period_len = self._get_period_days(inv.period, principal_cont.date)
                        rate /= period_len
                    interest = principal * rate
                    if interest:
                        writeoffs += [{
                            'date': day, 'amount': interest,
                            'money_id': interest_send.id,
                            'investment_ids': [(4, inv.id)]
                        }, {
                            'date': day, 'amount': -interest,
                            'money_id': interest_recv.id,
                            'investment_ids': [(4, inv.id)]
                        }]
                    # роялти
                    if inv.has_royalty:
                        for j in range(1, 10):
                            pct = getattr(inv, f'percent_{j}', 0.0)
                            recv = getattr(inv, f'royalty_recipient_{j}', False)
                            if not (recv and pct):
                                continue
                            cont = royalty_conts.filtered(lambda m: m.partner_id == recv)
                            if cont:
                                roy = principal * (pct / 100.0)
                                writeoffs.append({
                                    'date': day, 'amount': roy,
                                    'money_id': cont.id,
                                    'investment_ids': [(4, inv.id)]
                                })
            # запись
            if writeoffs:
                self._batch_create_writeoffs(writeoffs)

    @api.model
    def _cron_accrue_interest(self):
        """Cron: ежедневный запуск начисления"""
        self.search([('status', '=', 'open')]).accrue_daily_interest()
        return True

    def write(self, vals):
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
        if vals.get('royalty_post'):
            for r in self.filtered('royalty_post'):
                r.action_create_royalty_containers()
                r.action_create_writeoffs()
                r.action_sync_reconciliation()
                r.royalty_post = False
        if vals.get('close_investment'):
            for r in self.filtered('close_investment'):
                r.action_close_investment()
        if vals.get('accrue', False):
            for inv in self.filtered(lambda r: r.accrue):
                inv.accrue_daily_interest()
                inv.accrue = False  # Сбрасываем флаг после выполнения
        return res

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        if rec.create_action:
            rec.action_sync_airtable()
            rec.action_sync_reconciliation()
            rec.create_action = False
        if rec.to_delete:
            rec.action_delete()
        if rec.royalty_post:
            rec.action_create_royalty_containers()
            rec.action_create_writeoffs()
            rec.action_sync_reconciliation()
            rec.royalty_post = False
        if rec.close_investment:
            rec.action_close_investment()
        if vals.get('accrue', False):
            rec.accrue_daily_interest()
            rec.accrue = False
        return rec

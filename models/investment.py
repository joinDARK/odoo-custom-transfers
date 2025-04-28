from dateutil.relativedelta import relativedelta
from datetime import date, timedelta
from odoo import models, fields, api, _
from .base_model import AmanatBaseModel
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

    percent = fields.Float(string='Процент', tracking=True)
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
    calendar_days = fields.Integer(string='Календарных дней', compute='_compute_calendar_and_work_days', store=True, tracking=True)
    work_days = fields.Integer(string='Рабочих дней', compute='_compute_calendar_and_work_days', store=True, tracking=True)
    today_date = fields.Date(string='Дата сегодня', compute='_compute_calendar_and_work_days', store=True, tracking=True)
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

    @api.depends('date')
    def _compute_calendar_and_work_days(self):
        holidays = {date(2024,1,1), date(2024,2,23), date(2024,3,8), date(2024,5,1), date(2024,5,9), date(2024,6,12), date(2024,11,4)}
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.date:
                d0, d1 = rec.date, today
                delta = d1 - d0
                rec.calendar_days = delta.days + 1
                rec.work_days = sum(1 for i in range(delta.days+1) if (d0 + timedelta(days=i)).weekday() < 5 and (d0 + timedelta(days=i)) not in holidays)
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

    def action_sync_airtable(self):
        Money = self.env['amanat.money']
        Order = self.env['amanat.order']
        Writeoff = self.env['amanat.writeoff']
        Reconc = self.env['amanat.reconciliation']
        Wallet = self.env['amanat.wallet']
        Payer = self.env['amanat.payer']

        # Кошелек инвестиций
        wallet = Wallet.search([('name', '=', 'Инвестиции')], limit=1)
        if not wallet:
            raise UserError(_('Кошелёк "Инвестиции" не найден'))

        # Маппинг валют
        mapping = {
            'RUB':      'rub',      'RUB_cash':  'rub_cash',
            'USD':      'usd',      'USD_cash':  'usd_cash',
            'USDT':     'usdt',
            'EURO':     'euro',     'EURO_cash': 'euro_cash',
            'CNY':      'cny',      'CNY_cash':  'cny_cash',
            'AED':      'aed',      'AED_cash':  'aed_cash',
            'THB':      'thb',      'THB_cash':  'thb_cash',
        }

        # Найдем или создадим плательщика "Роялти"
        royal_payer = Payer.search([('name', '=', 'Роялти')], limit=1)
        if not royal_payer:
            royal_payer = Payer.create({'name': 'Роялти'})
        # Найдем или создадим контрагента "Роялти"
        royal_partner = self.env['amanat.contragent'].search([('name', '=', 'Роялти')], limit=1)
        if not royal_partner:
            royal_partner = self.env['amanat.contragent'].create({'name': 'Роялти'})
        if royal_partner.id not in royal_payer.contragents_ids.ids:
            royal_payer.write({'contragents_ids': [(4, royal_partner.id)]})

        for inv in self:
            # Удаляем старые записи
            for ord in inv.orders:
                Reconc.search([('order_id', 'in', ord.id)]).unlink()
                ord.money_ids.unlink()
                ord.unlink()
            inv.orders = [(5, 0, 0)]

            # Создаем новый ордер
            order_vals = {
                'date': inv.date,
                'type': 'transfer',
                'partner_1_id': inv.sender.id,
                'partner_2_id': inv.receiver.id,
                'payer_1_id': Payer.search([('contragents_ids', 'in', inv.sender.id)], limit=1).id,
                'payer_2_id': Payer.search([('contragents_ids', 'in', inv.receiver.id)], limit=1).id,
                'wallet_1_id': wallet.id,
                'wallet_2_id': wallet.id,
                'currency': mapping.get(inv.currency),
                'amount': inv.amount,
                'comment': _('Сделка Инвестиция %s %s%%') % (inv.period, inv.percent * 100),
            }
            new_ord = Order.create(order_vals)
            inv.orders = [(4, new_ord.id)]

            # Функция создания контейнеров
            def mk(holder, amt, debt=False, perc=False, roy=False):
                data = {
                    'date': inv.date,
                    'wallet_id': wallet.id,
                    'partner_id': holder.id,
                    'currency': mapping.get(inv.currency),
                    'amount': amt,
                    'state': 'debt' if debt else 'positive',
                    'percent': perc,
                    'royalty': roy,
                    'order_id': [(4, new_ord.id)],
                }
                data['sum'] = amt
                data[f'sum_{mapping.get(inv.currency)}'] = amt
                Money.create(data)

            # Долг и плюс
            mk(inv.sender, -inv.amount, debt=True)
            mk(inv.receiver, inv.amount)

            # Проценты или фикс
            if inv.percent > 0:
                mk(inv.sender, -inv.amount * inv.percent / 100.0, debt=True, perc=True)
                mk(inv.receiver, inv.amount * inv.percent / 100.0, perc=True)
            elif inv.fixed_amount > 0:
                mk(inv.sender, -inv.fixed_amount, debt=True, perc=True)
                mk(inv.receiver, inv.fixed_amount, perc=True)

            # Роялти контейнеры
            if inv.has_royalty:
                for i in range(1, 10):
                    recv = getattr(inv, f'royalty_recipient_{i}')
                    pct = getattr(inv, f'percent_{i}')
                    if recv and pct:
                        amt = (inv.amount or 0.0) * pct / 100.0
                        mk(recv, amt, roy=True)

            # Создаем сверки по месяцам
            cur = inv.date.replace(day=1)
            today = fields.Date.context_today(self)
            while cur <= today:
                end = (cur + relativedelta(months=1, day=1)) - timedelta(days=1)
                if cur.month == today.month and cur.year == today.year:
                    end = today
                for cont in new_ord.money_ids.filtered(lambda m: m.percent or m.royalty):
                    total = sum(
                        Writeoff.search([
                            ('id', 'in', cont.writeoff_ids.ids),
                            ('date', '>=', cur), ('date', '<=', end)
                        ]).mapped('amount')
                    )
                    recon_vals = {
                        'date': end,
                        'partner_id': cont.partner_id.id,
                        'currency': mapping.get(inv.currency),
                        'sum': total,
                        'wallet_id': wallet.id,
                        'order_id': [(4, new_ord.id)],
                    }
                    # в нужное поле суммы по валюте
                    recon_vals[f"sum_{mapping.get(inv.currency)}"] = total

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
        Money = self.env['amanat.money']; Order = self.env['amanat.order']; Writeoff = self.env['amanat.writeoff']; Reconc = self.env['amanat.reconciliation']
        for inv in self:
            for ord in inv.orders:
                Reconc.search([('order_id','in',ord.id)]).unlink()
                for c in ord.money_ids:
                    Writeoff.search([('id','in',c.writeoff_ids.ids)]).unlink()
                ord.money_ids.unlink(); ord.unlink()
            inv.orders=[(5,0,0)]; inv.status='archive'; inv.to_delete=False
        return True

    @api.model
    def create(self, vals):
        rec=super().create(vals)
        if rec.create_action: rec.action_sync_airtable(); rec.create_action=False
        if rec.to_delete: rec.action_delete()
        if rec.royalty_post: rec.action_sync_airtable(); rec.royalty_post=False
        return rec

    def write(self, vals):
        res=super().write(vals)
        if vals.get('create_action'):
            for r in self.filtered('create_action'): r.action_sync_airtable(); r.create_action=False
        if vals.get('to_delete'):
            for r in self.filtered('to_delete'): r.action_delete()
        if vals.get('royalty_post'):
            for r in self.filtered('royalty_post'): r.action_sync_airtable(); r.royalty_post=False
        return res

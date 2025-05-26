# models/reconciliation.py
from odoo import models, fields, api
from .base_model import AmanatBaseModel
from odoo.exceptions import UserError
import requests
from datetime import datetime
from odoo.tools.translate import _
import logging

_logger = logging.getLogger(__name__)

class Reconciliation(models.Model, AmanatBaseModel):
    _name = 'amanat.reconciliation'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Сверки'

    date = fields.Date(string='Дата', tracking=True)
    partner_id = fields.Many2one('amanat.contragent', string='Контрагент', tracking=True)
    currency = fields.Selection(
        [
            ('rub', 'RUB'), ('rub_cashe', 'RUB КЭШ'), ('usd', 'USD'), ('usd_cashe', 'USD КЭШ'), ('usdt', 'USDT'), ('euro', 'EURO'),
            ('euro_cashe', 'EURO КЭШ'), ('cny', 'CNY'), ('cny_cashe', 'CNY КЭШ'), ('aed', 'AED'), ('aed_cashe', 'AED КЭШ'),
            ('thb', 'THB'), ('thb_cashe', 'THB КЭШ'),
        ],
        string='Валюта',
        default='rub',
        tracking=True
    )
    sum = fields.Float(string='Сумма', tracking=True)
    wallet_id = fields.Many2one('amanat.wallet', string='Кошелек', tracking=True)
    sender_id = fields.Many2many(
        'amanat.payer',
        string='Отправитель',
        tracking=True
    )
    sender_contragent = fields.Many2many(
        'amanat.contragent',
        related='sender_id.contragents_ids',
        string='Отправитель (from Контрагент)',
        tracking=True
    )
    receiver_id = fields.Many2many(
        'amanat.payer',
        'amanat_reconciliation_payer_rel',
        'reconciliation_id',
        'payer_id',
        string='Получатель',
        tracking=True
    )
    receiver_contragent = fields.Many2many(
        'amanat.contragent',
        related='receiver_id.contragents_ids',
        string='Получатель (from Контрагент)',
        tracking=True
    )

    sum_rub = fields.Float(string='Сумма RUB', tracking=True)
    sum_usd = fields.Float(string='Сумма USD', tracking=True)
    sum_usdt = fields.Float(string='Сумма USDT', tracking=True)
    sum_cny = fields.Float(string='Сумма CNY', tracking=True)
    sum_euro = fields.Float(string='Сумма EURO', tracking=True)
    sum_aed = fields.Float(string='Сумма AED', tracking=True)
    sum_thb = fields.Float(string='Сумма THB', tracking=True)

    sum_rub_cashe = fields.Float(string='Сумма RUB КЭШ', tracking=True)
    sum_usd_cashe = fields.Float(string='Сумма USD КЭШ', tracking=True)
    sum_cny_cashe = fields.Float(string='Сумма CNY КЭШ', tracking=True)
    sum_euro_cashe = fields.Float(string='Сумма EURO КЭШ', tracking=True)
    sum_aed_cashe = fields.Float(string='Сумма AED КЭШ', tracking=True)
    sum_thb_cashe = fields.Float(string='Сумма THB КЭШ', tracking=True)

    rate = fields.Float(string='Курс', related='order_id.rate', store=True, tracking=True)
    award = fields.Float(string='За операцию (from Ордер)', related='order_id.operation_percent', store=True, tracking=True)
    rko = fields.Float(string='РКО (from Ордер)', related='order_id.rko', store=True, tracking=True)
    our_percent = fields.Float(string='Наш процент (from Ордер)', related='order_id.our_percent', store=True, tracking=True)
    rko_2 = fields.Float(string='РКО 2 (from Ордер)', related='order_id.rko_2', store=True, tracking=True)
    
    exchange = fields.Float(string='К выдаче', tracking=True)
    order_id = fields.Many2many(
        'amanat.order',
        'amanat_order_reconciliation_rel',
        'order_id', 
        'reconciliation_id',
        string='Ордер', 
        tracking=True
    )
    order_comment = fields.Text(string='Комментарий (from Ордер)', related='order_id.comment', store=True, tracking=True)
    unload = fields.Boolean(string='Выгрузить', default=False, tracking=True)

    range = fields.Many2one('amanat.ranges', string='Диапазон', tracking=True)
    range_reconciliation_date_1 = fields.Date(string='Сверка Дата 1 (from Диапазон)', related='range.reconciliation_date_1', store=True, tracking=True)
    range_reconciliation_date_2 = fields.Date(string='Сверка Дата 2 (from Диапазон)', related='range.reconciliation_date_2', store=True, tracking=True)
    range_date_reconciliation = fields.Selection(
        [('not', 'Нет'), ('yes', 'Да')],
        string='Диапазон дат сверка',
        default='not',
        tracking=True
    )
    compare_balance_date_1 = fields.Date(string='Сравнение баланса дата 1 (from Диапазон)', related='range.compare_balance_date_1', store=True, tracking=True)
    compare_balance_date_2 = fields.Date(string='Сравнение баланса дата 2 (from Диапазон)', related='range.compare_balance_date_2', store=True, tracking=True)
    status_comparison_1 = fields.Selection(
        [('not', 'Нет'), ('yes', 'Да')],
        string='Статус сравнение 1',
        default='not',
        tracking=True
    )
    status_comparison_2 = fields.Selection(
        [('not', 'Нет'), ('yes', 'Да')],
        string='Статус сравнение 2',
        default='not',
        tracking=True
    )
    range_date_start = fields.Date(string='Дата начало (from Диапазон)', related='range.date_start', store=True, tracking=True)
    range_date_end = fields.Date(string='Дата конец (from Диапазон)', related='range.date_end', store=True, tracking=True)
    status_range = fields.Selection(
        [('not', 'Нет'), ('yes', 'Да')],
        string='Статус диапазона',
        default='not',
        tracking=True
    )

    rate_id = fields.Many2one('amanat.rates', string='Курсы', tracking=True)
    rate_euro = fields.Float(string='euro (from Курсы)', related='rate_id.euro', store=True, tracking=True)
    rate_cny = fields.Float(string='cny (from Курсы)', related='rate_id.cny', store=True, tracking=True)
    rate_rub = fields.Float(string='rub (from Курсы)', related='rate_id.rub', store=True, tracking=True)
    rate_aed = fields.Float(string='aed (from Курсы)', related='rate_id.aed', store=True, tracking=True)
    rate_thb = fields.Float(string='thb (from Курсы)', related='rate_id.thb', store=True, tracking=True)
    rate_usd = fields.Float(string='usd (from Курсы)', related='rate_id.usd', store=True, tracking=True)
    rate_usdt = fields.Float(string='usdt (from Курсы)', related='rate_id.usdt', store=True, tracking=True)
    equivalent = fields.Float(string='Эквивалент $', tracking=True)

    create_Reconciliation = fields.Boolean(string='Создать', default=False, tracking=True) # TODO нужно удалить
    royalti_Reconciliation = fields.Boolean(string='Провести роялти', default=False, tracking=True) # TODO нужно удалить

    range_reconciliation_bool = fields.Boolean(string='Сверка по диапазону', default=False, tracking=True)

    def write(self, vals):
        unload_trigger = False
        if 'unload' in vals:
            # Выгружать только когда чекбокс стал True (но не при снятии галки)
            for rec in self:
                old_value = rec.unload
                new_value = vals['unload']
                if not old_value and new_value:
                    unload_trigger = True
                    break

        res = super(Reconciliation, self).write(vals)
        if unload_trigger:
            # После сохранения вызываем автоматизацию для тех записей, где unload = True
            for rec in self.filtered(lambda r: r.unload):
                rec._run_reconciliation_export()
                # Сбросить галку обратно
                rec.with_context(skip_export=True).write({'unload': False})
        return res

    @api.model
    def create(self, vals):
        # Автоматизация "Автодиапазон"
        # --- Блок автозаполнения диапазона ---
        range_id = vals.get('range')
        if not range_id:
            range_rec = self.env['amanat.ranges'].browse(1)
            if range_rec.exists():
                vals['range'] = range_rec.id
            else:
                _logger.warning(_('В таблице "Диапазон" не найдена запись с ID = 1.'))

        # --- Блок автозаполнения курса ---
        rate_id = vals.get('rate_id')
        if not rate_id:
            rate_rec = self.env['amanat.rates'].browse(1)
            if rate_rec.exists():
                vals['rate_id'] = rate_rec.id
            else:
                _logger.warning(_('В таблице "Курсы" не найдена запись с ID = 1.'))

        rec = super(Reconciliation, self).create(vals)

        # Срабатывание выгрузки если отмечен чекбокс "Выгрузить" (оставляем твою логику)
        if vals.get('unload'):
            rec._run_reconciliation_export()
            rec.with_context(skip_export=True).write({'unload': False})

        return rec
    
    @api.model
    def _prepare_reconciliation_export_data(self, contragent, use_range):
        """
        Готовит данные для экспорта по контрагенту (и диапазону).
        """
        domain = [('partner_id', '=', contragent.id)]
        if use_range:
            domain.append(('range_date_reconciliation', '=', 'yes'))
        recs = self.search(domain)
        data = []
        for rec in recs.sorted(key=lambda r: r.id):
            data.append({
                'id': rec.id,
                '№': rec.id,
                'Контрагент': rec.partner_id.name,
                'Дата': rec.date.isoformat() if rec.date else '',
                'Отправитель': ', '.join(rec.sender_id.mapped('name')),
                'Контрагенты (from Отправитель)': ', '.join(rec.sender_contragent.mapped('name')),
                'Получатель': ', '.join(rec.receiver_id.mapped('name')),
                'Валюта': rec.currency,
                'Сумма': rec.sum,
                'Сумма RUB': rec.sum_rub,
                'Сумма USD': rec.sum_usd,
                'Сумма USDT': rec.sum_usdt,
                'Сумма CNY': rec.sum_cny,
                'Сумма AED': rec.sum_aed,
                'Сумма EURO': rec.sum_euro,
                'Сумма THB': rec.sum_thb,
                'Сумма RUB КЕШ': rec.sum_rub_cashe,
                'Сумма USD КЕШ': rec.sum_usd_cashe,
                'Сумма CNY КЕШ': rec.sum_cny_cashe,
                'Сумма EURO КЕШ': rec.sum_euro_cashe,
                'Сумма AED КЕШ': rec.sum_aed_cashe,
                'Сумма THB КЕШ': rec.sum_thb_cashe,
                'Ордеры': ', '.join(rec.order_id.mapped('name')),
                'Комментарий (from Ордер)': rec.order_comment or '',
                'Сумма_Ордер': rec.order_id and rec.order_id[0].amount_total or 0.0,  # пример
                'Курс': rec.rate,
            })
        return data

    def _run_reconciliation_export(self):
        """
        Основная логика выгрузки.
        """
        for rec in self:
            contragent = rec.partner_id
            if not contragent:
                continue
            use_range = rec.range_reconciliation_bool

            file_name = '{} {}'.format(contragent.name, datetime.today().strftime('%d.%m.%Y'))

            data = self._prepare_reconciliation_export_data(contragent, use_range)
            payload = {'fileName': file_name, 'data': data}

            endpoint = "http://92.255.207.48:8080/receive-data"
            file_url = False
            try:
                resp = requests.post(endpoint, json=payload, timeout=60)
                resp.raise_for_status()
                resp_data = resp.json()
                if resp_data.get('success') and resp_data.get('fileUrl'):
                    file_url = resp_data['fileUrl']
            except Exception as e:
                raise UserError(_("Ошибка при отправке данных на сервер: %s" % e))

            if file_url:
                IrAttachment = self.env['ir.attachment']
                attachment = IrAttachment.create({
                    'name': file_name + ".xlsx",
                    'type': 'url',
                    'url': file_url,
                    'res_model': self._name,
                    'res_id': rec.id,
                })
        return True
    
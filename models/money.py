# models/money.py
from odoo import models, fields, api
from .base_model import AmanatBaseModel
import logging

_logger = logging.getLogger(__name__)

class Money(models.Model, AmanatBaseModel):
    _name = 'amanat.money'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Контейнеры денег'

    royalty = fields.Boolean(string='Роялти', tracking=True, default=False)
    percent = fields.Boolean(string='Проценты', tracking=True, default=False)
    date = fields.Date(string='Дата', tracking=True)
    wallet_id = fields.Many2one('amanat.wallet', string='Кошелек', tracking=True)
    partner_id = fields.Many2one('amanat.contragent', string='Держатель', tracking=True)
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
    
    # Списания, связанные по money_id
    writeoff_ids = fields.One2many(
        'amanat.writeoff',
        'money_id',
        string='Списания',
        tracking=True,
    )

    amount = fields.Float(string='Сумма', tracking=True)
    order_id = fields.Many2one(
        'amanat.order',
        string='Ордер',
        tracking=True,
    )
    state = fields.Selection([
        ('debt',      'Долг'),
        ('positive', 'Положительный'),
        ('empty',    'Пусто'),        # <-- новый вариант
    ], string='Состояние', default='positive')

    sum = fields.Float(string='Сумма', tracking=True)
    sum_rub = fields.Float(string='Сумма RUB', tracking=True)
    sum_usd = fields.Float(string='Сумма USD', tracking=True)
    sum_usdt = fields.Float(string='Сумма USDT', tracking=True)
    sum_cny = fields.Float(string='Сумма CNY', tracking=True)
    sum_euro = fields.Float(string='Сумма EURO', tracking=True)
    sum_aed = fields.Float(string='Сумма AED', tracking=True)
    sum_thb = fields.Float(string='Сумма THB', tracking=True)
    sum_usd_cashe = fields.Float(string='Сумма USD КЭШ', tracking=True)
    sum_euro_cashe = fields.Float(string='Сумма EURO КЭШ', tracking=True)
    sum_aed_cashe = fields.Float(string='Сумма AED КЭШ', tracking=True)
    sum_cny_cashe = fields.Float(string='Сумма CNY КЭШ', tracking=True)
    sum_rub_cashe = fields.Float(string='Сумма RUB КЭШ', tracking=True)
    sum_thb_cashe = fields.Float(string='Сумма THB КЭШ', tracking=True)

    # Computed-поля для остатков и суммы списаний
    remains = fields.Float(
        string='Остаток',
        tracking=True,
        compute='_compute_remains_fields',
        store = True
    )
    remains_rub = fields.Float(
        string='Остаток RUB',
        tracking=True,
        compute='_compute_remains_fields',
        # store=True
    )
    remains_rub_cashe = fields.Float(
        string='Остаток RUB КЭШ',
        tracking=True,
        compute='_compute_remains_fields',
        # store=True
    )
    remains_usd = fields.Float(
        string='Остаток USD',
        tracking=True,
        compute='_compute_remains_fields',
        # store=True
    )
    remains_usd_cashe = fields.Float(
        string='Остаток USD КЭШ',
        tracking=True,
        compute='_compute_remains_fields',
        # store=True
    )
    remains_usdt = fields.Float(
        string='Остаток USDT',
        tracking=True,
        compute='_compute_remains_fields',
        # store=True
    )
    remains_cny = fields.Float(
        string='Остаток CNY',
        tracking=True,
        compute='_compute_remains_fields',
        # store=True
    )
    remains_cny_cashe = fields.Float(
        string='Остаток CNY КЭШ',
        tracking=True,
        compute='_compute_remains_fields',
        # store=True
    )
    remains_euro = fields.Float(
        string='Остаток EURO',
        tracking=True,
        compute='_compute_remains_fields',
        # store=True
    )
    remains_euro_cashe = fields.Float(
        string='Остаток EURO КЭШ',
        tracking=True,
        compute='_compute_remains_fields',
        # store=True
    )
    remains_aed = fields.Float(
        string='Остаток AED',
        tracking=True,
        compute='_compute_remains_fields',
        # store=True
    )
    remains_aed_cashe = fields.Float(
        string='Остаток AED КЭШ',
        tracking=True,
        compute='_compute_remains_fields',
        # store=True
    )
    remains_thb = fields.Float(
        string='Остаток THB',
        tracking=True,
        compute='_compute_remains_fields',
        # store=True
    )
    remains_thb_cashe = fields.Float(
        string='Остаток THB КЭШ',
        tracking=True,
        compute='_compute_remains_fields',
        # store=True
    )
    sum_remains = fields.Float(
        string='Сумма списания',
        tracking=True,
        compute='_compute_remains_fields',
        # store=True
    )

    # Комментарий
    comment = fields.Text(
        related='order_id.comment',
        string='Комментарии',
        readonly=True,
        store=True,
        tracking=True
    )

    @api.depends(
        'sum', 'sum_rub', 'sum_usd', 'sum_usdt', 'sum_cny', 'sum_euro', 'sum_aed',
        'sum_rub_cashe', 'sum_usd_cashe', 'sum_cny_cashe', 'sum_euro_cashe', 'sum_aed_cashe',
        'sum_thb', 'sum_thb_cashe', 'writeoff_ids.amount'
    )
    def _compute_remains_fields(self):
        for rec in self:
            # Вычисляем сумму списаний (rollup)
            writeoff_sum = sum(rec.writeoff_ids.mapped('amount'))
            rec.sum_remains = writeoff_sum

            # Общий остаток:
            # Если "Сумма" заполнена (не равна нулю), то она считается основной, иначе суммируются конкретные валюты.
            if rec.sum:
                rec.remains = rec.sum - writeoff_sum
            else:
                rec.remains = (rec.sum_rub + rec.sum_usd + rec.sum_usdt + rec.sum_cny + rec.sum_euro + rec.sum_aed) - writeoff_sum

            # Остаток по отдельным валютам по аналогии с формулой:
            # IF({Валюта} = "XXX", {Сумма XXX} - {Сумма списаний}, 0)
            rec.remains_rub = rec.sum_rub - writeoff_sum if rec.currency == 'rub' else 0
            rec.remains_rub_cashe = rec.sum_rub_cashe - writeoff_sum if rec.currency == 'rub_cashe' else 0
            rec.remains_usd = rec.sum_usd - writeoff_sum if rec.currency == 'usd' else 0
            rec.remains_usd_cashe = rec.sum_usd_cashe - writeoff_sum if rec.currency == 'usd_cashe' else 0
            rec.remains_usdt = rec.sum_usdt - writeoff_sum if rec.currency == 'usdt' else 0
            rec.remains_cny = rec.sum_cny - writeoff_sum if rec.currency == 'cny' else 0
            rec.remains_cny_cashe = rec.sum_cny_cashe - writeoff_sum if rec.currency == 'cny_cashe' else 0
            rec.remains_euro = rec.sum_euro - writeoff_sum if rec.currency == 'euro' else 0
            rec.remains_euro_cashe = rec.sum_euro_cashe - writeoff_sum if rec.currency == 'euro_cashe' else 0
            rec.remains_aed = rec.sum_aed - writeoff_sum if rec.currency == 'aed' else 0
            rec.remains_aed_cashe = rec.sum_aed_cashe - writeoff_sum if rec.currency == 'aed_cashe' else 0
            rec.remains_thb = rec.sum_thb - writeoff_sum if rec.currency == 'thb' else 0
            rec.remains_thb_cashe = rec.sum_thb_cashe - writeoff_sum if rec.currency == 'thb_cashe' else 0

        # Автоматически обновляем состояние после вычисления остатков
        self._auto_update_state_after_compute()

    def _auto_update_state_after_compute(self):
        """
        Автоматическое обновление состояния после вычисления остатков.
        Вызывается из _compute_remains_fields.
        """
        for record in self:
            remainder = record.remains
            
            # Проверяем, что остаток является числом
            if not isinstance(remainder, (int, float)):
                continue
            
            # Определяем новое состояние на основе остатка
            if remainder > 0:
                new_state = 'positive'
            elif remainder < 0:
                new_state = 'debt'
            else:
                # remainder === 0
                new_state = 'empty'
            
            # Обновляем поле "Состояние" только если оно изменилось
            if record.state != new_state:
                # Используем sudo() для избежания рекурсии в логировании
                record.sudo().write({'state': new_state})
                _logger.info(f"Автоматически обновлено состояние контейнера ID={record.id}: {record.state} → {new_state} (остаток: {remainder})")

    def update_state_based_on_remainder(self):
        """
        Обновляет состояние контейнера на основе остатка.
        Используется в других моделях для принудительного обновления.
        """
        for record in self:
            remainder = record.remains
            
            # Проверяем, что остаток является числом
            if not isinstance(remainder, (int, float)):
                continue
            
            # Определяем новое состояние на основе остатка
            if remainder > 0:
                new_state = 'positive'
            elif remainder < 0:
                new_state = 'debt'
            else:
                # remainder === 0
                new_state = 'empty'
            
            # Обновляем поле "Состояние" только если оно изменилось
            if record.state != new_state:
                record.write({'state': new_state})
                _logger.info(f"Обновлено состояние контейнера ID={record.id}: {record.state} → {new_state} (остаток: {remainder})")

    @api.model
    def auto_update_all_states(self):
        """
        Автоматическое обновление состояния для всех контейнеров денег.
        Используется как cron job каждые 3 секунды.
        """
        all_money_records = self.search([])
        _logger.info(f"Начинаем автоматическое обновление состояния для {len(all_money_records)} контейнеров")
        
        for record in all_money_records:
            remainder = record.remains
            
            # Проверяем, что остаток является числом
            if not isinstance(remainder, (int, float)):
                _logger.error(f"Поле 'Остаток' не число или не заполнено: {remainder} для записи ID={record.id}")
                continue
            
            # Определяем новое состояние на основе остатка
            if remainder > 0:
                new_state = 'positive'
            elif remainder < 0:
                new_state = 'debt'
            else:
                # remainder === 0
                new_state = 'empty'
            
            # Обновляем поле "Состояние" только если оно изменилось
            if record.state != new_state:
                record.write({'state': new_state})
                _logger.info(f"Состояние контейнера ID={record.id} обновлено на '{new_state}' (остаток: {remainder})")
        
        _logger.info("Автоматическое обновление состояния завершено")

    def _get_realtime_fields(self):
        """Поля для real-time обновлений в списке контейнеров денег"""
        return [
            'id', 'display_name', 'date', 'wallet_id', 'partner_id', 'currency',
            'amount', 'sum', 'state', 'order_id', 'remains', 'sum_remains',
            'royalty', 'percent', 'comment', 'create_date', 'write_date'
        ]
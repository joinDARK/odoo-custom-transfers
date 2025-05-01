# amanat/models/writeoff.py

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class WriteOff(models.Model):
    _name = 'amanat.writeoff'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Списания'

    # Пользовательское поле-идентификатор «Id Списания» (вместо name)
    # Если хотите назвать его name, переименуйте соответственно.
    id_spisaniya = fields.Char(
        string="Id Списания", 
        tracking=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('amanat.writeoff.sequence')
    )

    date = fields.Date(
        string="Дата", 
        tracking=True,
        default=fields.Date.today,
    )
    amount = fields.Float(string="Сумма", tracking=True)

    sender_id = fields.Many2one(
        'amanat.contragent', 
        string='Отправитель',
        tracking=True,
    )
    sender_payer_id = fields.Many2one(
        'amanat.payer',
        string='Плательщик отправителя',
        tracking=True,
        domain="[('contragents_ids', 'in', sender_id)]"
    )
    sender_wallet_id = fields.Many2one('amanat.wallet', string='Кошелек отправителя', tracking=True)

    @api.onchange('sender_id')
    def _onchange_sender_id(self):
        if self.sender_id:
            payer = self.env['amanat.payer'].search(
                [('contragents_ids', 'in', self.sender_id.id)], limit=1)
            self.sender_payer_id = payer.id if payer else False
        else:
            self.sender_payer_id = False

    # Ссылка на модель "amanat.money" (Контейнер)
    money_id = fields.Many2one(
        'amanat.money',
        string='Контейнер',
        tracking=True,
        ondelete='cascade',
    )

    # Ссылка на модель "amanat.investment"
    investment_ids = fields.Many2many(
        'amanat.investment',
        'amanat_investment_writeoff_rel', 
        'writeoff_id',
        'investment_id',
        string="Инвестиции",
        tracking=True,
    )

    # Списание инвестиции. Используется для автоматизации
    writeoff_investment = fields.Boolean(
        string="Списание инвестиций",
        default=False,
        tracking=True,
    )

    @api.model
    def process_write_off(self):
        """
        Функция обрабатывает списание:
        - Привязывает подходящие контейнеры
        - Создает обратное списание на долговой контейнер
        """

        self.ensure_one()

        investment = self.investment_ids
        if not investment:
            raise ValidationError("Не указана инвестиция")

        order = investment.orders[:1]
        if not order:
            raise ValidationError("Нет связанного ордера")

        money_records = order.money_ids
        if not money_records:
            raise ValidationError("Нет связанных контейнеров")

        valid_container = money_records.filtered(
            lambda m: not m.percent and not m.royalty and m.state != 'debt'
        )[:1]
        if not valid_container:
            raise ValidationError("Нет подходящих контейнеров")

        self.money_id = valid_container.id  # 🟢 Many2one

        debt_container = money_records.filtered(lambda m: m.state == 'debt')[:1]
        if not debt_container:
            raise ValidationError("Не найден долговой контейнер")

        self.create({
            'amount': -self.amount,
            'date': self.date,
            'money_id': debt_container.id,
            'investment_ids': [(6, 0, [investment.id])],
        })

        return True

    def create_transfer_after_writeoff(self): # TODO активировать этот скрипт
        """
        Создает запись в 'Перевод' (amanat.transfer) на основе данных списания и инвестиции.
        """
        self.ensure_one()

        if not self.sender_id or not self.sender_payer_id or not self.sender_wallet_id:
            raise ValidationError("Отсутствуют данные отправителя")

        if not self.investment_ids:
            raise ValidationError("Нет связанной инвестиции")

        investment = self.investment_ids[:1]

        if not investment.recipient_id or not investment.recipient_payer_id or not investment.currency:
            raise ValidationError("Отсутствуют данные получателя или валюты")

        # Найти кошелек получателя с названием "Инвестиции"
        recipient_wallet = self.env['amanat.wallet'].search([('name', '=', 'Инвестиции')], limit=1)
        if not recipient_wallet:
            raise ValidationError("Кошелек 'Инвестиции' не найден")

        transfer = self.env['amanat.transfer'].create({
            'date': self.date,
            'currency': investment.currency,
            'amount': self.amount,
            'sender_id': self.sender_id.id,
            'sender_payer_id': self.sender_payer_id.id,
            'sender_wallet_id': self.sender_wallet_id.id,
            'recipient_id': investment.recipient_id.id,
            'recipient_payer_id': investment.recipient_payer_id.id,
            'recipient_wallet_id': recipient_wallet.id,
        })

        # Активируем чекбокс
        transfer.create_order = True

        return transfer

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        if rec.writeoff_investment:
            rec.process_write_off()
            rec.writeoff_investment = False
        return rec

    def write(self, vals):
        res = super().write(vals)
        if vals.get('writeoff_investment'):
            for rec in self.filtered('writeoff_investment'):
                rec.process_write_off()  # 🟢 Запуск при изменении
                rec.writeoff_investment = False
        return res

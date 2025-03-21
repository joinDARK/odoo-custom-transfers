from odoo import models, fields, api
from .base_model import AmanatBaseModel

class Transfer(models.Model, AmanatBaseModel):
    _name = 'amanat.transfer'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Перевод'
    
    state = fields.Selection(
        [('open', 'Открыта'), ('archive', 'Архив'), ('close', 'Закрыта')],
        string='Статус',
        default='open',
        tracking=True
    )
    date = fields.Date(string='Дата', default=fields.Date.today, tracking=True)
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
    amount = fields.Float(string='Сумма', required=True, tracking=True)
    sender_id = fields.Many2one('amanat.contragent', string='Отправитель', required=True, tracking=True)
    sender_payer_id = fields.Many2one(
        'amanat.payer',
        string='Плательщик отправителя',
        compute='_compute_payers',
        store=True,
        readonly=False,  # Позволяет редактировать поле вручную
        tracking=True
    )
    receiver_id = fields.Many2one('amanat.contragent', string='Получатель', required=True, tracking=True)
    receiver_payer_id = fields.Many2one(
        'amanat.payer',
        string='Плательщик получателя',
        compute='_compute_payers',
        store=True,
        readonly=False,
        tracking=True
    )

    manager_id = fields.Many2one('res.users', string='Manager', tracking=True)
    inspector_id = fields.Many2one('res.users', string='Inspector', tracking=True)

    def log_transfer_data(self):
        for record in self:
            data = {
                "ID": record.id,
                "Статус": record.state,
                "Дата": record.date,
                "Валюта": record.currency,
                "Сумма": record.amount,
                "Отправитель": record.sender_id.name,
                "Плательщик отправителя": record.sender_payer_id.name,
                "Получатель": record.receiver_id.name,
                "Плательщик получателя": record.receiver_payer_id.name,
                "Менеджер": record.manager_id.name or "",
                "Проверяющий": record.inspector_id.name or "",
            }
            print("\n=== Данные перевода ===")
            for key, value in data.items():
                print(f"{key}: {value}")
            print("=======================\n")

    # Переопределяем метод create
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)  # Сначала создаем записи
        records.log_transfer_data()          # Затем логируем
        return records

    @api.depends('sender_id', 'receiver_id')
    def _compute_payers(self):
        for record in self:
            # Для отправителя
            if record.sender_id and record.sender_id.payer_id:
                record.sender_payer_id = record.sender_id.payer_id
            else:
                record.sender_payer_id = False

            # Для получателя
            if record.receiver_id and record.receiver_id.payer_id:
                record.receiver_payer_id = record.receiver_id.payer_id
            else:
                record.receiver_payer_id = False

    # Добавьте onchange для обновления в интерфейсе
    @api.onchange('sender_id')
    def _onchange_sender_id(self):
        self.sender_payer_id = self.sender_id.payer_id if self.sender_id else False

    @api.onchange('receiver_id')
    def _onchange_receiver_id(self):
        self.receiver_payer_id = self.receiver_id.payer_id if self.receiver_id else False

#models/transfer.py
from odoo import models, fields, api
from .base_model import AmanatBaseModel

class Transfer(models.Model, AmanatBaseModel):
    _name = 'amanat.transfer'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Перевод'
    
    name = fields.Char(
        string='Номер заявки',
        default=lambda self: self.env['ir.sequence'].next_by_code('amanat.transfer.sequence'),
        required=True,
        readonly=True
    )
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
    sender_wallet_id = fields.Many2one('amanat.wallet', string='Кошелек отправителя', required=True, tracking=True)
    receiver_id = fields.Many2one('amanat.contragent', string='Получатель', required=True, tracking=True)
    receiver_payer_id = fields.Many2one(
        'amanat.payer',
        string='Плательщик получателя',
        compute='_compute_payers',
        store=True,
        readonly=False,
        tracking=True
    )
    receiver_wallet_id = fields.Many2one('amanat.wallet', string='Кошелек получателя', required=True, tracking=True)
    create_order = fields.Boolean(string='Создать', default=False, tracking=True)
    is_complex = fields.Boolean(string='Сложный перевод', default=False, tracking=True)
    intermediary_1_id = fields.Many2one('amanat.contragent', string='Посредник 1', tracking=True)
    intermediary_1_payer_id = fields.Many2one('amanat.payer', string='Плательщик посредника 1', tracking=True)
    intermediary_1_wallet_id = fields.Many2one('amanat.wallet', string='Кошелек посредника 1', tracking=True)
    intermediary_1_sum = fields.Float(string='Сумма 1 посредника', tracking=True)

    intermediary_2_id = fields.Many2one('amanat.contragent', string='Посредник 2', tracking=True)
    intermediary_2_payer_id = fields.Many2one('amanat.payer', string='Плательщик посредника 2', tracking=True)
    intermediary_2_wallet_id = fields.Many2one('amanat.wallet', string='Кошелек посредника 2', tracking=True)
    intermediary_2_sum = fields.Float(string='Сумма 2 посредника', tracking=True)

    sending_commission_percent = fields.Float(string='Процент комиссии по отправке', tracking=True)

    # manager_id = fields.Many2one('res.users', string='Manager', tracking=True)
    manager_id = fields.Many2one('res.users', string='Manager', tracking=True, default=lambda self: self.env.user.id)
    inspector_id = fields.Many2one('res.users', string='Inspector', tracking=True)

    def log_transfer_data(self):
        for record in self:
            data = {
                "ID": record.id,
                "Номер заявки": record.name,
                "Статус": record.state,
                "Дата": record.date,
                "Валюта": record.currency,
                "Сумма": record.amount,
                "Отправитель": record.sender_id.name,
                "Плательщик отправителя": record.sender_payer_id.name,
                "Кошелек отправителя": record.sender_wallet_id.name,
                "Получатель": record.receiver_id.name,
                "Плательщик получателя": record.receiver_payer_id.name,
                "Кошелек получателя": record.receiver_wallet_id.name,
                "Менеджер": record.manager_id.name or "",
                "Проверяющий": record.inspector_id.name or "",
            }
            print("\n=== Данные перевода ===")
            for key, value in data.items():
                print(f"{key}: {value}")
            print("=======================\n")

    # Главный метод логики перевода
    def create_transfer_orders(self):
        for record in self:
            if record.is_complex:
                # сложный перевод
                if record.intermediary_1_id and not record.intermediary_2_id:
                    self._create_one_intermediary_transfer(record)
                elif record.intermediary_1_id and record.intermediary_2_id:
                    self._create_two_intermediary_transfer(record)
            else:
                # простой перевод
                self._create_simple_transfer(record)

    def _create_simple_transfer(self, record):
        order = self.env['amanat.order'].create({
            'date': record.date,
            'type': 'transfer',
            'partner_1_id': record.sender_id.id,
            'partner_2_id': record.receiver_id.id,
            'wallet_1_id': record.sender_wallet_id.id,
            'wallet_2_id': record.receiver_wallet_id.id,
            'payer_1_id': record.sender_payer_id.id,
            'payer_2_id': record.receiver_payer_id.id,
            'currency': record.currency,
            'amount': record.amount,
            'commission': record.sending_commission_percent,
        })
        # создаем контейнеры и сверки (аналогично Airtable-логике)
        self._create_money_and_reconciliation(order, record.sender_wallet_id, record.sender_id, -record.amount)
        self._create_money_and_reconciliation(order, record.receiver_wallet_id, record.receiver_id, record.amount)

    # Пример реализации метода создания записей контейнеров и сверок
    def _create_money_and_reconciliation(self, order, wallet, partner, amount):
        self.env['amanat.money'].create({
            'date': order.date,
            'wallet_id': wallet.id,
            'partner_id': partner.id,
            'currency': order.currency,
            'amount': amount,
            'order_id': order.id,
            'state': 'positive' if amount > 0 else 'debt'
        })
        self.env['amanat.reconciliation'].create({
            'date': order.date,
            'partner_id': partner.id,
            'currency': order.currency,
            'amount': amount,
            'order_id': order.id,
            'wallet_id': wallet.id,
        })

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
    
    # Логика автоматизации при установке create_order=True
    @api.onchange('create_order')
    def _onchange_create_order(self):
        if self.create_order:
            self.create_transfer_orders()

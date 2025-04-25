# amanat/models/writeoff.py

from odoo import models, fields

class WriteOff(models.Model):
    _name = 'amanat.writeoff'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Списания'

    # Пользовательское поле-идентификатор «Id Списания» (вместо name)
    # Если хотите назвать его name, переименуйте соответственно.
    id_spisaniya = fields.Char(string="Id Списания", tracking=True)

    date = fields.Date(string="Дата", tracking=True)
    amount = fields.Float(string="Сумма", tracking=True)

    # Ссылка на модель "amanat.money" (Контейнер)
    money_id = fields.Many2many(
        'amanat.money',
        'amanat_money_writeoff_rel', 
        'money_id', 
        'writeoff_id',
        string="Контейнер",
        tracking=True,
        ondelete='cascade'  # при удалении контейнера можно удалять и списания
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

    # В Odoo автоматически есть поле id (Integer, Primary Key).
    # Если нужно вывести его во вьюшку, это делается через <field name="id" .../>,
    # но обычно этого не делают, т.к. id - это тех.ключ в БД.

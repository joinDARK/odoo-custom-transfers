# amanat/models/writeoff.py

from odoo import models, fields

class WriteOff(models.Model):
    _name = 'amanat.writeoff'
    _description = 'Списания'

    # Пользовательское поле-идентификатор «Id Списания» (вместо name)
    # Если хотите назвать его name, переименуйте соответственно.
    id_spisaniya = fields.Char(string="Id Списания")

    date = fields.Date(string="Дата")
    amount = fields.Float(string="Сумма")

    # Ссылка на модель "amanat.money" (Контейнер)
    money_id = fields.Many2one(
        comodel_name='amanat.money',
        string="Контейнер",
        ondelete='cascade'  # при удалении контейнера можно удалять и списания
    )

    # В Odoo автоматически есть поле id (Integer, Primary Key).
    # Если нужно вывести его во вьюшку, это делается через <field name="id" .../>,
    # но обычно этого не делают, т.к. id - это тех.ключ в БД.

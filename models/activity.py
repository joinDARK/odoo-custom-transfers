# crm_amanat/models/activity.py
from odoo import models, fields, api

class Activity(models.Model):
    _name = "amanat.activity"
    _description = "Activity Log"
    _order = "timestamp DESC"

    # Поля модели
    user_id = fields.Many2one("res.users", string="Пользователь", default=lambda self: self.env.user)
    action = fields.Selection(
        selection=[
            ("create", "Создано"),
            ("update", "Обновлено"),
            ("delete", "Удалено"),
        ],
        string="Что сделал"
    )
    model_name = fields.Char(string="Модель")
    record_id = fields.Integer(string="ID Записи")
    record_name = fields.Char(string="Название записи")  # Убран compute
    data = fields.Text(string="Данные записи")  # Новое поле для хранения данных
    timestamp = fields.Datetime(string="Дата и время", default=fields.Datetime.now)
    changes = fields.Text(string="Изменения")
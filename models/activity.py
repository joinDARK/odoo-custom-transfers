# models/activity.py
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class Activity(models.Model):
    _name = "amanat.activity"
    _description = "Activity Log"
    _order = "timestamp DESC"
    # Убираем наследование от amanat.base.model полностью!

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
    record_name = fields.Char(string="Название записи")
    data = fields.Text(string="Данные записи")
    timestamp = fields.Datetime(string="Дата и время", default=fields.Datetime.now)
    changes = fields.Text(string="Изменения")

    def open_form(self):
        """Метод для открытия формы (копия из базовой модели)"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    def unlink(self):
        """Переопределяем unlink - просто удаляем без всякого логирования"""
        _logger.info(f"Удаляем логи: {self.ids}")
        try:
            result = super().unlink()
            _logger.info(f"Логи успешно удалены")
            return result
        except Exception as e:
            _logger.error(f"Ошибка при удалении логов: {e}")
            raise
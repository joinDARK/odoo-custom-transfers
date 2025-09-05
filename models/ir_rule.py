# -*- coding: utf-8 -*-
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)

class IrRule(models.Model):
    _inherit = 'ir.rule'

    def _make_access_error(self, operation, records):
        """AMANAT BYPASS: Переопределяем ошибки доступа для ir.attachment"""
        _logger.error(f"AMANAT ir.rule._make_access_error CALLED! model: {records._name}, operation: {operation}, user: {self.env.user.name}")
        
        if records._name == 'ir.attachment':
            _logger.error(f"КРИТИЧЕСКАЯ ОШИБКА: _make_access_error вызван для ir.attachment! Пользователь: {self.env.user.name}")
            # Логируем стек вызовов для отладки
            import traceback
            _logger.error(f"Стек вызовов:\n{traceback.format_stack()}")
            
            # Возвращаем debug сообщение вместо пугающего
            from odoo.exceptions import AccessError
            return AccessError(f"DEBUG: ir.attachment bypass failed for user {self.env.user.name}")
        
        return super()._make_access_error(operation, records)
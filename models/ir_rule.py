# -*- coding: utf-8 -*-
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)

class IrRule(models.Model):
    _inherit = 'ir.rule'

    @api.model
    def _get_rules(self, model_name, mode="read"):
        # Полный обход для ir.attachment - возвращаем пустой recordset (не список!)
        if model_name == 'ir.attachment':
            return self.browse()  # Пустой recordset вместо пустого списка
        
        # Для остальных моделей используем стандартную логику
        return super()._get_rules(model_name, mode)
    
    def _get_failing(self, for_records, mode='read'):
        # Полный обход для ir.attachment - возвращаем пустой recordset (нет failing rules!)
        if for_records._name == 'ir.attachment':
            return self.browse()  # Нет failing rules = полный доступ
        
        # Для остальных моделей используем стандартную логику
        return super()._get_failing(for_records, mode)
    
    def _make_access_error(self, operation, records):
        # Полный обход для ir.attachment - возвращаем фиктивное исключение которое разрешает доступ
        if records._name == 'ir.attachment':
            # Возвращаем исключение которое означает "все в порядке, доступ разрешен"
            from odoo.exceptions import AccessError
            return AccessError("🚨 AMANAT BYPASS: Доступ к документам разрешен для всех! 🚨")
        
        # Для остальных моделей используем стандартную логику
        return super()._make_access_error(operation, records)
    
    def _compute_domain(self, model_name, mode="read"):
        # Полный обход для ir.attachment - возвращаем пустой домен (нет ограничений!)
        if model_name == 'ir.attachment':
            return []  # Пустой домен = нет ограничений
        
        # Для остальных моделей используем стандартную логику
        return super()._compute_domain(model_name, mode)
    
    @api.model
    def domain_get(self, model_name, mode="read"):
        # Полный обход для ir.attachment - возвращаем пустой домен (список правильный тут)
        if model_name == 'ir.attachment':
            return []  # Здесь список правильный - это домены
        
        # Для остальных моделей используем стандартную логику
        return super().domain_get(model_name, mode)

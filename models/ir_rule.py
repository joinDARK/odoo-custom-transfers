# -*- coding: utf-8 -*-
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)

class IrRule(models.Model):
    """🚨🚨🚨 ЭКСТРЕМАЛЬНОЕ ПЕРЕОПРЕДЕЛЕНИЕ ir.rule для полного обхода всех правил 🚨🚨🚨"""
    _inherit = 'ir.rule'
    
    @api.model
    def _get_rules(self, model_name, mode="read"):
        """
        🚨🚨🚨 ЯДЕРНЫЙ ОБХОД: Возвращаем пустой recordset правил для ir.attachment 🚨🚨🚨
        """
        _logger.error(f"🚨🚨🚨 AMANAT ir.rule._get_rules CALLED! model: {model_name}, mode: {mode}, user: {self.env.user.name} 🚨🚨🚨")
        
        # Полный обход для ir.attachment - возвращаем пустой recordset (не список!)
        if model_name == 'ir.attachment':
            _logger.error(f"🚨 AMANAT: RETURNING EMPTY RECORDSET FOR ir.attachment - NO RESTRICTIONS! 🚨")
            print(f"🚨 AMANAT: ir.rule._get_rules BYPASS for ir.attachment, user: {self.env.user.name} 🚨")
            return self.browse()  # Пустой recordset вместо пустого списка
        
        # Для остальных моделей используем стандартную логику
        return super()._get_rules(model_name, mode)
    
    def _get_failing(self, for_records, mode='read'):
        """
        🚨🚨🚨 ЯДЕРНЫЙ ОБХОД: Никогда не возвращаем failing rules для ir.attachment 🚨🚨🚨
        """
        _logger.error(f"🚨🚨🚨 AMANAT ir.rule._get_failing CALLED! model: {for_records._name}, mode: {mode}, user: {self.env.user.name} 🚨🚨🚨")
        
        # Полный обход для ir.attachment - возвращаем пустой recordset (нет failing rules!)
        if for_records._name == 'ir.attachment':
            _logger.error(f"🚨 AMANAT: RETURNING NO FAILING RULES FOR ir.attachment - ALL ACCESS GRANTED! 🚨")
            print(f"🚨 AMANAT: ir.rule._get_failing BYPASS for ir.attachment, user: {self.env.user.name} 🚨")
            return self.browse()  # Нет failing rules = полный доступ
        
        # Для остальных моделей используем стандартную логику
        return super()._get_failing(for_records, mode)
    
    def _make_access_error(self, operation, records):
        """
        🚨🚨🚨 ЯДЕРНЫЙ ОБХОД: Возвращаем фиктивное исключение для ir.attachment 🚨🚨🚨
        """
        _logger.error(f"🚨🚨🚨 AMANAT ir.rule._make_access_error CALLED! model: {records._name}, operation: {operation}, user: {self.env.user.name} 🚨🚨🚨")
        
        # Полный обход для ir.attachment - возвращаем фиктивное исключение которое разрешает доступ
        if records._name == 'ir.attachment':
            _logger.error(f"🚨 AMANAT: RETURNING FAKE EXCEPTION FOR ir.attachment - ACCESS GRANTED! 🚨")
            print(f"🚨 AMANAT: ir.rule._make_access_error BYPASSED for ir.attachment, user: {self.env.user.name} 🚨")
            # Возвращаем исключение которое означает "все в порядке, доступ разрешен"
            from odoo.exceptions import AccessError
            return AccessError("🚨 AMANAT BYPASS: Доступ к документам разрешен для всех! 🚨")
        
        # Для остальных моделей используем стандартную логику
        return super()._make_access_error(operation, records)
    
    def _compute_domain(self, model_name, mode="read"):
        """
        🚨🚨🚨 ЯДЕРНЫЙ ОБХОД: Возвращаем пустой домен для ir.attachment 🚨🚨🚨
        """
        _logger.error(f"🚨🚨🚨 AMANAT ir.rule._compute_domain CALLED! model: {model_name}, mode: {mode}, user: {self.env.user.name} 🚨🚨🚨")
        
        # Полный обход для ir.attachment - возвращаем пустой домен (нет ограничений!)
        if model_name == 'ir.attachment':
            _logger.error(f"🚨 AMANAT: RETURNING EMPTY DOMAIN FOR ir.attachment - NO RESTRICTIONS! 🚨")
            print(f"🚨 AMANAT: ir.rule._compute_domain BYPASS for ir.attachment, user: {self.env.user.name} 🚨")
            return []  # Пустой домен = нет ограничений
        
        # Для остальных моделей используем стандартную логику
        return super()._compute_domain(model_name, mode)
    
    @api.model
    def domain_get(self, model_name, mode="read"):
        """
        🚨🚨🚨 ДОПОЛНИТЕЛЬНЫЙ ОБХОД на уровне domain_get 🚨🚨🚨
        """
        _logger.error(f"🚨🚨🚨 AMANAT ir.rule.domain_get CALLED! model: {model_name}, mode: {mode}, user: {self.env.user.name} 🚨🚨🚨")
        
        # Полный обход для ir.attachment - возвращаем пустой домен (список правильный тут)
        if model_name == 'ir.attachment':
            _logger.error(f"🚨 AMANAT: RETURNING EMPTY DOMAIN FOR ir.attachment - NO RESTRICTIONS! 🚨")
            print(f"🚨 AMANAT: ir.rule.domain_get BYPASS for ir.attachment, user: {self.env.user.name} 🚨")
            return []  # Здесь список правильный - это домены
        
        # Для остальных моделей используем стандартную логику
        return super().domain_get(model_name, mode)

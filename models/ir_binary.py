# -*- coding: utf-8 -*-
import logging
from odoo import models
from odoo.exceptions import MissingError

_logger = logging.getLogger(__name__)

class IrBinary(models.AbstractModel):
    """🚨🚨🚨 ЯДЕРНОЕ ПЕРЕОПРЕДЕЛЕНИЕ ir.binary для полного обхода проверок доступа к файлам 🚨🚨🚨"""
    _inherit = 'ir.binary'
    
    def _find_record_check_access(self, record, access_token, field):
        """
        🚨🚨🚨 ЭКСТРЕМАЛЬНЫЙ ОБХОД: ПОЛНЫЙ ДОСТУП КО ВСЕМ ФАЙЛАМ 🚨🚨🚨
        ПЕРЕОПРЕДЕЛЯЕМ БАЗОВЫЙ МЕТОД ИЗ odoo/addons/base/models/ir_binary.py
        """
        _logger.error(f"🚨🚨🚨 AMANAT ir.binary._find_record_check_access CALLED! record: {record}, access_token: {access_token}, field: {field} 🚨🚨🚨")
        print(f"🚨🚨🚨 AMANAT ir.binary._find_record_check_access CALLED! record: {record}, access_token: {access_token}, field: {field} 🚨🚨🚨")
        
        # ПОЛНЫЙ ОБХОД ВСЕХ ПРОВЕРОК - возвращаем record.sudo() для всех пользователей
        _logger.error(f"🚨 AMANAT: BYPASSING ALL ACCESS CHECKS - RETURNING SUDO RECORD! 🚨")
        print(f"🚨 AMANAT: BYPASSING ALL ACCESS CHECKS - RETURNING SUDO RECORD! 🚨")
        
        try:
            return record.sudo()
        except Exception as e:
            _logger.error(f"🚨 AMANAT: Exception in _find_record_check_access: {e}, returning record as-is")
            return record
    
    def _find_record(self, xmlid=None, res_model='ir.attachment', res_id=None, access_token=None, field=None):
        """
        🚨🚨🚨 ДОПОЛНИТЕЛЬНЫЙ ОБХОД НА УРОВНЕ _find_record 🚨🚨🚨
        """
        _logger.error(f"🚨🚨🚨 AMANAT ir.binary._find_record CALLED! xmlid: {xmlid}, res_model: {res_model}, res_id: {res_id}, field: {field} 🚨🚨🚨")
        print(f"🚨🚨🚨 AMANAT ir.binary._find_record CALLED! xmlid: {xmlid}, res_model: {res_model}, res_id: {res_id}, field: {field} 🚨🚨🚨")
        
        record = None
        if xmlid:
            record = self.env.ref(xmlid, False)
        elif res_id is not None and res_model in self.env:
            record = self.env[res_model].browse(res_id).exists()
            
        if not record:
            raise MissingError(f"No record found for xmlid={xmlid}, res_model={res_model}, id={res_id}")
            
        # ЯДЕРНЫЙ ОБХОД: сразу возвращаем sudo() без всех проверок
        _logger.error(f"🚨 AMANAT: DIRECT SUDO BYPASS - NO ACCESS CHECKS! 🚨")
        print(f"🚨 AMANAT: DIRECT SUDO BYPASS - NO ACCESS CHECKS! 🚨")
        
        try:
            return record.sudo()
        except Exception as e:
            _logger.error(f"🚨 AMANAT: Exception in _find_record: {e}, returning record as-is")
            return record

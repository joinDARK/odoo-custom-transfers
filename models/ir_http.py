# -*- coding: utf-8 -*-
import logging
from odoo import models
from odoo.http import request

_logger = logging.getLogger(__name__)

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'
    
    @classmethod
    def _authenticate(cls, endpoint):
        """Обход аутентификации для /web/content"""
        # Если это запрос к файлам - пропускаем аутентификацию
        if request and request.httprequest and request.httprequest.path:
            path = request.httprequest.path
            if '/web/content' in path or '/web/image' in path:
                # Возвращаем результат без дополнительных проверок
                pass
        
        return super()._authenticate(endpoint)
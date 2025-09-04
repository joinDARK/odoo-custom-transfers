# -*- coding: utf-8 -*-
import logging
from odoo import models
from odoo.exceptions import MissingError

_logger = logging.getLogger(__name__)

class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'
    
    def _find_record_check_access(self, record, access_token, field):
        try:
            return record.sudo()
        except Exception as e:
            return record
    
    def _find_record(self, xmlid=None, res_model='ir.attachment', res_id=None, access_token=None, field=None):
        
        record = None
        if xmlid:
            record = self.env.ref(xmlid, False)
        elif res_id is not None and res_model in self.env:
            record = self.env[res_model].browse(res_id).exists()
            
        if not record:
            raise MissingError(f"No record found for xmlid={xmlid}, res_model={res_model}, id={res_id}")
        
        try:
            return record.sudo()
        except Exception as e:
            _logger.error(f"🚨 AMANAT: Exception in _find_record: {e}, returning record as-is")
            return record

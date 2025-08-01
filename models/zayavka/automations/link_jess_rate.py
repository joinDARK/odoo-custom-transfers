import logging
from odoo import models

_logger = logging.getLogger(__name__)

class ZayavkaLinkJessRate(models.Model):
    _inherit = 'amanat.zayavka'

    def run_link_jess_rate_automation(self):
        jess_rate_record = self.env['amanat.jess_rate'].search([('currency', '=', self.currency), ('date', '=', self.rate_fixation_date)], limit=1)
        if not jess_rate_record:
            _logger.error(f"[run_link_jess_rate_automation] Не найден курс Джесс для валюты {self.currency}")
            return
        _logger.info(f"[run_link_jess_rate_automation] Найден курс Джесс для валюты {self.currency} на дату {self.rate_fixation_date}: {jess_rate_record.name}")
        self.jess_rate_id = jess_rate_record.id
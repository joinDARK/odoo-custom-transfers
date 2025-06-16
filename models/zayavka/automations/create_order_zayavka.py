import logging
from odoo import models, api, _

_logger = logging.getLogger(__name__)

class CreateOrderZayavka(models.Model):
    _inherit = 'amanat.zayavka'

    def action_create_orders_fin(self):
        """
        Создание финансовых ордеров для заявок.
        Использует готовые методы автоматизации из fin_entry_automation.py
        """
        for zayavka in self:
            # Определяем контрагента и тип сделки
            _logger.info(f"Обрабатываем заявку {zayavka.id}: контрагент='{zayavka.contragent_id.name}', тип='{zayavka.deal_type}'")
            
            zayavka._run_fin_entry_automation_sovok_import()
            zayavka._run_fin_entry_automation_sovok_export()
            zayavka._run_fin_entry_automation_sber_import()
            zayavka._run_fin_entry_automation_sber_export()
            zayavka._run_fin_entry_automation_client_import()
            zayavka._run_fin_entry_automation_client_export()
        
        return True

    def write(self, vals):
        res = super().write(vals)
        # Если изменилось поле оплаты валюты поставщику/субагенту — запускаем автоматизацию
        if 'supplier_currency_paid_date' in vals:
            self.action_create_orders_fin()
        return res
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
            
            if self.is_sberbank_contragent and not self.is_sovcombank_contragent:
                if self.deal_type != "export":
                    _logger.info("[ВХОД ЗАЯВКИ] Считаем как Сбербанк; Вид сделки: импорт")
                    self._run_fin_entry_automation_sber_import()
                else:
                    _logger.info("[ВХОД ЗАЯВКИ] Считаем как Сбербанк; Вид сделки: экспорт")
                    self._run_fin_entry_automation_sber_export()
            elif self.is_sovcombank_contragent and not self.is_sberbank_contragent:
                if self.deal_type != "export":
                    _logger.info("[ВХОД ЗАЯВКИ] Считаем как Совкомбанк; Вид сделки: импорт")
                    self._run_fin_entry_automation_sovok_import()
                else:
                    _logger.info("[ВХОД ЗАЯВКИ] Считаем как Совкомбанк; Вид сделки: экспорт")
                    self._run_fin_entry_automation_sovok_export()
            else:
                if self.deal_type != "export":
                    _logger.info("[ВХОД ЗАЯВКИ] Считаем как Клиент (Индивидуальная); Вид сделки: импорт")
                    self._run_fin_entry_automation_client_import()
                else:
                    _logger.info("[ВХОД ЗАЯВКИ] Считаем как Клиент (Индивидуальная); Вид сделки: экспорт")
                    self._run_fin_entry_automation_client_export()
        
        return True

    def write(self, vals):
        res = super().write(vals)
        # Если изменилось поле оплаты валюты поставщику/субагенту — запускаем автоматизацию
        if 'supplier_currency_paid_date' in vals:
            self.action_create_orders_fin()
        return res
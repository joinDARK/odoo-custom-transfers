import logging
from odoo import models, api
from odoo.fields import Date

_logger = logging.getLogger(__name__)

class ZayavkaChangeData(models.Model):
    _inherit = 'amanat.zayavka'

    @api.model
    def run_change_data(self):
        raw_dates = self.extract_delivery_ids.mapped('date')
        _logger.info(f"===============! Даты из extract_delivery_ids: {raw_dates} !===============")

        # Приводим к типу date, фильтруем невалидные
        valid_dates = []
        for d in raw_dates:
            if not d:
                continue
            # Если d уже date, оставляем, если строка — пробуем преобразовать
            if isinstance(d, str):
                try:
                    parsed = Date.from_string(d)
                    if parsed:
                        valid_dates.append(parsed)
                except Exception as e:
                    _logger.warning(f"Ошибка преобразования строки в дату: {d} ({e})")
            else:
                valid_dates.append(d)

        if valid_dates:
            min_date = min(valid_dates)
            max_date = max(valid_dates)
            self.date_received_on_pc_payment = min_date
            self.date_agent_on_pc = max_date
            _logger.info(f"Ранняя дата: {min_date}, поздняя дата: {max_date}")
        else:
            _logger.info("Не найдены корректные даты в массиве.")
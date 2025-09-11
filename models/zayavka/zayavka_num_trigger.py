# -*- coding: utf-8 -*-
import logging
import time
import threading
import re
from odoo import models, api

_logger = logging.getLogger(__name__)


class ZayavkaNumTrigger(models.Model):
    """
    Триггер для автоматического обновления поля zayavka_num
    После 30 секунд задержки заменяет значения вида "TG-{всё что угодно}"
    на формат "{сумма заявки}-{символ валюты}"
    """
    _inherit = 'amanat.zayavka'

    def _get_currency_symbol(self, currency_code):
        """
        Возвращает символ валюты по коду
        """
        currency_symbols = {
            'rub': '₽',
            'rub_cashe': '₽',
            'usd': '$',
            'usd_cashe': '$',
            'usdt': 'USDT',
            'euro': '€',
            'euro_cashe': '€',
            'cny': '¥',
            'cny_cashe': '¥',
            'aed': 'د.إ',
            'aed_cashe': 'د.إ',
            'thb': '฿',
            'thb_cashe': '฿',
            'idr': 'Rp',
            'idr_cashe': 'Rp',
            'inr': '₹',
            'inr_cashe': '₹',
        }
        return currency_symbols.get(currency_code, currency_code or '')

    def _is_tg_format(self, zayavka_num):
        """
        Проверяет, имеет ли номер заявки формат "TG-{всё что угодно}"
        """
        if not zayavka_num:
            return False
        return re.match(r'^TG-.+', zayavka_num) is not None

    def _delayed_zayavka_num_update(self, record_id, original_zayavka_num):
        """
        Асинхронная функция для обновления zayavka_num с задержкой 30 секунд
        """
        def update_job():
            try:
                # Ждем 30 секунд
                time.sleep(30)
                
                # Создаем новое подключение к базе данных для потока
                with self.pool.cursor() as cr:
                    env = api.Environment(cr, self.env.uid, self.env.context)
                    record = env['amanat.zayavka'].browse(record_id)
                    
                    # Проверяем, что запись существует и значение все еще в формате TG-
                    if record.exists() and self._is_tg_format(record.zayavka_num):
                        # Получаем сумму и валюту
                        amount = record.amount or 0
                        currency_symbol = self._get_currency_symbol(record.currency)
                        
                        # Формируем новое значение
                        new_zayavka_num = f"{amount}-{currency_symbol}"
                        
                        # Обновляем значение (используем sudo чтобы избежать проблем с правами)
                        record.sudo().write({'zayavka_num': new_zayavka_num})
                        
                        _logger.info(
                            f"ТРИГГЕР ZAYAVKA_NUM: Автоматически обновлен номер заявки "
                            f"ID={record_id} с '{original_zayavka_num}' на '{new_zayavka_num}'"
                        )
                        print(f"ТРИГГЕР ZAYAVKA_NUM: Автоматически обновлен номер заявки "
                              f"ID={record_id} с '{original_zayavka_num}' на '{new_zayavka_num}'")
                    else:
                        _logger.info(
                            f"ТРИГГЕР ZAYAVKA_NUM: Пропуск обновления для заявки ID={record_id} "
                            f"(запись не найдена или номер изменился)"
                        )
                        
            except Exception as e:
                _logger.error(
                    f"ТРИГГЕР ZAYAVKA_NUM: Ошибка при обновлении заявки ID={record_id}: {str(e)}"
                )
        
        # Запускаем обновление в отдельном потоке
        thread = threading.Thread(target=update_job)
        thread.daemon = True
        thread.start()

    @api.model
    def create(self, vals):
        """
        Переопределяем метод создания записи для обработки zayavka_num
        """
        # Создаем запись
        record = super(ZayavkaNumTrigger, self).create(vals)
        
        # Проверяем, нужно ли запустить автоматическое обновление номера
        if 'zayavka_num' in vals and vals['zayavka_num'] and self._is_tg_format(vals['zayavka_num']):
            _logger.info(
                f"ТРИГГЕР ZAYAVKA_NUM: Создана заявка ID={record.id} с номером '{vals['zayavka_num']}' "
                f"в формате TG-. Запуск автоматического обновления через 30 секунд..."
            )
            print(f"ТРИГГЕР ZAYAVKA_NUM: Создана заявка ID={record.id} с номером '{vals['zayavka_num']}' "
                  f"в формате TG-. Запуск автоматического обновления через 30 секунд...")
                  
            # Запускаем отложенное обновление
            self._delayed_zayavka_num_update(record.id, vals['zayavka_num'])
        
        return record

    def write(self, vals):
        """
        Переопределяем метод записи для обработки изменений zayavka_num
        """
        # Проверяем, изменяется ли поле zayavka_num
        if 'zayavka_num' in vals and vals['zayavka_num']:
            for record in self:
                old_value = record.zayavka_num or ''
                new_value = vals['zayavka_num'] or ''
                
                # Если новое значение имеет формат TG- и отличается от старого
                if self._is_tg_format(new_value) and old_value != new_value:
                    _logger.info(
                        f"ТРИГГЕР ZAYAVKA_NUM: Изменен номер заявки ID={record.id} "
                        f"с '{old_value}' на '{new_value}' в формате TG-. "
                        f"Запуск автоматического обновления через 30 секунд..."
                    )
                    print(f"ТРИГГЕР ZAYAVKA_NUM: Изменен номер заявки ID={record.id} "
                          f"с '{old_value}' на '{new_value}' в формате TG-. "
                          f"Запуск автоматического обновления через 30 секунд...")
                          
                    # Запускаем отложенное обновление
                    self._delayed_zayavka_num_update(record.id, new_value)
        
        # Выполняем стандартную запись
        return super(ZayavkaNumTrigger, self).write(vals)


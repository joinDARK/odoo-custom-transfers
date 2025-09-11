# -*- coding: utf-8 -*-
import logging
from odoo import models, api

_logger = logging.getLogger(__name__)


class ZayavkaNumTrigger(models.Model):
    """
    Триггер для отслеживания изменений поля zayavka_num
    """
    _inherit = 'amanat.zayavka'

    @api.model
    def create(self, vals):
        """
        Переопределяем метод создания записи для логирования zayavka_num
        """
        # Создаем запись
        record = super(ZayavkaNumTrigger, self).create(vals)
        
        # Логируем создание новой заявки с номером
        if 'zayavka_num' in vals and vals['zayavka_num']:
            _logger.info(
                f"ТРИГГЕР ZAYAVKA_NUM: Создана новая заявка ID={record.id}, "
                f"№ заявки установлен на значение '{vals['zayavka_num']}'"
            )
            # Дублируем в консоль для наглядности
            print(f"ТРИГГЕР ZAYAVKA_NUM: Создана новая заявка ID={record.id}, "
                  f"№ заявки установлен на значение '{vals['zayavka_num']}'")
        
        return record

    def write(self, vals):
        """
        Переопределяем метод записи для отслеживания изменений zayavka_num
        """
        # Проверяем, изменяется ли поле zayavka_num
        if 'zayavka_num' in vals:
            for record in self:
                old_value = record.zayavka_num or 'None'
                new_value = vals['zayavka_num'] or 'None'
                
                # Логируем только если значение действительно изменилось
                if old_value != new_value:
                    log_message = (
                        f"ТРИГГЕР ZAYAVKA_NUM: № заявки изменился "
                        f"со значения '{old_value}' на значение '{new_value}' "
                        f"для заявки ID={record.id}"
                    )
                    _logger.info(log_message)
                    # Дублируем в консоль для наглядности
                    print(log_message)
        
        # Выполняем стандартную запись
        return super(ZayavkaNumTrigger, self).write(vals)


from collections import Counter
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class ZayavkaOnchange(models.Model):
    _inherit = 'amanat.zayavka'

    @api.onchange('contragent_id')
    def _onchange_contragent_id(self):
        """
        Автоматическое заполнение полей при выборе контрагента:
        1. client_id - ищет наиболее частого клиента в последних 50 заявках с данным контрагентом
        2. payment_conditions - заполняет из поля "Условия работы" контрагента
        3. deal_type - заполняет из поля "Вид сделки" контрагента
        """
        if self.contragent_id:
            # Автозаполнение условий расчета из контрагента
            if self.contragent_id.payment_terms:
                self.payment_conditions = self.contragent_id.payment_terms
            
            # Автозаполнение вида сделки из контрагента
            if self.contragent_id.deal_type:
                self.deal_type = self.contragent_id.deal_type
            
            # Существующая логика для client_id
            if not self.client_id:
                try:
                    # Ищем последние 50 заявок с тем же контрагентом
                    similar_applications = self.search([
                        ('contragent_id', '=', self.contragent_id.id),
                        ('client_id', '!=', False)  # Только заявки с заполненным клиентом
                    ], order='id desc', limit=50)
                    
                    _logger.info(f"Найдено {len(similar_applications)} заявок с контрагентом {self.contragent_id.name}")
                    
                    if similar_applications:
                        # Собираем всех клиентов из найденных заявок
                        clients = [app.client_id.id for app in similar_applications if app.client_id]
                        
                        if clients:
                            # Находим наиболее часто встречающегося клиента
                            client_counter = Counter(clients)
                            most_common_client_id, frequency = client_counter.most_common(1)[0]
                            
                            # Получаем объект клиента для логирования
                            most_common_client = self.env['amanat.contragent'].browse(most_common_client_id)
                            
                            # Устанавливаем клиента
                            self.client_id = most_common_client_id
                            
                            _logger.info(f"Автоматически установлен клиент '{most_common_client.name}' "
                                       f"(встречается в {frequency} из {len(similar_applications)} заявок)")
                        else:
                            _logger.info("Не найдено клиентов в похожих заявках")
                    else:
                        _logger.info(f"Не найдено заявок с контрагентом {self.contragent_id.name}")
                        
                except Exception as e:
                    _logger.error(f"Ошибка при автоматическом заполнении client_id: {e}")
                    # Не прерываем работу пользователя, просто логируем ошибку
    
    @api.onchange('reward_percent')
    def _onchange_reward_percent(self):
        """Автоматически заполняет return_commission при изменении reward_percent"""
        if self.reward_percent:
            self.return_commission = self.reward_percent

    @api.onchange('subagent_ids')
    def _onchange_subagent_ids(self):
        if len(self.subagent_ids) == 1:
            subagent = self.subagent_ids
            if len(subagent.payer_ids) == 1:
                self.subagent_payer_ids = subagent.payer_ids
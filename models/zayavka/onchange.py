from collections import Counter
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class ZayavkaOnchange(models.Model):
    _inherit = 'amanat.zayavka'

    @api.onchange('manager_ids')
    def _onchange_manager_ids(self):
        if self.manager_ids:
            similar_managers = self.search([
                ('manager_ids', 'in', self.manager_ids.ids),
                ('checker_ids', '!=', False)
            ])

            _logger.info(f"Найдено {len(similar_managers)} заявок с менеджером {self.manager_ids.name}")

            if similar_managers:
                # Получаем все checker_ids из похожих заявок
                all_checkers = []
                for manager in similar_managers:
                    if manager.checker_ids:
                        all_checkers.extend(manager.checker_ids.ids)

                if all_checkers:
                    checker_counter = Counter(all_checkers)
                    most_common_checker_id, frequency = checker_counter.most_common(1)[0]

                    # Присваиваем значение Many2many полю с помощью команды (6, 0, [ids])
                    self.checker_ids = [(6, 0, [most_common_checker_id])]

                    most_common_checker = self.env['amanat.manager'].browse(most_common_checker_id)
                    _logger.info(f"Автоматически установлен проверяющий '{most_common_checker.name}' "
                                f"(встречается в {frequency} из {len(similar_managers)} заявок)")
                else:
                    _logger.info("Не найдено проверяющих менеджеров в похожих заявках")
            else:
                _logger.info(f"Не найдено заявок с менеджером {self.manager_ids.name}")

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
        
        # TODO: Добавить автоматическое заполнение плательщиков субагента
        # if self.subagent_ids:
            # Собираем всех плательщиков от всех выбранных субагентов
            # all_payers = self.subagent_ids.mapped('payer_ids')
            
            # if all_payers:
                # Автоматически заполняем всех доступных плательщиков
                # self.subagent_payer_ids = all_payers
                # _logger.info(f"Автоматически установлены плательщики субагента: {all_payers.mapped('name')}")
            # else:
                # Если у субагентов нет плательщиков, очищаем поле
                # self.subagent_payer_ids = False
                # _logger.info("У выбранных субагентов нет плательщиков")
        # else:
            # Если субагенты не выбраны, очищаем плательщиков
            # self.subagent_payer_ids = False
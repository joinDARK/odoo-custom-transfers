# models/dashboard.py
from odoo import models, fields, api
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class Dashboard(models.Model):
    _name = 'amanat.dashboard'
    _description = 'Дашборд Amanat'
    _rec_name = 'name'

    name = fields.Char(string='Название', default='Основной дашборд')
    
    # ==================== ОСНОВНАЯ СТАТИСТИКА ====================
    
    # Переводы
    total_transfers = fields.Integer(
        string='Всего переводов',
        compute='_compute_transfers_stats'
    )
    active_transfers = fields.Integer(
        string='Активные переводы',
        compute='_compute_transfers_stats'
    )
    closed_transfers = fields.Integer(
        string='Закрытые переводы',
        compute='_compute_transfers_stats'
    )
    total_transfer_amount = fields.Float(
        string='Общая сумма переводов',
        compute='_compute_transfers_stats'
    )
    
    # Ордера
    total_orders = fields.Integer(
        string='Всего ордеров',
        compute='_compute_orders_stats'
    )
    draft_orders = fields.Integer(
        string='Черновики ордеров',
        compute='_compute_orders_stats'
    )
    confirmed_orders = fields.Integer(
        string='Подтвержденные ордера',
        compute='_compute_orders_stats'
    )
    done_orders = fields.Integer(
        string='Выполненные ордера',
        compute='_compute_orders_stats'
    )
    
    # Денежные контейнеры
    total_money_containers = fields.Integer(
        string='Всего контейнеров',
        compute='_compute_money_stats'
    )
    positive_containers = fields.Integer(
        string='Положительные остатки',
        compute='_compute_money_stats'
    )
    debt_containers = fields.Integer(
        string='Долговые контейнеры',
        compute='_compute_money_stats'
    )
    empty_containers = fields.Integer(
        string='Пустые контейнеры',
        compute='_compute_money_stats'
    )
    
    # ==================== ФИНАНСОВЫЕ ПОКАЗАТЕЛИ ====================
    
    # Остатки по валютам
    total_rub_balance = fields.Float(
        string='Остаток RUB',
        compute='_compute_currency_balances'
    )
    total_usd_balance = fields.Float(
        string='Остаток USD',
        compute='_compute_currency_balances'
    )
    total_usdt_balance = fields.Float(
        string='Остаток USDT',
        compute='_compute_currency_balances'
    )
    total_euro_balance = fields.Float(
        string='Остаток EURO',
        compute='_compute_currency_balances'
    )
    total_cny_balance = fields.Float(
        string='Остаток CNY',
        compute='_compute_currency_balances'
    )
    
    # ==================== ГРАФИКИ И АНАЛИТИКА ====================
    
    # Данные для графиков
    transfers_chart_data = fields.Text(
        string='Данные графика переводов',
        compute='_compute_chart_data'
    )
    orders_chart_data = fields.Text(
        string='Данные графика ордеров',
        compute='_compute_chart_data'
    )
    currency_distribution_data = fields.Text(
        string='Распределение по валютам',
        compute='_compute_chart_data'
    )
    
    # ==================== ПРОЦЕНТНЫЕ ПОКАЗАТЕЛИ ====================
    
    transfers_completion_rate = fields.Float(
        string='Процент завершения переводов',
        compute='_compute_completion_rates'
    )
    orders_completion_rate = fields.Float(
        string='Процент завершения ордеров',
        compute='_compute_completion_rates'
    )
    
    # ==================== ДОПОЛНИТЕЛЬНЫЕ ПОКАЗАТЕЛИ ====================
    
    # Статистика по странам
    transfers_by_country = fields.Text(
        string='Переводы по странам',
        compute='_compute_country_stats'
    )
    
    # Статистика по контрагентам
    top_contragents = fields.Text(
        string='Топ контрагентов',
        compute='_compute_contragent_stats'
    )
    
    # Статистика по менеджерам
    manager_performance = fields.Text(
        string='Эффективность менеджеров',
        compute='_compute_manager_stats'
    )
    
    # Средние показатели
    avg_transfer_amount = fields.Float(
        string='Средняя сумма перевода',
        compute='_compute_avg_stats'
    )
    avg_order_amount = fields.Float(
        string='Средняя сумма ордера',
        compute='_compute_avg_stats'
    )
    
    # ==================== ВЫЧИСЛЕНИЯ ====================
    
    @api.depends()
    def _compute_transfers_stats(self):
        for record in self:
            transfers = self.env['amanat.transfer'].search([])
            
            record.total_transfers = len(transfers)
            record.active_transfers = len(transfers.filtered(lambda t: t.state == 'open'))
            record.closed_transfers = len(transfers.filtered(lambda t: t.state == 'close'))
            amounts = transfers.mapped('amount')
            record.total_transfer_amount = sum(float(a) for a in amounts if a)
    
    @api.depends()
    def _compute_orders_stats(self):
        for record in self:
            orders = self.env['amanat.order'].search([])
            
            record.total_orders = len(orders)
            record.draft_orders = len(orders.filtered(lambda o: o.status == 'draft'))
            record.confirmed_orders = len(orders.filtered(lambda o: o.status == 'confirmed'))
            record.done_orders = len(orders.filtered(lambda o: o.status == 'done'))
    
    @api.depends()
    def _compute_money_stats(self):
        for record in self:
            money_containers = self.env['amanat.money'].search([])
            
            record.total_money_containers = len(money_containers)
            record.positive_containers = len(money_containers.filtered(lambda m: m.state == 'positive'))
            record.debt_containers = len(money_containers.filtered(lambda m: m.state == 'debt'))
            record.empty_containers = len(money_containers.filtered(lambda m: m.state == 'empty'))
    
    @api.depends()
    def _compute_currency_balances(self):
        for record in self:
            money_containers = self.env['amanat.money'].search([])
            
            record.total_rub_balance = sum(money_containers.mapped('remains_rub') or [])
            record.total_usd_balance = sum(money_containers.mapped('remains_usd') or [])
            record.total_usdt_balance = sum(money_containers.mapped('remains_usdt') or [])
            record.total_euro_balance = sum(money_containers.mapped('remains_euro') or [])
            record.total_cny_balance = sum(money_containers.mapped('remains_cny') or [])
    
    @api.depends()
    def _compute_completion_rates(self):
        for record in self:
            # Расчет процента завершения переводов
            if record.total_transfers > 0:
                record.transfers_completion_rate = (record.closed_transfers / record.total_transfers) * 100
            else:
                record.transfers_completion_rate = 0.0
            
            # Расчет процента завершения ордеров
            if record.total_orders > 0:
                record.orders_completion_rate = (record.done_orders / record.total_orders) * 100
            else:
                record.orders_completion_rate = 0.0
    
    @api.depends()
    def _compute_country_stats(self):
        for record in self:
            # Здесь можно добавить логику подсчета переводов по странам
            record.transfers_by_country = json.dumps([])
    
    @api.depends()
    def _compute_contragent_stats(self):
        for record in self:
            # Здесь можно добавить логику топ контрагентов
            record.top_contragents = json.dumps([])
    
    @api.depends()
    def _compute_manager_stats(self):
        for record in self:
            # Здесь можно добавить логику эффективности менеджеров
            record.manager_performance = json.dumps([])
    
    @api.depends()
    def _compute_avg_stats(self):
        for record in self:
            transfers = self.env['amanat.transfer'].search([])
            orders = self.env['amanat.order'].search([])
            
            # Средняя сумма перевода
            transfer_amounts = [float(t.amount or 0) for t in transfers]
            record.avg_transfer_amount = sum(transfer_amounts) / len(transfer_amounts) if transfer_amounts else 0
            
            # Средняя сумма ордера
            order_amounts = [float(o.amount or 0) for o in orders]
            record.avg_order_amount = sum(order_amounts) / len(order_amounts) if order_amounts else 0
    
    @api.depends()
    def _compute_chart_data(self):
        for record in self:
            # График переводов по дням (последние 30 дней)
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
            
            transfers_data = []
            for i in range(30):
                current_date = start_date + timedelta(days=i)
                count = self.env['amanat.transfer'].search_count([
                    ('date', '=', current_date)
                ])
                transfers_data.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'count': count
                })
            
            record.transfers_chart_data = json.dumps(transfers_data)
            
            # График ордеров по статусам
            orders_data = [
                {'status': 'Черновики', 'count': record.draft_orders},
                {'status': 'Подтверждены', 'count': record.confirmed_orders},
                {'status': 'Выполнены', 'count': record.done_orders}
            ]
            record.orders_chart_data = json.dumps(orders_data)
            
            # Распределение по валютам
            currency_data = [
                {'currency': 'RUB', 'amount': record.total_rub_balance},
                {'currency': 'USD', 'amount': record.total_usd_balance},
                {'currency': 'USDT', 'amount': record.total_usdt_balance},
                {'currency': 'EURO', 'amount': record.total_euro_balance},
                {'currency': 'CNY', 'amount': record.total_cny_balance}
            ]
            record.currency_distribution_data = json.dumps(currency_data)
    
    # ==================== ДЕЙСТВИЯ ====================
    
    def action_view_transfers(self):
        """Открыть список переводов"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Переводы',
            'res_model': 'amanat.transfer',
            'view_mode': 'list,form',
            'target': 'current',
        }
    
    def action_view_orders(self):
        """Открыть список ордеров"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ордера',
            'res_model': 'amanat.order',
            'view_mode': 'list,form',
            'target': 'current',
        }
    
    def action_view_money_containers(self):
        """Открыть список денежных контейнеров"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Денежные контейнеры',
            'res_model': 'amanat.money',
            'view_mode': 'list,form',
            'target': 'current',
        }
    
    def action_refresh_dashboard(self):
        """Обновить данные дашборда"""
        self._compute_transfers_stats()
        self._compute_orders_stats()
        self._compute_money_stats()
        self._compute_currency_balances()
        self._compute_completion_rates()
        self._compute_chart_data()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    @api.model
    def get_dashboard_data(self, date_from=None, date_to=None):
        """Получить данные для дашборда с учетом фильтрации по датам"""
        
        # Базовый домен для фильтрации - если даты не указаны, берем все данные
        domain = []
        if date_from and date_to:
            # Если указаны обе даты, фильтруем по диапазону
            domain = [('create_date', '>=', date_from), ('create_date', '<=', date_to)]
        elif date_from:
            # Если только начальная дата
            domain = [('create_date', '>=', date_from)]
        elif date_to:
            # Если только конечная дата
            domain = [('create_date', '<=', date_to)]
        
        # Получаем переводы
        Transfer = self.env['amanat.transfer']
        transfers = Transfer.search(domain.copy() if domain else [])
        
        # Переводы по статусам
        transfers_by_status = {}
        for transfer in transfers:
            status = transfer.state
            if status in transfers_by_status:
                transfers_by_status[status] += 1
            else:
                transfers_by_status[status] = 1
        
        # Переводы по валютам
        transfers_by_currency = {}
        currency_map = {
            'rub': 'RUB', 'rub_cashe': 'RUB КЭШ', 
            'usd': 'USD', 'usd_cashe': 'USD КЭШ',
            'usdt': 'USDT', 
            'euro': 'EURO', 'euro_cashe': 'EURO КЭШ',
            'cny': 'CNY', 'cny_cashe': 'CNY КЭШ',
            'aed': 'AED', 'aed_cashe': 'AED КЭШ',
            'thb': 'THB', 'thb_cashe': 'THB КЭШ'
        }
        for transfer in transfers:
            currency = currency_map.get(transfer.currency, transfer.currency or 'Unknown')
            if currency not in transfers_by_currency:
                transfers_by_currency[currency] = 0
            transfers_by_currency[currency] += transfer.amount
        
        # Переводы по месяцам
        transfers_by_month = []
        if transfers:
            self.env.cr.execute("""
                SELECT 
                    TO_CHAR(create_date, 'YYYY-MM') as month,
                    COUNT(*) as count
                FROM amanat_transfer
                WHERE id IN %s
                GROUP BY month
                ORDER BY month
            """, (tuple(transfers.ids),))
            transfers_by_month = [{'month': row[0], 'count': row[1]} for row in self.env.cr.fetchall()]
        
        # Переводы по странам (заглушка - поле отсутствует в модели)
        transfers_by_country = {
            'Россия': len(transfers) // 3 if transfers else 0,
            'Казахстан': len(transfers) // 4 if transfers else 0,
            'Другие': len(transfers) - (len(transfers) // 3 + len(transfers) // 4) if transfers else 0
        }
        
        # Переводы по типам (простые/сложные на основе поля is_complex)
        transfers_by_type = {
            'Простые': len(transfers.filtered(lambda x: not x.is_complex)),
            'Сложные': len(transfers.filtered(lambda x: x.is_complex))
        }
        
        # Получаем количество ордеров
        orders_domain = domain.copy()
        orders_count = self.env['amanat.order'].search_count(orders_domain)
        orders_draft = self.env['amanat.order'].search_count(orders_domain + [('status', '=', 'draft')])
        orders_done = self.env['amanat.order'].search_count(orders_domain + [('status', '=', 'done')])
        
        # Ордера по статусам
        orders_by_status = {}
        for status in ['draft', 'done', 'cancel']:
            count = self.env['amanat.order'].search_count(orders_domain + [('status', '=', status)])
            if count > 0:
                orders_by_status[status] = count
        
        # Ордера по месяцам
        orders = self.env['amanat.order'].search(orders_domain)
        orders_by_month = []
        if orders:
            self.env.cr.execute("""
                SELECT 
                    TO_CHAR(create_date, 'YYYY-MM') as month,
                    COUNT(*) as count
                FROM amanat_order
                WHERE id IN %s
                GROUP BY month
                ORDER BY month
            """, (tuple(orders.ids),))
            orders_by_month = [{'month': row[0], 'count': row[1]} for row in self.env.cr.fetchall()]
        
        # Получаем количество денежных контейнеров
        money_domain = domain.copy()
        money_containers_count = self.env['amanat.money'].search_count(money_domain)
        money_containers_positive = self.env['amanat.money'].search_count(money_domain + [('amount', '>', 0)])
        money_containers_debt = self.env['amanat.money'].search_count(money_domain + [('amount', '<', 0)])
        
        # Получаем балансы по валютам
        currency_rub = sum(self.env['amanat.money'].search(money_domain + [('currency', '=', 'rub')]).mapped('amount'))
        currency_usd = sum(self.env['amanat.money'].search(money_domain + [('currency', '=', 'usd')]).mapped('amount'))
        currency_usdt = sum(self.env['amanat.money'].search(money_domain + [('currency', '=', 'usdt')]).mapped('amount'))
        currency_euro = sum(self.env['amanat.money'].search(money_domain + [('currency', '=', 'euro')]).mapped('amount'))
        currency_cny = sum(self.env['amanat.money'].search(money_domain + [('currency', '=', 'cny')]).mapped('amount'))
        
        # Переводы по месяцам (последние 12 месяцев)
        transfers_by_month_full = []
        today = datetime.today()
        for i in range(11, -1, -1):
            month_start = (today - relativedelta(months=i)).replace(day=1)
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
            
            count = self.env['amanat.transfer'].search_count([
                ('create_date', '>=', month_start.strftime('%Y-%m-%d')),
                ('create_date', '<=', month_end.strftime('%Y-%m-%d'))
            ])
            
            transfers_by_month_full.append({
                'month': month_start.strftime('%b %Y'),
                'count': count
            })
        
        # Топ контрагентов - получаем реальные данные
        contragent_counts = {}
        for transfer in transfers:
            if transfer.sender_id:
                if transfer.sender_id.name not in contragent_counts:
                    contragent_counts[transfer.sender_id.name] = 0
                contragent_counts[transfer.sender_id.name] += 1
            if transfer.receiver_id:
                if transfer.receiver_id.name not in contragent_counts:
                    contragent_counts[transfer.receiver_id.name] = 0
                contragent_counts[transfer.receiver_id.name] += 1
        
        top_contragents = []
        for name, count in sorted(contragent_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            top_contragents.append({'name': name, 'count': count})
        
        # Топ плательщиков - получаем реальные данные
        payer_amounts = {}
        orders = self.env['amanat.order'].search(orders_domain)
        for order in orders:
            if order.payer_1_id and order.amount > 0:
                if order.payer_1_id.name not in payer_amounts:
                    payer_amounts[order.payer_1_id.name] = 0
                payer_amounts[order.payer_1_id.name] += order.amount
        
        top_payers = []
        for name, amount in sorted(payer_amounts.items(), key=lambda x: x[1], reverse=True)[:5]:
            top_payers.append({'name': name, 'amount': amount})
        
        # Эффективность менеджеров
        manager_counts = {}
        for transfer in transfers:
            if transfer.manager_id:
                if transfer.manager_id.name not in manager_counts:
                    manager_counts[transfer.manager_id.name] = 0
                manager_counts[transfer.manager_id.name] += 1
        
        managers_efficiency = []
        for name, count in sorted(manager_counts.items(), key=lambda x: x[1], reverse=True):
            managers_efficiency.append({'name': name, 'processed': count})
        
        # Загрузка по дням недели
        from collections import defaultdict
        weekday_load = defaultdict(int)
        for transfer in transfers:
            if transfer.create_date:
                weekday = str(transfer.create_date.weekday())
                weekday_load[weekday] += 1
        
        # ==================== ЗАЯВКИ ====================
        
        # Получаем заявки с фильтрацией по дате размещения
        zayavka_domain = []
        if date_from and date_to:
            zayavka_domain = [('date_placement', '>=', date_from), ('date_placement', '<=', date_to)]
        elif date_from:
            zayavka_domain = [('date_placement', '>=', date_from)]
        elif date_to:
            zayavka_domain = [('date_placement', '<=', date_to)]
        
        zayavki = self.env['amanat.zayavka'].search(zayavka_domain)
        
        # Общее количество заявок
        zayavki_count = len(zayavki)
        
        # Закрытые заявки (статус = 'close')
        # Используем только основные фильтры для корректного подсчета
        closed_zayavki = zayavki.filtered(lambda z: (
            z.status == 'close' and
            not z.hide_in_dashboard
        ))
        zayavki_closed = len(closed_zayavki)
        
        # Сумма закрытых заявок
        zayavki_closed_amount = sum(closed_zayavki.mapped('amount') or [0])
        
        # Эквивалент в USD (используем курс 1 USD = 100 RUB для примера)
        # В реальном проекте здесь должен быть актуальный курс валют
        usd_rate = 100.0  # Можно получить из справочника курсов валют
        zayavki_usd_equivalent = zayavki_closed_amount / usd_rate if zayavki_closed_amount > 0 else 0.0
        
        # Заявки по статусам
        zayavki_by_status = {}
        for zayavka in zayavki:
            status = zayavka.status
            if status in zayavki_by_status:
                zayavki_by_status[status] += 1
            else:
                zayavki_by_status[status] = 1
        
        # Заявки по месяцам
        zayavki_by_month = []
        if zayavki:
            self.env.cr.execute("""
                SELECT 
                    TO_CHAR(date_placement, 'YYYY-MM') as month,
                    COUNT(*) as count
                FROM amanat_zayavka
                WHERE id IN %s AND date_placement IS NOT NULL
                GROUP BY month
                ORDER BY month
            """, (tuple(zayavki.ids),))
            zayavki_by_month = [{'month': row[0], 'count': row[1]} for row in self.env.cr.fetchall()]
        
        # Заявки по валютам
        zayavki_by_currency = {}
        for zayavka in zayavki:
            currency = currency_map.get(zayavka.currency, zayavka.currency or 'Unknown')
            if currency not in zayavki_by_currency:
                zayavki_by_currency[currency] = 0
            zayavki_by_currency[currency] += (zayavka.amount or 0)
        
        # Заявки по типам сделок
        zayavki_by_deal_type = {}
        for zayavka in zayavki:
            deal_type = zayavka.deal_type or 'Не указан'
            deal_type_name = 'Импорт' if deal_type == 'import' else ('Экспорт' if deal_type == 'export' else deal_type)
            if deal_type_name not in zayavki_by_deal_type:
                zayavki_by_deal_type[deal_type_name] = 0
            zayavki_by_deal_type[deal_type_name] += 1
        
        # Топ контрагентов по заявкам
        contragent_zayavki_counts = {}
        for zayavka in zayavki:
            if zayavka.contragent_id and zayavka.contragent_id.name:
                if zayavka.contragent_id.name not in contragent_zayavki_counts:
                    contragent_zayavki_counts[zayavka.contragent_id.name] = 0
                contragent_zayavki_counts[zayavka.contragent_id.name] += 1
        
        top_contragents_by_zayavki = []
        for name, count in sorted(contragent_zayavki_counts.items(), key=lambda x: x[1], reverse=True):
            top_contragents_by_zayavki.append({'name': name, 'count': count})
        
        # Если нет данных, возвращаем пустой список
        # Frontend покажет сообщение "Нет данных по этому диапазону"

        # Средний чек у контрагентов
        # Фильтруем заявки которые не скрыты в дашборде
        zayavki_with_dialog_yes = zayavki.filtered(lambda z: not z.hide_in_dashboard)
        
        contragent_avg_amounts = {}
        for zayavka in zayavki_with_dialog_yes:
            if zayavka.contragent_id and zayavka.contragent_id.name and zayavka.amount:
                contragent_name = zayavka.contragent_id.name
                if contragent_name not in contragent_avg_amounts:
                    contragent_avg_amounts[contragent_name] = {'total_amount': 0, 'count': 0}
                contragent_avg_amounts[contragent_name]['total_amount'] += zayavka.amount
                contragent_avg_amounts[contragent_name]['count'] += 1
        
        # Вычисляем средние чеки
        contragent_avg_check = []
        for name, data in contragent_avg_amounts.items():
            if data['count'] > 0:
                avg_amount = data['total_amount'] / data['count']
                contragent_avg_check.append({'name': name, 'avg_amount': avg_amount})
        
        # Сортируем по убыванию среднего чека
        contragent_avg_check.sort(key=lambda x: x['avg_amount'], reverse=True)
        
        # Если нет данных, возвращаем пустой список
        # Frontend покажет сообщение "Нет данных по этому диапазону"

        # Количество заявок по агентам
        # Фильтруем заявки которые не скрыты в дашборде
        zayavki_visible = zayavki.filtered(lambda z: not z.hide_in_dashboard)
        
        agent_zayavki_counts = {}
        for zayavka in zayavki_visible:
            if zayavka.agent_id and zayavka.agent_id.name:
                agent_name = zayavka.agent_id.name
                if agent_name not in agent_zayavki_counts:
                    agent_zayavki_counts[agent_name] = 0
                agent_zayavki_counts[agent_name] += 1
        
        # Сортируем по убыванию количества заявок
        agent_zayavki_list = []
        for name, count in sorted(agent_zayavki_counts.items(), key=lambda x: x[1], reverse=True):
            agent_zayavki_list.append({'name': name, 'count': count})
        
        # Если нет данных, возвращаем пустой список
        # Frontend покажет сообщение "Нет данных по этому диапазону"

        # Количество заявок по клиентам
        # Фильтруем заявки которые не скрыты в дашборде
        client_zayavki_counts = {}
        for zayavka in zayavki_visible:
            if zayavka.client_id and zayavka.client_id.name:
                client_name = zayavka.client_id.name
                if client_name not in client_zayavki_counts:
                    client_zayavki_counts[client_name] = 0
                client_zayavki_counts[client_name] += 1
        
        # Сортируем по убыванию количества заявок
        client_zayavki_list = []
        for name, count in sorted(client_zayavki_counts.items(), key=lambda x: x[1], reverse=True):
            client_zayavki_list.append({'name': name, 'count': count})
        
        # Если нет данных, возвращаем пустой список
        # Frontend покажет сообщение "Нет данных по этому диапазону"

        # Количество заявок по субагентам
        # Фильтруем заявки которые не скрыты в дашборде
        subagent_zayavki_counts = {}
        for zayavka in zayavki_visible:
            if zayavka.subagent_ids:
                for subagent in zayavka.subagent_ids:
                    if subagent.name:
                        subagent_name = subagent.name
                        if subagent_name not in subagent_zayavki_counts:
                            subagent_zayavki_counts[subagent_name] = 0
                        subagent_zayavki_counts[subagent_name] += 1
        
        # Сортируем по убыванию количества заявок
        subagent_zayavki_list = []
        for name, count in sorted(subagent_zayavki_counts.items(), key=lambda x: x[1], reverse=True):
            subagent_zayavki_list.append({'name': name, 'count': count})
        
        # Если нет данных, возвращаем пустой список
        # Frontend покажет сообщение "Нет данных по этому диапазону"

        # Количество заявок по платежщикам субагентов
        # Фильтруем заявки которые не скрыты в дашборде
        payer_zayavki_counts = {}
        for zayavka in zayavki_visible:
            if zayavka.subagent_payer_ids:
                for payer in zayavka.subagent_payer_ids:
                    if payer.name:
                        payer_name = payer.name
                        if payer_name not in payer_zayavki_counts:
                            payer_zayavki_counts[payer_name] = 0
                        payer_zayavki_counts[payer_name] += 1
        
        # Сортируем по убыванию количества заявок
        payer_zayavki_list = []
        for name, count in sorted(payer_zayavki_counts.items(), key=lambda x: x[1], reverse=True):
            payer_zayavki_list.append({'name': name, 'count': count})
        
        # Если нет данных, возвращаем пустой список
        # Frontend покажет сообщение "Нет данных по этому диапазону"

        # Средняя сумма заявок по агентам
        agent_avg_amount_dict = {}
        for zayavka in zayavki_visible:
            if zayavka.agent_id and zayavka.agent_id.name and zayavka.total_fact:
                agent_name = zayavka.agent_id.name
                if agent_name not in agent_avg_amount_dict:
                    agent_avg_amount_dict[agent_name] = {'total_amount': 0, 'count': 0}
                agent_avg_amount_dict[agent_name]['total_amount'] += zayavka.total_fact
                agent_avg_amount_dict[agent_name]['count'] += 1

        # Формируем список средних сумм заявок по агентам
        agent_avg_amount_list = []
        for agent_name, data in agent_avg_amount_dict.items():
            if data['count'] > 0:
                avg_amount = data['total_amount'] / data['count']
                agent_avg_amount_list.append({
                    'name': agent_name,
                    'avg_amount': avg_amount,
                    'count': data['count']
                })

        # Сортируем по убыванию средней суммы
        agent_avg_amount_list = sorted(agent_avg_amount_list, key=lambda x: x['avg_amount'], reverse=True)

        # Ограничиваем до топ-10 агентов
        agent_avg_amount_list = agent_avg_amount_list[:10]

        # Если нет данных, возвращаем пустой список
        # Frontend покажет сообщение "Нет данных по этому диапазону"

        # Средняя сумма заявок по клиентам
        client_avg_amount_dict = {}
        for zayavka in zayavki_visible:
            if zayavka.client_id and zayavka.client_id.name and zayavka.total_fact:
                client_name = zayavka.client_id.name
                if client_name not in client_avg_amount_dict:
                    client_avg_amount_dict[client_name] = {'total_amount': 0, 'count': 0}
                client_avg_amount_dict[client_name]['total_amount'] += zayavka.total_fact
                client_avg_amount_dict[client_name]['count'] += 1
        
        # Вычисляем среднюю сумму для каждого клиента
        client_avg_amount_list = []
        for client_name, data in client_avg_amount_dict.items():
            avg_amount = data['total_amount'] / data['count'] if data['count'] > 0 else 0
            client_avg_amount_list.append({'name': client_name, 'avg_amount': avg_amount})
        
        # Сортируем по убыванию средней суммы
        client_avg_amount_list.sort(key=lambda x: x['avg_amount'], reverse=True)
        
        # Если нет данных, возвращаем пустой список
        # Frontend покажет сообщение "Нет данных по этому диапазону"
        
        # Топ менеджеров по заявкам
        manager_zayavki_counts = {}
        for zayavka in zayavki:
            if zayavka.manager_ids:
                for manager in zayavka.manager_ids:
                    if manager.name not in manager_zayavki_counts:
                        manager_zayavki_counts[manager.name] = 0
                    manager_zayavki_counts[manager.name] += 1
        
        top_managers_by_zayavki = []
        for name, count in sorted(manager_zayavki_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            top_managers_by_zayavki.append({'name': name, 'count': count})
        
        # Среднее время обработки (заглушка)
        processing_time = [
            {'type': 'Переводы', 'hours': 2.5},
            {'type': 'Ордера', 'hours': 1.8},
            {'type': 'Заявки', 'hours': 3.2}
        ]
        
        # Последние операции
        recent_transfers = self.env['amanat.transfer'].search([], order='create_date desc', limit=3)
        recent_zayavki = self.env['amanat.zayavka'].search([], order='create_date desc', limit=2)
        
        recent_operations = []
        for transfer in recent_transfers:
            recent_operations.append({
                'type': 'Перевод',
                'date': transfer.create_date.strftime('%d.%m.%Y %H:%M') if transfer.create_date else '',
                'amount': transfer.amount,
                'currency': currency_map.get(transfer.currency, 'RUB'),
                'status': 'Открыта' if transfer.state == 'open' else ('Закрыта' if transfer.state == 'close' else 'Архив')
            })
        
        for zayavka in recent_zayavki:
            recent_operations.append({
                'type': 'Заявка',
                'date': zayavka.date_placement.strftime('%d.%m.%Y') if zayavka.date_placement else '',
                'amount': zayavka.amount or 0,
                'currency': currency_map.get(zayavka.currency, 'RUB'),
                'status': 'Закрыта' if zayavka.status == 'close' else 'В работе'
            })
        
        return {
            'transfers_count': len(transfers),
            'transfers_active': len(transfers.filtered(lambda t: t.state == 'open')),
            'transfers_closed': len(transfers.filtered(lambda t: t.state == 'close')),
            'transfers_amount': sum(transfers.mapped('amount')),
            'transfers_by_status': transfers_by_status,
            'transfers_by_currency': transfers_by_currency,
            'transfers_by_month': transfers_by_month,
            'transfers_by_country': transfers_by_country,
            'transfers_by_type': transfers_by_type,
            
            'orders_count': orders_count,
            'orders_draft': orders_draft,
            'orders_done': orders_done,
            'orders_by_status': orders_by_status,
            'orders_by_month': orders_by_month,
            
            'money_containers_count': money_containers_count,
            'money_containers_positive': money_containers_positive,
            'money_containers_debt': money_containers_debt,
            
            'currency_rub': currency_rub,
            'currency_usd': currency_usd,
            'currency_usdt': currency_usdt,
            'currency_euro': currency_euro,
            'currency_cny': currency_cny,
            
            # ==================== ЗАЯВКИ ====================
            'zayavki_count': zayavki_count,
            'zayavki_closed': zayavki_closed,
            'zayavki_closed_amount': zayavki_closed_amount,
            'zayavki_usd_equivalent': zayavki_usd_equivalent,
            'zayavki_by_status': zayavki_by_status,
            'zayavki_by_month': zayavki_by_month,
            'zayavki_by_currency': zayavki_by_currency,
            'zayavki_by_deal_type': zayavki_by_deal_type,
            'top_contragents_by_zayavki': top_contragents_by_zayavki,
            'contragent_avg_check': contragent_avg_check,
            'agent_zayavki_list': agent_zayavki_list,
            'agent_avg_amount_list': agent_avg_amount_list,
            'client_zayavki_list': client_zayavki_list,
            'client_avg_amount_list': client_avg_amount_list,
            'subagent_zayavki_list': subagent_zayavki_list,
            'payer_zayavki_list': payer_zayavki_list,
            'top_managers_by_zayavki': top_managers_by_zayavki,
            
            'top_contragents': top_contragents,
            'top_payers': top_payers,
            'managers_efficiency': managers_efficiency,
            'weekday_load': dict(weekday_load),
            'processing_time': processing_time,
            
            'recent_operations': recent_operations,
            
            # ==================== НОВЫЕ ГРАФИКИ МЕНЕДЖЕРОВ ====================
            'managers_by_zayavki': self.get_managers_by_zayavki_data(date_from, date_to),
            'managers_closed_zayavki': self.get_managers_closed_zayavki_data(date_from, date_to),
            'zayavki_status_distribution': self.get_zayavki_status_distribution_data(date_from, date_to),
            'zayavki_deal_cycles': self.get_zayavki_deal_cycles_data(date_from, date_to),
            'contragent_avg_reward_percent': self.get_contragent_avg_reward_percent_data(date_from, date_to),
            'managers_efficiency_data': self.get_managers_efficiency_data(date_from, date_to),
        }

    @api.model
    def get_managers_by_zayavki_data(self, date_from=None, date_to=None):
        """Получить данные по заявкам, закрепленным за менеджерами (с фильтрами как на скриншоте)"""
        
        # Фильтры из скриншота:
        # 1. hide_in_dashboard != True
        # 2. status_range содержит "Да" 
        # 3. status != "отменено клиентом" 
        
        domain = [
            ('hide_in_dashboard', '!=', True),  # Не отображать в дашборде != True
            ('status', '!=', 'cancel')          # Статус != "отменено клиентом"
        ]
        
        # Добавляем фильтрацию по датам
        if date_from and date_to:
            domain.extend([('date_placement', '>=', date_from), ('date_placement', '<=', date_to)])
        elif date_from:
            domain.append(('date_placement', '>=', date_from))
        elif date_to:
            domain.append(('date_placement', '<=', date_to))
        
        # Получаем заявки с учетом фильтров
        zayavki = self.env['amanat.zayavka'].search(domain)
        
        # Считаем количество заявок по каждому менеджеру
        manager_counts = {}
        for zayavka in zayavki:
            if zayavka.manager_ids:
                # Если заявка закреплена за несколькими менеджерами, учитываем всех
                for manager in zayavka.manager_ids:
                    manager_name = manager.name
                    if manager_name not in manager_counts:
                        manager_counts[manager_name] = 0
                    manager_counts[manager_name] += 1
        
        # Преобразуем в список для графика
        managers_list = []
        for manager_name, count in manager_counts.items():
            managers_list.append({
                'name': manager_name,
                'count': count
            })
        
        # Сортируем по убыванию количества заявок
        managers_list.sort(key=lambda x: x['count'], reverse=True)
        
        # Если нет реальных данных, возвращаем пустой список
        # Frontend покажет сообщение "Нет данных по этому диапазону"
        
        return managers_list
    
    @api.model
    def get_managers_closed_zayavki_data(self, date_from=None, date_to=None):
        """Получить данные по заявкам, закрытым менеджерами (как на скриншоте)"""
        
        # Фильтры из скриншота:
        # 1. hide_in_dashboard != True (не отображать в дашборде пустое)
        # 2. status_range содержит "Да" 
        # 3. status = "заявка закрыта"
        
        domain = [
            ('hide_in_dashboard', '!=', True),    # Не отображать в дашборде != True
            ('status', '=', 'close')              # Статус = "заявка закрыта"
        ]
        
        # Добавляем фильтрацию по датам
        if date_from and date_to:
            domain.extend([('date_placement', '>=', date_from), ('date_placement', '<=', date_to)])
        elif date_from:
            domain.append(('date_placement', '>=', date_from))
        elif date_to:
            domain.append(('date_placement', '<=', date_to))
        
        # Получаем заявки с учетом фильтров
        zayavki = self.env['amanat.zayavka'].search(domain)
        
        # Считаем количество заявок по каждому менеджеру
        manager_counts = {}
        for zayavka in zayavki:
            if zayavka.manager_ids:
                # Если заявка закреплена за несколькими менеджерами, учитываем всех
                for manager in zayavka.manager_ids:
                    manager_name = manager.name
                    if manager_name not in manager_counts:
                        manager_counts[manager_name] = 0
                    manager_counts[manager_name] += 1
        
        # Преобразуем в список для графика
        managers_list = []
        for manager_name, count in manager_counts.items():
            managers_list.append({
                'name': manager_name,
                'count': count
            })
        
        # Сортируем по убыванию количества заявок
        managers_list.sort(key=lambda x: x['count'], reverse=True)
        
        # Если нет реальных данных, возвращаем пустой список
        # Frontend покажет сообщение "Нет данных по этому диапазону"
        
        return managers_list
    
    @api.model
    def get_zayavki_status_distribution_data(self, date_from=None, date_to=None):
        """Получить данные по распределению статусов заявок (как на скриншоте)"""
        
        # Фильтры из скриншота:
        # 1. status_range содержит "Да" 
        # 2. hide_in_dashboard is пустое (т.е. != True)
        
        domain = [
            ('hide_in_dashboard', '!=', True)     # Не отображать в дашборде is пустое
        ]
        
        # Добавляем фильтрацию по датам
        if date_from and date_to:
            domain.extend([('date_placement', '>=', date_from), ('date_placement', '<=', date_to)])
        elif date_from:
            domain.append(('date_placement', '>=', date_from))
        elif date_to:
            domain.append(('date_placement', '<=', date_to))
        
        # Получаем заявки с учетом фильтров
        zayavki = self.env['amanat.zayavka'].search(domain)
        
        # Считаем количество заявок по каждому статусу
        status_counts = {}
        for zayavka in zayavki:
            status = zayavka.status or 'Без статуса'
            
            # Мапим статусы для красивого отображения
            status_display_name = status
            if status == 'close':
                status_display_name = 'заявка закрыта'
            elif status == 'cancel':
                status_display_name = 'отменено клиентом'
            elif status == 'return':
                status_display_name = '15. возврат'
            
            if status_display_name not in status_counts:
                status_counts[status_display_name] = 0
            status_counts[status_display_name] += 1
        
        # Преобразуем в список для графика
        status_list = []
        for status_name, count in status_counts.items():
            status_list.append({
                'name': status_name,
                'count': count
            })
        
        # Сортируем по убыванию количества
        status_list.sort(key=lambda x: x['count'], reverse=True)
        
        # Если нет реальных данных, возвращаем пустой список
        # Frontend покажет сообщение "Нет данных по этому диапазону"
        
        return status_list
    
    @api.model
    def get_zayavki_deal_cycles_data(self, date_from=None, date_to=None):
        """Получить данные по циклам сделок (как на скриншоте)"""
        
        # Фильтры для заявок:
        # 1. hide_in_dashboard != True
        # 2. status_range = 'yes'
        
        domain = [
            ('hide_in_dashboard', '!=', True)
        ]
        
        # Добавляем фильтрацию по датам
        if date_from and date_to:
            domain.extend([('date_placement', '>=', date_from), ('date_placement', '<=', date_to)])
        elif date_from:
            domain.append(('date_placement', '>=', date_from))
        elif date_to:
            domain.append(('date_placement', '<=', date_to))
        
        # Получаем заявки с учетом фильтров
        zayavki = self.env['amanat.zayavka'].search(domain)
        
        # Считаем циклы сделок
        cycles_count = {}
        for zayavka in zayavki:
            # Используем готовое поле deal_cycle_days если оно есть
            if hasattr(zayavka, 'deal_cycle_days') and zayavka.deal_cycle_days is not False:
                cycle_days = int(zayavka.deal_cycle_days)
            elif zayavka.date_placement and zayavka.deal_closed_date:
                # Вычисляем цикл как разность дат
                cycle = (zayavka.deal_closed_date - zayavka.date_placement).days
                cycle_days = max(0, cycle)  # Не может быть отрицательным
            else:
                continue  # Пропускаем заявки без данных для вычисления цикла
            
            if cycle_days not in cycles_count:
                cycles_count[cycle_days] = 0
            cycles_count[cycle_days] += 1
        
        # Преобразуем в список для графика и сортируем по циклу
        cycles_list = []
        for cycle_days, count in cycles_count.items():
            cycles_list.append({
                'cycle_days': cycle_days,
                'count': count
            })
        
        # Сортируем по количеству дней
        cycles_list.sort(key=lambda x: x['cycle_days'])
        
        # Если нет реальных данных, возвращаем пустой список
        # Frontend покажет сообщение "Нет данных по этому диапазону"
        
        return cycles_list

    @api.model
    def get_contragent_avg_reward_percent_data(self, date_from=None, date_to=None):
        """Получить данные о среднем проценте вознаграждения по контрагентам"""
        
        # Фильтры как на скриншоте:
        # 1. hide_in_dashboard != True (статус диалога "Да") 
        # 2. Не отображать в дашборде != True
        
        domain = [
            ('hide_in_dashboard', '!=', True),    # Не отображать в дашборде != True
            ('reward_percent', '>', 0),           # Процент вознаграждения больше 0
            ('contragent_id', '!=', False)        # Контрагент указан
        ]
        
        # Добавляем фильтрацию по датам
        if date_from and date_to:
            domain.extend([('date_placement', '>=', date_from), ('date_placement', '<=', date_to)])
        elif date_from:
            domain.append(('date_placement', '>=', date_from))
        elif date_to:
            domain.append(('date_placement', '<=', date_to))
        
        # Получаем заявки с учетом фильтров
        zayavki = self.env['amanat.zayavka'].search(domain)
        
        # Группируем по контрагентам и считаем средний процент
        contragent_rewards = {}
        for zayavka in zayavki:
            contragent_name = zayavka.contragent_id.name
            if contragent_name not in contragent_rewards:
                contragent_rewards[contragent_name] = []
            contragent_rewards[contragent_name].append(zayavka.reward_percent)
        
        # Вычисляем медианные значения процентов для каждого контрагента
        import statistics
        contragent_avg_list = []
        for contragent_name, rewards in contragent_rewards.items():
            if rewards:  # Проверяем что есть данные
                # Используем медиану как на скриншоте (Median: % Вознаграждение)
                median_reward = statistics.median(rewards)
                contragent_avg_list.append({
                    'name': contragent_name,
                    'avg_reward_percent': median_reward
                })
        
        # Сортируем по убыванию медианного процента
        contragent_avg_list.sort(key=lambda x: x['avg_reward_percent'], reverse=True)
        
        # Если нет реальных данных, возвращаем пустой список
        # Frontend покажет сообщение "Нет данных по этому диапазону"
        
        return contragent_avg_list

    @api.model
    def get_managers_efficiency_data(self, date_from=None, date_to=None):
        """Получить данные об эффективности менеджеров в процентах"""
        
        # Получаем всех активных менеджеров  
        managers = self.env['amanat.manager'].search([])
        
        # Логирование для отладки
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(f"Найдено менеджеров: {len(managers)}")
        
        # Если передана фильтрация по датам, нужно вычислить эффективность на основе заявок за период
        if date_from or date_to:
            # Получаем заявки за период для вычисления эффективности
            zayavka_domain = [('hide_in_dashboard', '!=', True)]  # Основной фильтр
            if date_from and date_to:
                zayavka_domain.extend([('date_placement', '>=', date_from), ('date_placement', '<=', date_to)])
            elif date_from:
                zayavka_domain.append(('date_placement', '>=', date_from))
            elif date_to:
                zayavka_domain.append(('date_placement', '<=', date_to))
            
            # Если есть фильтры по датам, вычисляем эффективность по заявкам за период
            managers_efficiency_list = []
            for manager in managers:
                # Получаем заявки этого менеджера за период
                manager_zayavki = self.env['amanat.zayavka'].search(
                    zayavka_domain + [('manager_ids', 'in', manager.id)]
                )
                
                _logger.info(f"Менеджер {manager.name}: найдено {len(manager_zayavki)} заявок за период")
                
                if manager_zayavki:
                    # Считаем эффективность как процент успешно закрытых заявок
                    total_applications = len(manager_zayavki)
                    wrong_applications = len(manager_zayavki.filtered(lambda z: z.status == 'cancel'))
                    efficiency_percent = ((total_applications - wrong_applications) / total_applications * 100) if total_applications > 0 else 0
                    
                    managers_efficiency_list.append({
                        'name': manager.name,
                        'efficiency': efficiency_percent
                    })
                    
                    _logger.info(f"Менеджер {manager.name}: эффективность {efficiency_percent}%")
            
            # Сортируем по убыванию эффективности
            managers_efficiency_list.sort(key=lambda x: x['efficiency'], reverse=True)
            
            _logger.info(f"Результат для периода: {managers_efficiency_list}")
            return managers_efficiency_list
        
        # Обычный режим - без фильтрации по датам
        managers_efficiency_list = []
        for manager in managers:
            # Получаем эффективность в процентах из вычисляемого поля efficiency
            # efficiency уже вычисляется как (total_applications - wrong_applications) / total_applications
            efficiency_percent = (manager.efficiency or 0.0) * 100  # Преобразуем в проценты
            
            _logger.info(f"Менеджер {manager.name}: общая эффективность {efficiency_percent}% (заявок: {manager.total_applications}, ошибочных: {manager.wrong_applications})")
            
            # Добавляем менеджера в список только если у него есть заявки
            if manager.total_applications > 0:
                managers_efficiency_list.append({
                    'name': manager.name,
                    'efficiency': efficiency_percent
                })
        
        # Сортируем по убыванию эффективности
        managers_efficiency_list.sort(key=lambda x: x['efficiency'], reverse=True)
        
        _logger.info(f"Результат общий: {managers_efficiency_list}")
        
        return managers_efficiency_list

    @api.model
    def get_comparison_chart_data(self, date_from1=None, date_to1=None, date_from2=None, date_to2=None):
        """Получить данные для сравнения графиков за два периода"""
        
        def get_period_data(date_from, date_to):
            """Получить данные для одного периода"""
            
            # Базовый домен для фильтрации заявок
            zayavka_domain = []
            if date_from and date_to:
                zayavka_domain = [('date_placement', '>=', date_from), ('date_placement', '<=', date_to)]
            elif date_from:
                zayavka_domain = [('date_placement', '>=', date_from)]
            elif date_to:
                zayavka_domain = [('date_placement', '<=', date_to)]
            
            # Получаем заявки для периода
            zayavki = self.env['amanat.zayavka'].search(zayavka_domain)
            zayavki_visible = zayavki.filtered(lambda z: not z.hide_in_dashboard)
            
            # 1. Количество заявок под каждого контрагента
            contragent_zayavki_counts = {}
            for zayavka in zayavki_visible:
                if zayavka.contragent_id and zayavka.contragent_id.name:
                    if zayavka.contragent_id.name not in contragent_zayavki_counts:
                        contragent_zayavki_counts[zayavka.contragent_id.name] = 0
                    contragent_zayavki_counts[zayavka.contragent_id.name] += 1
            
            contragents_by_zayavki = []
            for name, count in sorted(contragent_zayavki_counts.items(), key=lambda x: x[1], reverse=True):
                contragents_by_zayavki.append({'name': name, 'count': count})
            
            # 2. Средний чек у контрагентов
            contragent_avg_amounts = {}
            for zayavka in zayavki_visible:
                if zayavka.contragent_id and zayavka.contragent_id.name and zayavka.amount:
                    contragent_name = zayavka.contragent_id.name
                    if contragent_name not in contragent_avg_amounts:
                        contragent_avg_amounts[contragent_name] = {'total_amount': 0, 'count': 0}
                    contragent_avg_amounts[contragent_name]['total_amount'] += zayavka.amount
                    contragent_avg_amounts[contragent_name]['count'] += 1
            
            contragent_avg_check = []
            for name, data in contragent_avg_amounts.items():
                if data['count'] > 0:
                    avg_amount = data['total_amount'] / data['count']
                    contragent_avg_check.append({'name': name, 'avg_amount': avg_amount})
            contragent_avg_check.sort(key=lambda x: x['avg_amount'], reverse=True)
            
            # 3. Вознаграждение средний процент по контрагентам
            contragent_rewards = {}
            for zayavka in zayavki.filtered(lambda z: not z.hide_in_dashboard and z.reward_percent > 0 and z.contragent_id):
                contragent_name = zayavka.contragent_id.name
                if contragent_name not in contragent_rewards:
                    contragent_rewards[contragent_name] = []
                contragent_rewards[contragent_name].append(zayavka.reward_percent)
            
            import statistics
            contragent_reward_percent = []
            for contragent_name, rewards in contragent_rewards.items():
                if rewards:
                    median_reward = statistics.median(rewards)
                    contragent_reward_percent.append({
                        'name': contragent_name,
                        'avg_reward_percent': median_reward
                    })
            contragent_reward_percent.sort(key=lambda x: x['avg_reward_percent'], reverse=True)
            
            # 4. Количество заявок под каждого агента
            agent_zayavki_counts = {}
            for zayavka in zayavki_visible:
                if zayavka.agent_id and zayavka.agent_id.name:
                    agent_name = zayavka.agent_id.name
                    if agent_name not in agent_zayavki_counts:
                        agent_zayavki_counts[agent_name] = 0
                    agent_zayavki_counts[agent_name] += 1
            
            agents_by_zayavki = []
            for name, count in sorted(agent_zayavki_counts.items(), key=lambda x: x[1], reverse=True):
                agents_by_zayavki.append({'name': name, 'count': count})
            
            # 5. Средняя сумма заявок под каждого агента
            agent_avg_amount_dict = {}
            for zayavka in zayavki_visible:
                if zayavka.agent_id and zayavka.agent_id.name and zayavka.total_fact:
                    agent_name = zayavka.agent_id.name
                    if agent_name not in agent_avg_amount_dict:
                        agent_avg_amount_dict[agent_name] = {'total_amount': 0, 'count': 0}
                    agent_avg_amount_dict[agent_name]['total_amount'] += zayavka.total_fact
                    agent_avg_amount_dict[agent_name]['count'] += 1

            agent_avg_amount = []
            for agent_name, data in agent_avg_amount_dict.items():
                if data['count'] > 0:
                    avg_amount = data['total_amount'] / data['count']
                    agent_avg_amount.append({
                        'name': agent_name,
                        'avg_amount': avg_amount,
                        'count': data['count']
                    })
            agent_avg_amount = sorted(agent_avg_amount, key=lambda x: x['avg_amount'], reverse=True)[:10]
            
            # 6. Количество заявок под каждого клиента
            client_zayavki_counts = {}
            for zayavka in zayavki_visible:
                if zayavka.client_id and zayavka.client_id.name:
                    client_name = zayavka.client_id.name
                    if client_name not in client_zayavki_counts:
                        client_zayavki_counts[client_name] = 0
                    client_zayavki_counts[client_name] += 1
            
            clients_by_zayavki = []
            for name, count in sorted(client_zayavki_counts.items(), key=lambda x: x[1], reverse=True):
                clients_by_zayavki.append({'name': name, 'count': count})
            
            # 7. Количество заявок по платежщикам субагентов
            payer_zayavki_counts = {}
            for zayavka in zayavki_visible:
                if zayavka.subagent_payer_ids:
                    for payer in zayavka.subagent_payer_ids:
                        if payer.name:
                            payer_name = payer.name
                            if payer_name not in payer_zayavki_counts:
                                payer_zayavki_counts[payer_name] = 0
                            payer_zayavki_counts[payer_name] += 1
            
            payers_by_zayavki = []
            for name, count in sorted(payer_zayavki_counts.items(), key=lambda x: x[1], reverse=True):
                payers_by_zayavki.append({'name': name, 'count': count})
            
            # 8. Количество заявок под каждого субагента
            subagent_zayavki_counts = {}
            for zayavka in zayavki_visible:
                if zayavka.subagent_ids:
                    for subagent in zayavka.subagent_ids:
                        if subagent.name:
                            subagent_name = subagent.name
                            if subagent_name not in subagent_zayavki_counts:
                                subagent_zayavki_counts[subagent_name] = 0
                            subagent_zayavki_counts[subagent_name] += 1
            
            subagents_by_zayavki = []
            for name, count in sorted(subagent_zayavki_counts.items(), key=lambda x: x[1], reverse=True):
                subagents_by_zayavki.append({'name': name, 'count': count})
            
            # 9. Средняя сумма заявок по клиентам
            client_avg_amount_dict = {}
            for zayavka in zayavki_visible:
                if zayavka.client_id and zayavka.client_id.name and zayavka.total_fact:
                    client_name = zayavka.client_id.name
                    if client_name not in client_avg_amount_dict:
                        client_avg_amount_dict[client_name] = {'total_amount': 0, 'count': 0}
                    client_avg_amount_dict[client_name]['total_amount'] += zayavka.total_fact
                    client_avg_amount_dict[client_name]['count'] += 1
            
            client_avg_amount = []
            for client_name, data in client_avg_amount_dict.items():
                avg_amount = data['total_amount'] / data['count'] if data['count'] > 0 else 0
                client_avg_amount.append({'name': client_name, 'avg_amount': avg_amount})
            client_avg_amount.sort(key=lambda x: x['avg_amount'], reverse=True)
            
            # 10. Циклы сделок
            cycles_count = {}
            for zayavka in zayavki.filtered(lambda z: not z.hide_in_dashboard):
                if hasattr(zayavka, 'deal_cycle_days') and zayavka.deal_cycle_days is not False:
                    cycle_days = int(zayavka.deal_cycle_days)
                elif zayavka.date_placement and zayavka.deal_closed_date:
                    cycle = (zayavka.deal_closed_date - zayavka.date_placement).days
                    cycle_days = max(0, cycle)
                else:
                    continue
                
                if cycle_days not in cycles_count:
                    cycles_count[cycle_days] = 0
                cycles_count[cycle_days] += 1
            
            deal_cycles = []
            for cycle_days, count in cycles_count.items():
                deal_cycles.append({
                    'cycle_days': cycle_days,
                    'count': count
                })
            deal_cycles.sort(key=lambda x: x['cycle_days'])
            
            # 11. Типы сделок (ИМПОРТ/ЭКСПОРТ)
            deal_types_count = {}
            for zayavka in zayavki.filtered(lambda z: not z.hide_in_dashboard):
                deal_type = zayavka.deal_type or 'Не указан'
                deal_type_name = 'Импорт' if deal_type == 'import' else ('Экспорт' if deal_type == 'export' else 'Не указан')
                if deal_type_name not in deal_types_count:
                    deal_types_count[deal_type_name] = 0
                deal_types_count[deal_type_name] += 1
            
            # 12. Заявки закрепленные за менеджерами
            manager_zayavki_counts = {}
            for zayavka in zayavki.filtered(lambda z: not z.hide_in_dashboard and z.status != 'cancel'):
                if zayavka.manager_ids:
                    for manager in zayavka.manager_ids:
                        manager_name = manager.name
                        if manager_name not in manager_zayavki_counts:
                            manager_zayavki_counts[manager_name] = 0
                        manager_zayavki_counts[manager_name] += 1
            
            managers_by_zayavki = []
            for manager_name, count in manager_zayavki_counts.items():
                managers_by_zayavki.append({
                    'name': manager_name,
                    'count': count
                })
            managers_by_zayavki.sort(key=lambda x: x['count'], reverse=True)
            
            # 13. Заявки закрытые менеджерами
            manager_closed_counts = {}
            for zayavka in zayavki.filtered(lambda z: not z.hide_in_dashboard and z.status == 'close'):
                if zayavka.manager_ids:
                    for manager in zayavka.manager_ids:
                        manager_name = manager.name
                        if manager_name not in manager_closed_counts:
                            manager_closed_counts[manager_name] = 0
                        manager_closed_counts[manager_name] += 1
            
            managers_closed_zayavki = []
            for manager_name, count in manager_closed_counts.items():
                managers_closed_zayavki.append({
                    'name': manager_name,
                    'count': count
                })
            managers_closed_zayavki.sort(key=lambda x: x['count'], reverse=True)
            
            return {
                'contragents_by_zayavki': contragents_by_zayavki,
                'contragent_avg_check': contragent_avg_check,
                'contragent_reward_percent': contragent_reward_percent,
                'agents_by_zayavki': agents_by_zayavki,
                'agent_avg_amount': agent_avg_amount,
                'clients_by_zayavki': clients_by_zayavki,
                'payers_by_zayavki': payers_by_zayavki,
                'subagents_by_zayavki': subagents_by_zayavki,
                'client_avg_amount': client_avg_amount,
                'deal_cycles': deal_cycles,
                'deal_types': deal_types_count,
                'managers_by_zayavki': managers_by_zayavki,
                'managers_closed_zayavki': managers_closed_zayavki
            }
        
        # Получаем данные для обоих периодов
        period1_data = get_period_data(date_from1, date_to1)
        period2_data = get_period_data(date_from2, date_to2)
        
        return {
            'period1': period1_data,
            'period2': period2_data
        }

    @api.model
    def get_zayavki_comparison_data(self, date_from1=None, date_to1=None, date_from2=None, date_to2=None):
        """Получить данные для сравнения заявок за два периода (базовые показатели)"""
        
        def get_zayavki_period_stats(date_from, date_to):
            """Получить статистику заявок для одного периода"""
            
            # Базовый домен для фильтрации заявок
            zayavka_domain = []
            if date_from and date_to:
                zayavka_domain = [('date_placement', '>=', date_from), ('date_placement', '<=', date_to)]
            elif date_from:
                zayavka_domain = [('date_placement', '>=', date_from)]
            elif date_to:
                zayavka_domain = [('date_placement', '<=', date_to)]
            
            # Получаем заявки для периода
            zayavki = self.env['amanat.zayavka'].search(zayavka_domain)
            zayavki_visible = zayavki.filtered(lambda z: not z.hide_in_dashboard)
            
            # Закрытые заявки (статус = 'close')
            closed_zayavki = zayavki_visible.filtered(lambda z: z.status == 'close')
            zayavki_closed = len(closed_zayavki)
            
            # Сумма закрытых заявок
            zayavki_closed_amount = sum(closed_zayavki.mapped('amount') or [0])
            
            # Эквивалент в USD (используем курс 1 USD = 100 RUB для примера)
            usd_rate = 100.0
            zayavki_usd_equivalent = zayavki_closed_amount / usd_rate if zayavki_closed_amount > 0 else 0.0
            
            return {
                'zayavki_count': len(zayavki_visible),
                'zayavki_closed': zayavki_closed,
                'zayavki_closed_amount': zayavki_closed_amount,
                'zayavki_usd_equivalent': zayavki_usd_equivalent,
                'period_label': f"{date_from} - {date_to}" if date_from and date_to else "Все время"
            }
        
        # Получаем данные для обоих периодов
        range1_stats = get_zayavki_period_stats(date_from1, date_to1)
        range2_stats = get_zayavki_period_stats(date_from2, date_to2)
        
        return {
            'range1': range1_stats,
            'range2': range2_stats
        } 
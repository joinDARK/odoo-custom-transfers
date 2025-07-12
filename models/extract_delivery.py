# models/extract_delivery.py
from odoo import models, fields, api
from .base_model import AmanatBaseModel
import logging

_logger = logging.getLogger(__name__)

class Extract_delivery(models.Model, AmanatBaseModel):
    _name = 'amanat.extract_delivery'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Выписка разнос'

    name = fields.Char(
        string="Номер платежа", 
        readonly=True, 
        default=lambda self: self.env['ir.sequence'].next_by_code('amanat.extract_delivery.sequence'), copy=False
    )
    date = fields.Date(string="Дата", tracking=True)
    amount = fields.Float(string="Сумма", tracking=True)

    payer = fields.Many2one('amanat.payer', string="Плательщик", tracking=True)
    payer_inn = fields.Char(
        string="ИНН Плательщика",
        related='payer.inn',
        store=True,
        readonly=True,
        tracking=True
    )
    serial_number = fields.Integer(string="Порядковый номер в выписке", tracking=True)

    recipient = fields.Many2one('amanat.payer', string="Получатель", tracking=True)
    recipient_inn = fields.Char(
        string="ИНН Получателя",
        related='recipient.inn',
        store=True,
        readonly=True,
        tracking=True
    )
    payment_purpose = fields.Char(string="Назначение платежа", tracking=True)
    document_id = fields.Many2one('amanat.extracts', string="ID Документа", tracking=True)
    bank_document = fields.Selection(
        related='document_id.bank',
        string='Банк',
        store=True,
        readonly=True,
        tracking=True
    )
    assign_bulinan = fields.Boolean(string="Разнести", tracking=True)
    create_transfer_bulinan = fields.Boolean(string="Создать перевод", tracking=True)
    dds_article = fields.Selection([
        ('operational', 'Операционные потоки'),
        ('investment', 'Инвестиционные потоки'),
        ('financial', 'Финансовые потоки'),
        ('not_applicable', 'Не относится')
    ], string="Статья ДДС", default='not_applicable', tracking=True)
    direction_choice = fields.Selection([
        ('currency_reserve', 'Валютный резерв'),
        ('transfer', 'Перевод'),
        ('conversion', 'Конвертация'),
        ('investment', 'Инвестиция'),
        ('gold_deal', 'Золото сделка'),
        ('no_matches', 'Нет совпадений'),
        ('applications', 'Заявки')
    ], string="Выбор направления", tracking=True)

    applications = fields.Many2many(
        'amanat.zayavka', 
        'amanat_zayavka_extract_delivery_rel',
        'extract_delivery_id',
        'zayavka_id',
        string="Заявки", 
        tracking=True
    )
    currency_reserve = fields.Many2many('amanat.reserve', string="Валютный резерв", tracking=True)
    transfer_ids = fields.Many2many('amanat.transfer', string="Перевод", tracking=True)
    conversion = fields.Many2many(
        'amanat.conversion',
        'amanat_conversion_extract_delivery_rel',
        'extract_delivery',
        'conversion_id',
        string="Конвертация", 
        tracking=True
    )
    investment = fields.Many2many('amanat.investment', string="Инвестиция", tracking=True)
    gold_deal = fields.Many2many('amanat.gold_deal', string="Золото сделка", tracking=True)

    counterparty1 = fields.Many2one('amanat.contragent', string="Контрагент 1", tracking=True)
    counterparty2 = fields.Many2one('amanat.contragent', string="Контрагент 2", tracking=True)
    wallet1 = fields.Many2one('amanat.wallet', string="Кошелек 1", tracking=True)
    wallet2 = fields.Many2one('amanat.wallet', string="Кошелек 2", tracking=True)

    percent = fields.Float(string="Процент", tracking=True)
    fragment_statement = fields.Boolean(string="Раздробить выписку", tracking=True)
    
    range_field = fields.Many2one('amanat.ranges', string="Диапазон", tracking=True)
    date_start = fields.Date(
        string="Дата начало (from Диапазон)", 
        store=True, 
        readonly=True,
        tracking=True,
        related="range_field.date_start"
    )
    date_end = fields.Date(
        string="Дата конец (from Диапазон)", 
        store=True, 
        readonly=True,
        tracking=True,
        related="range_field.date_end"
    )
    range_status = fields.Char(string="Статус диапазона", compute='_compute_range_status', store=True, tracking=True)

    # Оставшиеся поля
    statement_part_1 = fields.Float(string="Выписка дробь 1", digits=(16, 2), tracking=True)
    statement_part_2 = fields.Float(string="Выписка дробь 2", digits=(16, 2), tracking=True)
    statement_part_3 = fields.Float(string="Выписка дробь 3", digits=(16, 2), tracking=True)
    statement_part_4 = fields.Float(string="Выписка дробь 4", digits=(16, 2), tracking=True)
    statement_part_5 = fields.Float(string="Выписка дробь 5", digits=(16, 2), tracking=True)
    statement_part_6 = fields.Float(string="Выписка дробь 6", digits=(16, 2), tracking=True)
    statement_part_7 = fields.Float(string="Выписка дробь 7", digits=(16, 2), tracking=True)
    statement_part_8 = fields.Float(string="Выписка дробь 8", digits=(16, 2), tracking=True)
    statement_part_9 = fields.Float(string="Выписка дробь 9", digits=(16, 2), tracking=True)
    statement_part_10 = fields.Float(string="Выписка дробь 10", digits=(16, 2), tracking=True)
    statement_part_11 = fields.Float(string="Выписка дробь 11", digits=(16, 2), tracking=True)
    statement_part_12 = fields.Float(string="Выписка дробь 12", digits=(16, 2), tracking=True)
    statement_part_13 = fields.Float(string="Выписка дробь 13", digits=(16, 2), tracking=True)
    statement_part_14 = fields.Float(string="Выписка дробь 14", digits=(16, 2), tracking=True)
    statement_part_15 = fields.Float(string="Выписка дробь 15", digits=(16, 2), tracking=True)
    statement_part_16 = fields.Float(string="Выписка дробь 16", digits=(16, 2), tracking=True)
    statement_part_17 = fields.Float(string="Выписка дробь 17", digits=(16, 2), tracking=True)
    statement_part_18 = fields.Float(string="Выписка дробь 18", digits=(16, 2), tracking=True)
    statement_part_19 = fields.Float(string="Выписка дробь 19", digits=(16, 2), tracking=True)
    statement_part_20 = fields.Float(string="Выписка дробь 20", digits=(16, 2), tracking=True)

    remaining_statement = fields.Float(
        string="Остаток для исходной выписки", 
        compute='_compute_remaining_statement',
        store=True,
        tracking=True,
        readonly=False,
    )

    # Вычисляемое поле "Сделка" - аналог формулы из Airtable
    deal = fields.Char(
        string="Сделка",
        compute='_compute_deal',
        store=True,
        tracking=True
    )

    @api.depends('date', 'date_start', 'date_end')
    def _compute_range_status(self):
        for record in self:
            if record.date and record.date_start and record.date_end:
                if record.date >= record.date_start and record.date <= record.date_end:
                    record.range_status = "Да"
                else:
                    record.range_status = "Нет"
            else:
                record.range_status = "Нет"

    @api.depends('amount', 'statement_part_1', 'statement_part_2', 'statement_part_3', 'statement_part_4', 
                 'statement_part_5', 'statement_part_6', 'statement_part_7', 'statement_part_8', 'statement_part_9', 
                 'statement_part_10', 'statement_part_11', 'statement_part_12', 'statement_part_13', 'statement_part_14', 
                 'statement_part_15', 'statement_part_16', 'statement_part_17', 'statement_part_18', 'statement_part_19', 
                 'statement_part_20')
    def _compute_remaining_statement(self):
        for record in self:
            # Вычисляем остаток как сумма минус все дроби
            total_parts = sum([
                record.statement_part_1 or 0,
                record.statement_part_2 or 0,
                record.statement_part_3 or 0,
                record.statement_part_4 or 0,
                record.statement_part_5 or 0,
                record.statement_part_6 or 0,
                record.statement_part_7 or 0,
                record.statement_part_8 or 0,
                record.statement_part_9 or 0,
                record.statement_part_10 or 0,
                record.statement_part_11 or 0,
                record.statement_part_12 or 0,
                record.statement_part_13 or 0,
                record.statement_part_14 or 0,
                record.statement_part_15 or 0,
                record.statement_part_16 or 0,
                record.statement_part_17 or 0,
                record.statement_part_18 or 0,
                record.statement_part_19 or 0,
                record.statement_part_20 or 0,
            ])
            record.remaining_statement = (record.amount or 0) - total_parts

    @api.depends('currency_reserve', 'transfer_ids', 'conversion', 'investment', 'gold_deal', 'applications')
    def _compute_deal(self):
        for record in self:
            # Проверяем поля в том же порядке, что и в Airtable
            if record.currency_reserve:
                record.deal = ", ".join(record.currency_reserve.mapped('name'))
            elif record.transfer_ids:
                record.deal = ", ".join(record.transfer_ids.mapped('name'))
            elif record.conversion:
                record.deal = ", ".join(record.conversion.mapped('name'))
            elif record.investment:
                record.deal = ", ".join(record.investment.mapped('name'))
            elif record.gold_deal:
                record.deal = ", ".join(record.gold_deal.mapped('name'))
            elif record.applications:
                # Используем правильное поле zayavka_id для отображения
                record.deal = ", ".join(record.applications.mapped('zayavka_id'))
            else:
                record.deal = ""

    def write(self, vals):
        res = super().write(vals)
        if vals.get('fragment_statement'):
            for rec in self.filtered('fragment_statement'):
                rec.action_fragment_statement()
                rec.match_extract_with_zayavka()
                rec.fragment_statement = False

        if vals.get('create_transfer_bulinan'):
            for rec in self.filtered('create_transfer_bulinan'):
                rec.create_transfer()
                rec.create_transfer_bulinan = False

        if vals.get('assign_bulinan'):
            for rec in self.filtered('assign_bulinan'):
                rec.env['amanat.extract_delivery']._run_matching_automation()
                rec.env['amanat.extract_delivery']._run_stellar_tdk_logic()
                rec.assign_bulinan = False
        return res

    def _find_matching_applications(self):
        """
        Находит заявки, подходящие для текущей записи выписки по критериям:
        - плательщик и получатель выписки должны быть среди плательщиков заявки  
        - сумма должна совпадать с допуском ±1 рубль
        - заявка должна быть взята в работу
        """
        self.ensure_one()
        
        if not self.payer or not self.recipient or not self.amount:
            return self.env['amanat.zayavka']
            
        TOLERANCE = 1.0
        
        # Получаем плательщиков выписки
        extract_payers = [self.payer.id, self.recipient.id]
        extract_sum = self.amount
        
        # Ищем заявки с заполненной датой "Взята в работу"
        all_zayavki = self.env['amanat.zayavka'].search([('taken_in_work_date', '!=', False)])
        
        matching_zayavki = []
        
        for zayavka in all_zayavki:
            # Собираем плательщиков заявки через контрагентов
            candidate_payers = []
            
            if zayavka.agent_id and zayavka.agent_id.payer_ids:
                candidate_payers.extend(zayavka.agent_id.payer_ids.ids)
                
            if zayavka.client_id and zayavka.client_id.payer_ids:
                candidate_payers.extend(zayavka.client_id.payer_ids.ids)
            
            if not candidate_payers:
                continue
            
            # Проверяем, что все плательщики выписки есть среди кандидатов
            all_matched = all(payer_id in candidate_payers for payer_id in extract_payers)
            
            if not all_matched:
                continue

            # Проверяем суммы заявки (в порядке приоритета)
            zayavka_sums = [
                getattr(zayavka, 'application_amount_rub_contract', None),  # Заявка по курсу в рублях по договору
                getattr(zayavka, 'total_fact', None),                      # Итого факт
                getattr(zayavka, 'contract_reward', None)                  # Вознаграждение по договору
            ]
            
            # Находим первую непустую сумму
            zayavka_sum = None
            for sum_val in zayavka_sums:
                if isinstance(sum_val, (int, float)) and sum_val is not None:
                    zayavka_sum = sum_val
                    break
            
            if zayavka_sum is None:
                continue

            # Проверяем сумму с допуском
            if abs(zayavka_sum - extract_sum) <= TOLERANCE:
                matching_zayavki.append(zayavka)
                _logger.info(f"Найдено совпадение: выписка {self.id} (сумма {extract_sum}) с заявкой {zayavka.zayavka_id} (сумма {zayavka_sum})")
        
        return self.env['amanat.zayavka'].browse([z.id for z in matching_zayavki])

    def manual_match_applications(self):
        """
        Ручное сопоставление выписки с заявками.
        Используется как кнопка или для обработки старых записей.
        """
        for record in self:
            if record.applications:
                _logger.info(f"Выписка {record.id} уже имеет связанные заявки: {record.applications.mapped('zayavka_id')}")
                continue
                
            if any([record.currency_reserve, record.transfer_ids, record.conversion, 
                   record.investment, record.gold_deal]):
                _logger.info(f"Выписка {record.id} уже имеет другие сделки, пропускаем")
                continue
                
            matching_apps = record._find_matching_applications()
            if matching_apps:
                record.write({
                    'applications': [(6, 0, matching_apps.ids)],
                    'direction_choice': 'applications'
                })
                
                # Обновляем обратную связь в заявках
                for app in matching_apps:
                    app.write({
                        'extract_delivery_ids': [(4, record.id)]
                    })
                
                record.message_post(
                    body=f"Ручное сопоставление: найдены подходящие заявки: {', '.join(matching_apps.mapped('zayavka_id'))}"
                )
                _logger.info(f"Ручное сопоставление: выписка {record.id} связана с заявками: {matching_apps.mapped('zayavka_id')}")
            else:
                record.message_post(body="Ручное сопоставление: подходящие заявки не найдены")
                _logger.info(f"Ручное сопоставление: для выписки {record.id} подходящие заявки не найдены")
        
        return True

    @api.model
    def create(self, vals):
        res = super().create(vals)
        trigger = vals.get('fragment_statement', False)
        trigger2 = vals.get('create_transfer_bulinan', False)

        if trigger:
            res.action_fragment_statement()
            res.match_extract_with_zayavka()
            res.fragment_statement = False

        if trigger2:
            res.create_transfer_bulinan = False
            res.create_transfer()

        if vals.get('assign_bulinan'):
            res.env['amanat.extract_delivery']._run_matching_automation()
            res.env['amanat.extract_delivery']._run_stellar_tdk_logic()
            res.assign_bulinan = False
        
        # Автоматический поиск и установка подходящих заявок при создании
        # Только если нет уже связанных заявок и других сделок
        if (not res.applications and not trigger and not trigger2 and 
            not vals.get('assign_bulinan') and not any([
                res.currency_reserve, res.transfer_ids, res.conversion, 
                res.investment, res.gold_deal
            ])):
            try:
                matching_apps = res._find_matching_applications()
                if matching_apps:
                    res.write({
                        'applications': [(6, 0, matching_apps.ids)],
                        'direction_choice': 'applications'
                    })
                    
                    # Обновляем обратную связь в заявках
                    for app in matching_apps:
                        app.write({
                            'extract_delivery_ids': [(4, res.id)]
                        })
                    
                    _logger.info(f"Автоматически связана выписка {res.id} с заявками: {matching_apps.mapped('zayavka_id')}")
            except Exception as e:
                _logger.error(f"Ошибка при автоматическом сопоставлении заявок для выписки {res.id}: {e}")

        return res
    
    def create_transfer(self):
        """
        Создает новую запись в модели Transfer на основе данных из текущей записи Extract_delivery.
        Перенесена логика из JavaScript скрипта.
        """
        for record in self:
            # Проверяем наличие необходимых данных
            if not all([record.date, record.amount, record.wallet1, record.wallet2, 
                       record.counterparty1, record.counterparty2]):
                _logger.error(f"Отсутствуют необходимые данные в записи Extract_delivery ID={record.id}")
                continue
            
            # Подготавливаем данные для создания Transfer
            transfer_vals = {
                'date': record.date,
                'currency': 'rub',  # По умолчанию RUB, как в JavaScript
                'amount': record.amount,
                'sender_wallet_id': record.wallet1.id,
                'receiver_wallet_id': record.wallet2.id,
                'sender_id': record.counterparty1.id,
                'receiver_id': record.counterparty2.id,
                'sending_commission_percent': record.percent or 0.0,
                'create_order': True,  # Устанавливаем флаг "Создать" в активный режим
            }
            
            # Добавляем плательщиков если они указаны
            if record.payer:
                transfer_vals['sender_payer_id'] = record.payer.id
            if record.recipient:
                transfer_vals['receiver_payer_id'] = record.recipient.id
            
            # Создаем новую запись Transfer
            try:
                new_transfer = self.env['amanat.transfer'].create(transfer_vals)
                
                # Добавляем обратную связь - связываем Transfer с текущей Extract_delivery
                record.write({
                    'transfer_ids': [(4, new_transfer.id)]
                })
                
                _logger.info(f"Создана новая запись Transfer ID={new_transfer.id} из Extract_delivery ID={record.id}")
                
            except Exception as e:
                _logger.error(f"Ошибка при создании Transfer из Extract_delivery ID={record.id}: {str(e)}")
                continue

        return True
    
    def action_fragment_statement(self):
        record = self.id
        if not record:
            return {'error': f'Запись с ID {record} не найдена.'}

        # Копируем нужные поля
        base_vals = {
            'date': self.date,
            'payer': self.payer.id if self.payer else False,
            'recipient': self.recipient.id if self.recipient else False,
            'payment_purpose': self.payment_purpose,
            'document_id': self.document_id.id if self.document_id else False,
            'direction_choice': self.direction_choice,
            'range_field': self.range_field.id if self.range_field else False,
            'serial_number': self.serial_number,
        }

        new_records = []
        # Перебираем дроби
        for i in range(1, 21):
            part_field = f'statement_part_{i}'
            part_value = getattr(self, part_field, None)
            if part_value:
                vals = base_vals.copy()
                vals['amount'] = part_value
                # Создаём новую выписку
                new_rec = self.create(vals)
                new_records.append(new_rec.id)

        # Обновляем исходную выписку
        self.amount = self.remaining_statement
        for i in range(1, 21):
            setattr(self, f'statement_part_{i}', 0)
        self.fragment_statement = False

        _logger.info(f"Обновлена выписка разнос с ID={self.id} а также созданы новые записи: {new_records}")
        
        # Запускаем сопоставление с заявками после дробления
        
        return True

    def match_extract_with_zayavka(self):
        """
        Сопоставляет выписки с заявками по логике из скрипта.
        Ищет подходящие заявки для выписок без связанных заявок.
        """
        TOLERANCE = 1.0
        
        # Поля для проверки сумм в заявках
        fields_to_check = [
            'application_amount_rub_contract',  # Заявка по курсу в рублях по договору
            'contract_reward',                  # Вознаграждение по договору
            'total_fact'                       # Итого факт
        ]
        
        # Получаем все заявки с заполненной датой "Взята в работу"
        zayavka_records = self.env['amanat.zayavka'].search([
            ('taken_in_work_date', '!=', False)
        ])
        
        used_extract_ids = set()
        
        for zayavka in zayavka_records:
            # Собираем кандидатов плательщиков через агента и клиента
            candidate_payers = []
            
            if zayavka.agent_id and zayavka.agent_id.payer_ids:
                candidate_payers.extend(zayavka.agent_id.payer_ids.ids)
                
            if zayavka.client_id and zayavka.client_id.payer_ids:
                candidate_payers.extend(zayavka.client_id.payer_ids.ids)
            
            if not candidate_payers:
                continue
                
            # Ищем подходящие выписки
            candidate_extracts = []
            
            # Получаем выписки без связанных заявок и не использованные ранее
            extract_records = self.env['amanat.extract_delivery'].search([
                ('applications', '=', False),  # Нет связанных заявок
                ('id', 'not in', list(used_extract_ids))
            ])
            
            for extract in extract_records:
                # Проверяем, что нет "сделки" (аналог проверки sdelka в JavaScript)
                if (extract.currency_reserve or extract.transfer_ids or 
                    extract.conversion or extract.investment or extract.gold_deal):
                    continue
                
                # Проверяем плательщиков и получателей
                extract_payers = []
                if extract.payer:
                    extract_payers.append(extract.payer.id)
                if extract.recipient:
                    extract_payers.append(extract.recipient.id)
                
                if not extract_payers:
                    continue
                    
                # Проверяем, что все плательщики/получатели выписки есть среди кандидатов
                all_matched = all(payer_id in candidate_payers for payer_id in extract_payers)
                
                if not all_matched:
                    continue
                    
                # Проверяем сумму с допуском
                if extract.amount is None:
                    continue
                    
                sum_matches = False
                for field_name in fields_to_check:
                    zayavka_sum = getattr(zayavka, field_name, None)
                    if isinstance(zayavka_sum, (int, float)) and zayavka_sum is not None:
                        if abs(zayavka_sum - extract.amount) <= TOLERANCE:
                            sum_matches = True
                            break
                            
                if not sum_matches:
                    continue
                    
                candidate_extracts.append(extract)
            
            # Если найдены подходящие выписки, выбираем лучшую (самую раннюю по дате)
            if candidate_extracts:
                # Сортируем по дате (самая ранняя первая)
                candidate_extracts.sort(key=lambda x: x.date or fields.Date.today())
                best_extract = candidate_extracts[0]
                
                # Обновляем выписку
                best_extract.write({
                    'applications': [(4, zayavka.id)],  # Добавляем связь с заявкой
                    'direction_choice': 'applications'   # Устанавливаем направление
                })
                
                # Обновляем заявку - добавляем обратную связь
                zayavka.write({
                    'extract_delivery_ids': [(4, best_extract.id)]  # Добавляем связь с выпиской
                })
                
                used_extract_ids.add(best_extract.id)
                
                _logger.info(f"Связана выписка ID={best_extract.id} с заявкой ID={zayavka.id}")
        
        _logger.info(f"Сопоставление завершено. Обработано заявок: {len(zayavka_records)}, связано выписок: {len(used_extract_ids)}")
        return True
    
    @api.model
    def _run_matching_automation(self):
        """
        Логика сопоставления выписок с заявками:
        - Ищем плательщиков заявки через связанных контрагентов (агент и клиент)
        - Проверяем что плательщики выписки есть среди найденных
        - Суммы должны совпадать с погрешностью 1 рубль
        - Одна выписка может быть связана с несколькими заявками
        """
        _logger.info("Запуск автоматического сопоставления Выписок и Заявок")
        TOLERANCE = 1.0

        # Получаем все заявки с заполненной датой "Взята в работу"
        all_zayavki = self.env['amanat.zayavka'].search([('taken_in_work_date', '!=', False)])
        
        # Получаем все выписки без связанных заявок
        candidate_extracts = self.env['amanat.extract_delivery'].search([
            ('applications', '=', False)
        ])
        
        # Словарь для хранения всех подходящих заявок для каждой выписки
        extract_to_zayavki = {}
        
        # Проходим по всем выпискам
        for extract in candidate_extracts:
            # Проверяем, что нет других "сделок"
            if (extract.currency_reserve or extract.transfer_ids or 
                extract.conversion or extract.investment or extract.gold_deal):
                continue
                
            # Получаем плательщиков выписки
            extract_payers = []
            if extract.payer:
                extract_payers.append(extract.payer.id)
            if extract.recipient:
                extract_payers.append(extract.recipient.id)
                
            if not extract_payers:
                continue
                
            extract_sum = extract.amount or 0.0
            matching_zayavki = []
            
            # Проверяем все заявки для этой выписки
            for zayavka in all_zayavki:
                # Собираем плательщиков заявки через контрагентов
                candidate_payers = []
                
                if zayavka.agent_id and zayavka.agent_id.payer_ids:
                    candidate_payers.extend(zayavka.agent_id.payer_ids.ids)
                    
                if zayavka.client_id and zayavka.client_id.payer_ids:
                    candidate_payers.extend(zayavka.client_id.payer_ids.ids)
                
                if not candidate_payers:
                    continue
                
                # Проверяем, что все плательщики выписки есть среди кандидатов
                all_matched = all(payer_id in candidate_payers for payer_id in extract_payers)
                
                if not all_matched:
                    continue

                # Проверяем суммы заявки (в порядке приоритета)
                zayavka_sums = [
                    getattr(zayavka, 'application_amount_rub_contract', None),  # Заявка по курсу в рублях по договору
                    getattr(zayavka, 'total_fact', None),                # Итого факт
                    getattr(zayavka, 'contract_reward', None)            # Вознаграждение по договору
                ]
                
                # Находим первую непустую сумму
                zayavka_sum = None
                for sum_val in zayavka_sums:
                    if isinstance(sum_val, (int, float)) and sum_val is not None:
                        zayavka_sum = sum_val
                        break
                
                if zayavka_sum is None:
                    continue

                # Проверяем сумму с допуском
                if abs(zayavka_sum - extract_sum) <= TOLERANCE:
                    matching_zayavki.append(zayavka)
                    _logger.info(f"Найдено совпадение: выписка {extract.id} (сумма {extract_sum}) с заявкой {zayavka.zayavka_id} (сумма {zayavka_sum})")
            
            # Если нашли подходящие заявки, сохраняем их
            if matching_zayavki:
                extract_to_zayavki[extract] = matching_zayavki

        # Применяем обновления
        total_links = 0
        if extract_to_zayavki:
            _logger.info(f"Найдено {len(extract_to_zayavki)} выписок с подходящими заявками. Применение обновлений...")
            
            for extract, zayavki in extract_to_zayavki.items():
                # Собираем все ID заявок для связывания
                zayavka_ids = [z.id for z in zayavki]
                
                # Обновляем выписку - связываем со всеми найденными заявками
                extract.write({
                    'applications': [(6, 0, zayavka_ids)],  # 6,0,ids - заменяет все связи новым списком
                    'direction_choice': 'applications'
                })
                
                # Обновляем каждую заявку - добавляем обратную связь
                for zayavka in zayavki:
                    existing_extract_ids = [e.id for e in zayavka.extract_delivery_ids]
                    if extract.id not in existing_extract_ids:
                        zayavka.write({
                            'extract_delivery_ids': [(4, extract.id)]  # 4 - добавить связь
                        })
                
                total_links += len(zayavki)
                _logger.info(f"Выписка ID={extract.id} связана с {len(zayavki)} заявками: {[z.zayavka_id for z in zayavki]}")
        
        _logger.info(f"Процесс сопоставления завершен. Обработано выписок: {len(extract_to_zayavki)}, создано связей: {total_links}")
        return True
    
    @api.model
    def _run_stellar_tdk_logic(self):
        """
        Processes records for specific payers ("СТЕЛЛАР", "ТДК", "ИНДОТРЕЙД РФ"),
        assigns them a default wallet and contragents, and flags them for transfer creation.
        """
        _logger.info("Running Stellar/TDK/Indotrade logic...")
        
        allowed_names = {"СТЕЛЛАР", "ТДК", "ИНДОТРЕЙД РФ"}

        # Find the "Неразмеченные" wallet
        unassigned_wallet = self.env['amanat.wallet'].search([('name', '=', 'Неразмеченные')], limit=1)
        if not unassigned_wallet:
            _logger.warning("Wallet 'Неразмеченные' not found. Skipping Stellar/TDK logic.")
            return

        # Get records that have no deal assigned yet.
        records_to_process = self.search([('deal', '=', False)])

        for record in records_to_process:
            # Payer and Recipient must exist
            if not record.payer or not record.recipient:
                continue
                
            payer_name = (record.payer.name or "").strip().upper()
            recipient_name = (record.recipient.name or "").strip().upper()

            if payer_name in allowed_names and recipient_name in allowed_names:
                payer_contragent = record.payer.contragents_ids[0] if record.payer.contragents_ids else None
                recipient_contragent = record.recipient.contragents_ids[0] if record.recipient.contragents_ids else None

                update_vals = {
                    'wallet1': unassigned_wallet.id,
                    'wallet2': unassigned_wallet.id,
                    'create_transfer_bulinan': True,
                }
                if payer_contragent:
                    update_vals['counterparty1'] = payer_contragent.id
                if recipient_contragent:
                    update_vals['counterparty2'] = recipient_contragent.id

                # Use a try-except block to handle potential errors during write
                try:
                    # No need for with_context, the write trigger for create_transfer is intentional
                    record.write(update_vals)
                    _logger.info(f"Updated extract_delivery record {record.id} for Stellar/TDK/Indotrade and triggered transfer creation.")
                except Exception as e:
                    _logger.error(f"Failed to update record {record.id} in _run_stellar_tdk_logic: {e}")
        
        _logger.info("Stellar/TDK/Indotrade logic finished.")

    def diagnose_application_matching(self):
        """
        Диагностический метод для выявления проблем с сопоставлением заявок.
        Возвращает подробную информацию о том, почему заявки не находятся.
        """
        self.ensure_one()
        
        diagnosis = {
            'extract_id': self.id,
            'extract_payer': self.payer.name if self.payer else None,
            'extract_recipient': self.recipient.name if self.recipient else None,
            'extract_amount': self.amount,
            'extract_date': str(self.date) if self.date else None,
            'current_applications': len(self.applications),
            'issues': [],
            'potential_matches': [],
            'total_zayavki_with_date': 0,
            'total_zayavki_checked': 0
        }
        
        # Проверяем базовые данные выписки
        if not self.payer:
            diagnosis['issues'].append("У выписки не заполнен плательщик")
        if not self.recipient:
            diagnosis['issues'].append("У выписки не заполнен получатель")
        if not self.amount:
            diagnosis['issues'].append("У выписки не заполнена сумма")
            
        if diagnosis['issues']:
            return diagnosis
            
        extract_payers = [self.payer.id, self.recipient.id]
        extract_sum = self.amount
        TOLERANCE = 1.0
        
        # Ищем заявки с заполненной датой "Взята в работу"
        all_zayavki = self.env['amanat.zayavka'].search([('taken_in_work_date', '!=', False)])
        diagnosis['total_zayavki_with_date'] = len(all_zayavki)
        
        if not all_zayavki:
            diagnosis['issues'].append("Не найдено заявок с заполненной датой 'Взята в работу'")
            return diagnosis
        
        for zayavka in all_zayavki:
            diagnosis['total_zayavki_checked'] += 1
            match_info = {
                'zayavka_id': zayavka.zayavka_id,
                'zayavka_db_id': zayavka.id,
                'agent': zayavka.agent_id.name if zayavka.agent_id else None,
                'client': zayavka.client_id.name if zayavka.client_id else None,
                'issues': []
            }
            
            # Собираем плательщиков заявки через контрагентов
            candidate_payers = []
            
            if zayavka.agent_id and zayavka.agent_id.payer_ids:
                candidate_payers.extend(zayavka.agent_id.payer_ids.ids)
                match_info['agent_payers'] = [p.name for p in zayavka.agent_id.payer_ids]
            else:
                match_info['issues'].append("У агента нет связанных плательщиков")
                
            if zayavka.client_id and zayavka.client_id.payer_ids:
                candidate_payers.extend(zayavka.client_id.payer_ids.ids)
                match_info['client_payers'] = [p.name for p in zayavka.client_id.payer_ids]
            else:
                match_info['issues'].append("У клиента нет связанных плательщиков")
            
            if not candidate_payers:
                match_info['issues'].append("Нет плательщиков ни у агента, ни у клиента")
                diagnosis['potential_matches'].append(match_info)
                continue
            
            match_info['all_candidate_payers'] = candidate_payers
            
            # Проверяем, что все плательщики выписки есть среди кандидатов
            matched_payers = [p for p in extract_payers if p in candidate_payers]
            if len(matched_payers) != len(extract_payers):
                match_info['issues'].append(f"Не все плательщики выписки найдены среди кандидатов. Найдено: {len(matched_payers)} из {len(extract_payers)}")
                diagnosis['potential_matches'].append(match_info)
                continue
            
            match_info['payers_matched'] = True
            
            # Проверяем суммы заявки
            zayavka_sums = [
                ('application_amount_rub_contract', getattr(zayavka, 'application_amount_rub_contract', None)),
                ('total_fact', getattr(zayavka, 'total_fact', None)),
                ('contract_reward', getattr(zayavka, 'contract_reward', None))
            ]
            
            match_info['available_sums'] = {name: val for name, val in zayavka_sums if val is not None}
            
            # Находим первую непустую сумму
            zayavka_sum = None
            used_field = None
            for field_name, sum_val in zayavka_sums:
                if isinstance(sum_val, (int, float)) and sum_val is not None:
                    zayavka_sum = sum_val
                    used_field = field_name
                    break
            
            if zayavka_sum is None:
                match_info['issues'].append("Все поля с суммами пусты или не числовые")
                diagnosis['potential_matches'].append(match_info)
                continue
                
            match_info['used_sum_field'] = used_field
            match_info['used_sum_value'] = zayavka_sum
            match_info['extract_sum'] = extract_sum
            match_info['sum_difference'] = abs(zayavka_sum - extract_sum)
            
            # Проверяем сумму с допуском
            if abs(zayavka_sum - extract_sum) <= TOLERANCE:
                match_info['sum_matched'] = True
                match_info['is_perfect_match'] = True
                diagnosis['potential_matches'].append(match_info)
            else:
                match_info['sum_matched'] = False
                match_info['issues'].append(f"Сумма не совпадает. Разница: {abs(zayavka_sum - extract_sum)} (допуск: {TOLERANCE})")
                diagnosis['potential_matches'].append(match_info)
        
        # Подсчитываем идеальные совпадения
        perfect_matches = [m for m in diagnosis['potential_matches'] if m.get('is_perfect_match')]
        diagnosis['perfect_matches_count'] = len(perfect_matches)
        
        if not perfect_matches:
            diagnosis['issues'].append("Не найдено ни одного идеального совпадения")
        
        return diagnosis

    def force_application_matching(self):
        """
        Принудительно запускает сопоставление заявок для текущих записей.
        Использует улучшенную логику с детальным логированием.
        """
        matched_count = 0
        
        for record in self:
            # Пропускаем записи, которые уже имеют заявки или другие сделки
            if record.applications:
                _logger.info(f"Выписка {record.id} уже имеет связанные заявки: {record.applications.mapped('zayavka_id')}")
                continue
                
            if any([record.currency_reserve, record.transfer_ids, record.conversion, 
                   record.investment, record.gold_deal]):
                _logger.info(f"Выписка {record.id} уже имеет другие сделки, пропускаем")
                continue
            
            _logger.info(f"Принудительное сопоставление для выписки {record.id}")
            
            try:
                matching_apps = record._find_matching_applications()
                if matching_apps:
                    record.write({
                        'applications': [(6, 0, matching_apps.ids)],
                        'direction_choice': 'applications'
                    })
                    
                    # Обновляем обратную связь в заявках
                    for app in matching_apps:
                        app.write({
                            'extract_delivery_ids': [(4, record.id)]
                        })
                    
                    matched_count += 1
                    record.message_post(
                        body=f"Принудительное сопоставление: найдены и связаны заявки: {', '.join(matching_apps.mapped('zayavka_id'))}"
                    )
                    _logger.info(f"Принудительное сопоставление: выписка {record.id} связана с заявками: {matching_apps.mapped('zayavka_id')}")
                else:
                    record.message_post(body="Принудительное сопоставление: подходящие заявки не найдены")
                    _logger.info(f"Принудительное сопоставление: для выписки {record.id} подходящие заявки не найдены")
                    
                    # Запускаем диагностику для выяснения причин
                    diagnosis = record.diagnose_application_matching()
                    if diagnosis['issues']:
                        issues_text = "; ".join(diagnosis['issues'])
                        record.message_post(body=f"Диагностика показала проблемы: {issues_text}")
                        _logger.info(f"Диагностика выписки {record.id}: {issues_text}")
                        
            except Exception as e:
                _logger.error(f"Ошибка при принудительном сопоставлении заявок для выписки {record.id}: {e}")
                record.message_post(body=f"Ошибка при принудительном сопоставлении: {e}")
        
        if matched_count > 0:
            message = f"Принудительное сопоставление завершено. Обработано записей: {matched_count}"
        else:
            message = "Принудительное сопоставление завершено. Новых связей не создано."
            
        _logger.info(message)
        
        # Возвращаем сообщение пользователю
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Принудительное сопоставление',
                'message': message,
                'type': 'success' if matched_count > 0 else 'info',
                'sticky': False,
            }
        }

    @api.model 
    def diagnose_all_unmatched_extracts(self):
        """
        Запускает диагностику для всех несопоставленных выписок.
        Возвращает сводную информацию о проблемах.
        """
        unmatched_extracts = self.search([
            ('applications', '=', False),
            ('currency_reserve', '=', False),
            ('transfer_ids', '=', False),
            ('conversion', '=', False),
            ('investment', '=', False),
            ('gold_deal', '=', False),
        ])
        
        _logger.info(f"Найдено {len(unmatched_extracts)} несопоставленных выписок для диагностики")
        
        summary = {
            'total_unmatched': len(unmatched_extracts),
            'common_issues': {},
            'extracts_with_perfect_matches': 0,
            'extracts_with_partial_matches': 0,
            'extracts_with_no_matches': 0
        }
        
        for extract in unmatched_extracts[:10]:  # Ограничиваем для производительности
            diagnosis = extract.diagnose_application_matching()
            
            # Подсчитываем типы совпадений
            if diagnosis['perfect_matches_count'] > 0:
                summary['extracts_with_perfect_matches'] += 1
            elif diagnosis['potential_matches']:
                summary['extracts_with_partial_matches'] += 1
            else:
                summary['extracts_with_no_matches'] += 1
            
            # Собираем общие проблемы
            for issue in diagnosis['issues']:
                if issue in summary['common_issues']:
                    summary['common_issues'][issue] += 1
                else:
                    summary['common_issues'][issue] = 1
        
        _logger.info(f"Диагностика завершена: {summary}")
        return summary

    def show_diagnosis_result(self):
        """
        Показывает результаты диагностики пользователю в удобном виде.
        """
        self.ensure_one()
        diagnosis = self.diagnose_application_matching()
        
        # Формируем детальное сообщение
        message_parts = []
        message_parts.append(f"<h3>Диагностика выписки {self.name}</h3>")
        message_parts.append(f"<p><strong>Плательщик:</strong> {diagnosis['extract_payer']}</p>")
        message_parts.append(f"<p><strong>Получатель:</strong> {diagnosis['extract_recipient']}</p>")
        message_parts.append(f"<p><strong>Сумма:</strong> {diagnosis['extract_amount']}</p>")
        message_parts.append(f"<p><strong>Дата:</strong> {diagnosis['extract_date']}</p>")
        message_parts.append(f"<p><strong>Текущих заявок:</strong> {diagnosis['current_applications']}</p>")
        
        if diagnosis['issues']:
            message_parts.append("<h4 style='color: red;'>Обнаруженные проблемы:</h4>")
            message_parts.append("<ul>")
            for issue in diagnosis['issues']:
                message_parts.append(f"<li>{issue}</li>")
            message_parts.append("</ul>")
        
        message_parts.append(f"<p><strong>Всего заявок с датой 'Взята в работу':</strong> {diagnosis['total_zayavki_with_date']}</p>")
        message_parts.append(f"<p><strong>Проверено заявок:</strong> {diagnosis['total_zayavki_checked']}</p>")
        message_parts.append(f"<p><strong>Идеальных совпадений:</strong> {diagnosis['perfect_matches_count']}</p>")
        
        if diagnosis['potential_matches']:
            message_parts.append("<h4>Потенциальные совпадения:</h4>")
            message_parts.append("<ul>")
            for match in diagnosis['potential_matches'][:5]:  # Показываем только первые 5
                match_issues = ", ".join(match.get('issues', []))
                if match.get('is_perfect_match'):
                    message_parts.append(f"<li style='color: green;'><strong>✓ {match['zayavka_id']}</strong> - ИДЕАЛЬНОЕ СОВПАДЕНИЕ</li>")
                else:
                    message_parts.append(f"<li><strong>{match['zayavka_id']}</strong> - Проблемы: {match_issues}</li>")
            message_parts.append("</ul>")
        
        message = "".join(message_parts)
        
        # Отправляем сообщение в чат записи
        self.message_post(body=message)
        
        # Возвращаем уведомление
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Диагностика завершена',
                'message': f'Найдено {diagnosis["perfect_matches_count"]} идеальных совпадений. Детали см. в чате записи.',
                'type': 'success' if diagnosis['perfect_matches_count'] > 0 else 'warning',
                'sticky': True,
            }
        }
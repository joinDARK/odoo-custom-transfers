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
        tracking=True
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
        Основная логика сопоставления выписок с заявками,
        основанная на актуальном скрипте Airtable.
        """
        _logger.info("Запуск автоматического сопоставления Выписок и Заявок.")
        TOLERANCE = 1.0
        fields_to_check = [
            'application_amount_rub_contract',
            'contract_reward',
            'total_fact'
        ]

        # 1. Загружаем все необходимые записи один раз для производительности
        all_zayavki = self.env['amanat.zayavka'].search([('taken_in_work_date', '!=', False)])
        
        # Получаем все выписки, которые еще не связаны ни с какой сделкой или заявкой
        # Это основной набор кандидатов для сопоставления
        candidate_extracts = self.env['amanat.extract_delivery'].search([
            ('deal', '=', False),
            ('applications', '=', False)
        ])
        
        # Кэшируем плательщиков для контрагентов, чтобы не запрашивать их в цикле
        all_contragents = all_zayavki.mapped('agent_id') + all_zayavki.mapped('client_id')
        contragent_payers_map = {
            c.id: c.payer_ids.ids for c in all_contragents.filtered(lambda c: c.payer_ids)
        }

        # 2. Основная логика сопоставления
        used_extract_ids = set()
        updates = []
        
        for zayavka in all_zayavki:
            # Собираем ID плательщиков-кандидатов для текущей заявки
            candidate_payer_ids = set()
            if zayavka.agent_id and zayavka.agent_id.id in contragent_payers_map:
                candidate_payer_ids.update(contragent_payers_map[zayavka.agent_id.id])
            if zayavka.client_id and zayavka.client_id.id in contragent_payers_map:
                candidate_payer_ids.update(contragent_payers_map[zayavka.client_id.id])

            if not candidate_payer_ids:
                continue
                
            # Фильтруем выписки-кандидаты
            best_match = None
            matching_extracts = []

            for extract in candidate_extracts:
                if extract.id in used_extract_ids:
                    continue
                    
                # Проверка плательщиков: все плательщики и получатели выписки должны быть среди кандидатов
                extract_party_ids = {p.id for p in (extract.payer, extract.recipient) if p}
                if not extract_party_ids or not extract_party_ids.issubset(candidate_payer_ids):
                    continue
                    
                # Проверка суммы
                sum_matches = False
                for field_name in fields_to_check:
                    zayavka_sum = getattr(zayavka, field_name, None)
                    if isinstance(zayavka_sum, (int, float)) and abs(zayavka_sum - (extract.amount or 0.0)) <= TOLERANCE:
                            sum_matches = True
                            break
                            
                if not sum_matches:
                    continue
                    
                matching_extracts.append(extract)

            # Если есть совпадения, выбираем лучшее (самое раннее по дате)
            if matching_extracts:
                matching_extracts.sort(key=lambda r: r.date or fields.Date.today())
                best_match = matching_extracts[0]

                updates.append({
                    'extract_id': best_match.id,
                    'zayavka_id': zayavka.id,
                })
                used_extract_ids.add(best_match.id)
        
        # 3. Применяем обновления пакетами
        if updates:
            _logger.info(f"Найдено {len(updates)} сопоставлений. Применение обновлений...")
            for update in updates:
                extract_to_update = self.env['amanat.extract_delivery'].browse(update['extract_id'])
                zayavka_to_link = self.env['amanat.zayavka'].browse(update['zayavka_id'])
                
                extract_to_update.write({
                    'applications': [(4, zayavka_to_link.id)],
                    'direction_choice': 'applications'
                })
                # Odoo автоматически обработает симметричную M2M связь,
                zayavka_to_link.write({
                    'extract_delivery_ids': [(4, extract_to_update.id)]
                })
        
        _logger.info(f"Процесс сопоставления завершен. Найдено {len(updates)} сопоставлений.")
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
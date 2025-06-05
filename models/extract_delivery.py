# models/extract_delivery.py
from odoo import models, fields, api
from .base_model import AmanatBaseModel
import logging

_logger = logging.getLogger(__name__)

class Extract_delivery(models.Model, AmanatBaseModel):
    _name = 'amanat.extract_delivery'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Выписка разнос'

    name = fields.Char(string="Номер платежа", tracking=True, readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('amanat.extract_delivery.sequence'), copy=False)
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
    assign_bulinan = fields.Boolean(string="Разнести булинан", tracking=True)
    create_transfer_bulinan = fields.Boolean(string="Создать перевод булинан", tracking=True)
    dds_article = fields.Selection([
        ('operational', 'Операционные потоки'),
        ('investment', 'Инвестиционные потоки'),
        ('financial', 'Финансовые потоки'),
        ('not_applicable', 'Не относится')
    ], string="Статья ДДС", tracking=True)
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
    remaining_statement = fields.Float(string="Остаток для исходной выписки", tracking=True)
    
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

    remaining_statement = fields.Float(string="Остаток для исходной выписки", tracking=True)

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

    def write(self, vals):
        res = super().write(vals)
        if vals.get('fragment_statement'):
            for rec in self.filtered('fragment_statement'):
                rec.action_fragment_statement()
                rec.match_extract_with_zayavka()
                rec.fragment_statement = False
        return res

    @api.model
    def create(self, vals):
        res = super().create(vals)
        trigger = vals.get('fragment_statement', False)
        if trigger:
            res.action_fragment_statement()
            res.match_extract_with_zayavka()
            res.fragment_statement = False
        return res
    
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
                
                used_extract_ids.add(best_extract.id)
                
                _logger.info(f"Связана выписка ID={best_extract.id} с заявкой ID={zayavka.id}")
        
        _logger.info(f"Сопоставление завершено. Обработано заявок: {len(zayavka_records)}, связано выписок: {len(used_extract_ids)}")
        return True
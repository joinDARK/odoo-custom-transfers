from odoo import models, fields, api
from .base_model import AmanatBaseModel
import logging

_logger = logging.getLogger(__name__)

class AmanatSwiftDocumentUpload(models.Model, AmanatBaseModel):
    _name = 'amanat.swift_document_upload'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Загрузка SWIFT документов'
    _order = 'create_date desc'

    # Основные поля
    swift_file = fields.Binary(
        string='SWIFT документ',
        required=True
    )
    
    swift_file_name = fields.Char(
        string='Имя файла'
    )

    manager_id = fields.Many2one(
        'amanat.manager',
        string='Менеджер',
        required=False,
        tracking=True
    )
    
    currency = fields.Char(
        string='Валюта',
        required=False,
        tracking=True
    )
    
    amount = fields.Float(
        string='Сумма',
        required=False,
        digits=(16, 2),
        tracking=True
    )
    
    payer_subagent = fields.Char(
        string='Плательщик субагента',
        required=False,
        tracking=True,
        help='Имя плательщика субагента для поиска заявки в поле subagent_payer_ids'
    )
    
    payment_date = fields.Date(
        string='Дата платежа',
        tracking=True,
        help='Дата оплаты валюты поставщику субагенту'
    )
    
    swift_code = fields.Char(
        string='Код SWIFT',
        tracking=True,
        help='Код SWIFT операции'
    )
    
    application_sequence = fields.Char(
        string='Номер заявки',
        tracking=True,
        help='Номер заявки из SWIFT документа для точного поиска'
    )
    
    # Связанная заявка
    zayavka_id = fields.Many2one(
        'amanat.zayavka',
        string='Связанная заявка',
        compute='_compute_zayavka_id',
        store=True,
        tracking=True,
        help='Заявка, найденная автоматически по плательщику субагента с проверкой валюты, суммы и отсутствия SWIFT файлов'
    )
    
    # Статус обработки
    processing_status = fields.Selection([
        ('pending', 'Ожидает обработки'),
        ('processed', 'Обработано'),
        ('error', 'Ошибка обработки'),
        ('no_zayavka', 'Заявка не найдена')
    ], string='Статус обработки', default='pending', tracking=True)
    
    processing_notes = fields.Text(
        string='Примечания к обработке',
        help='Детали обработки документа'
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Переопределяем создание для автоматической обработки"""
        _logger.info("[SWIFT AUTO] === НАЧАЛО СОЗДАНИЯ swift_document_upload ===")
        _logger.info(f"[SWIFT AUTO] Получены данные для создания: {vals_list}")
        
        # Проверяем сколько заявок было ДО создания
        zayavka_count_before = self.env['amanat.zayavka'].search_count([])
        _logger.info(f"[SWIFT AUTO] Количество заявок ДО создания swift_document_upload: {zayavka_count_before}")
        
        records = super().create(vals_list)
        _logger.info(f"[SWIFT AUTO] Создано записей swift_document_upload: {len(records)}")
        
        # Проверяем сколько заявок стало ПОСЛЕ создания (но ДО автоматизации)
        zayavka_count_after_create = self.env['amanat.zayavka'].search_count([])
        _logger.info(f"[SWIFT AUTO] Количество заявок ПОСЛЕ создания swift_document_upload (до автоматизации): {zayavka_count_after_create}")
        
        if zayavka_count_after_create > zayavka_count_before:
            _logger.error(f"[SWIFT AUTO] ⚠️ ВНИМАНИЕ! Заявка была создана ВНЕ нашей автоматизации! Было: {zayavka_count_before}, стало: {zayavka_count_after_create}")
        
        for record in records:
            try:
                _logger.info(f"[SWIFT AUTO] Запускаем автоматизацию для записи {record.id} с плательщиком '{record.payer_subagent}'")
                # Запускаем автоматизацию при создании записи
                record._process_swift_document_automation()
            except Exception as e:
                _logger.error(f"Ошибка при автоматической обработке SWIFT документа {record.id}: {str(e)}")
                record.processing_status = 'error'
                record.processing_notes = f"Ошибка автоматизации: {str(e)}"
        
        # Проверяем финальное количество заявок
        zayavka_count_final = self.env['amanat.zayavka'].search_count([])
        _logger.info(f"[SWIFT AUTO] Итоговое количество заявок ПОСЛЕ автоматизации: {zayavka_count_final}")
        
        if zayavka_count_final > zayavka_count_after_create:
            _logger.error("[SWIFT AUTO] ⚠️ ВНИМАНИЕ! Заявка была создана НАШЕЙ автоматизацией! Это НЕ должно происходить!")
        
        _logger.info("[SWIFT AUTO] === КОНЕЦ СОЗДАНИЯ swift_document_upload ===")
        return records

    def _process_swift_document_automation(self):
        """Основная логика автоматизации SWIFT документов - ТОЛЬКО линковка с существующей заявкой"""
        self.ensure_one()
        
        _logger.info(f"[SWIFT AUTO] Начинаем обработку SWIFT документа {self.id} для плательщика '{self.payer_subagent}'")
        _logger.info(f"[SWIFT AUTO] Данные SWIFT документа: валюта={self.currency}, сумма={self.amount}, плательщик={self.payer_subagent}")
        _logger.info(f"[SWIFT AUTO] Текущее состояние zayavka_id: {self.zayavka_id}")
        _logger.info(f"[SWIFT AUTO] Файл присутствует: {bool(self.swift_file)}, имя файла: {self.swift_file_name}")
        
        # Предварительная проверка обязательных полей
        if not self.payer_subagent:
            self.processing_status = 'error'
            self.processing_notes = "Не указан плательщик субагента. Автоматизация невозможна."
            _logger.error(f"[SWIFT AUTO] ❌ Отсутствует плательщик субагента в SWIFT документе {self.id}")
            return
        
        if not self.currency:
            self.processing_status = 'error'
            self.processing_notes = "Не указана валюта в SWIFT документе. Автоматизация невозможна."
            _logger.error(f"[SWIFT AUTO] ❌ Отсутствует валюта в SWIFT документе {self.id}")
            return
        
        if not self.amount:
            self.processing_status = 'error'
            self.processing_notes = "Не указана сумма в SWIFT документе. Автоматизация невозможна."
            _logger.error(f"[SWIFT AUTO] ❌ Отсутствует сумма в SWIFT документе {self.id}")
            return
        
        # Шаг 1: Найти СУЩЕСТВУЮЩУЮ заявку (НЕ создавать новую!)
        zayavka = self._find_matching_zayavka()
        
        if not zayavka:
            self.processing_status = 'no_zayavka'
            self.processing_notes = f"Подходящая заявка не найдена для плательщика субагента '{self.payer_subagent}'. Требования: совпадение валюты ({self.currency}), суммы ({self.amount}), отсутствие прикрепленных SWIFT файлов. Создание новой заявки НЕ разрешено."
            _logger.warning(f"[SWIFT AUTO] ❌ ПОДХОДЯЩАЯ ЗАЯВКА НЕ НАЙДЕНА для плательщика субагента '{self.payer_subagent}' с учетом всех проверок. Обработка ОСТАНОВЛЕНА.")
            _logger.warning("[SWIFT AUTO] ❌ НОВАЯ ЗАЯВКА НЕ БУДЕТ СОЗДАНА! Это правильное поведение.")
            return
        
        _logger.info(f"[SWIFT AUTO] Найдена существующая заявка {zayavka.id} для плательщика '{self.payer_subagent}'")
        
        # Шаг 2: Линкуем swift_document_upload с найденной заявкой
        _logger.info(f"[SWIFT AUTO] Устанавливаем связь: swift_document_upload {self.id} -> заявка {zayavka.id}")
        self.zayavka_id = zayavka.id
        _logger.info(f"[SWIFT AUTO] ✅ Связь установлена успешно: swift_document_upload {self.id} связан с заявкой {zayavka.id}")
        _logger.info(f"[SWIFT AUTO] Проверяем установленную связь: self.zayavka_id = {self.zayavka_id}")
        
        # Шаг 3: Загружаем SWIFT документ в заявку (в поле swift_attachments)
        attachment = self._upload_document_to_zayavka(zayavka)
        
        if not attachment:
            self.processing_status = 'error'
            self.processing_notes = "Ошибка при загрузке SWIFT документа в заявку"
            _logger.error(f"[SWIFT AUTO] Ошибка загрузки документа в заявку {zayavka.id}")
            return
        
        _logger.info(f"[SWIFT AUTO] SWIFT документ успешно загружен в заявку {zayavka.id}, attachment ID: {attachment.id}")
        
        # Шаг 4: Встроенная автоматизация заявки уже запустилась при добавлении в swift_attachments
        # НЕ запускаем Yandex GPT анализ - только базовая автоматизация по SWIFT
        
        # Шаг 5: Обновляем статус обработки
        self.processing_status = 'processed'
        self.processing_notes = f"Успешно обработано. SWIFT документ загружен в заявку {zayavka.zayavka_num or zayavka.id}. Автоматизация заявки запущена."
        
        _logger.info("[SWIFT AUTO] ✅ Обработка завершена успешно!")
        _logger.info(f"[SWIFT AUTO] ✅ Документ {self.id} связан с заявкой {zayavka.id}")
        _logger.info(f"[SWIFT AUTO] ✅ Финальное состояние zayavka_id: {self.zayavka_id}")
        _logger.info(f"[SWIFT AUTO] ✅ Статус обработки: {self.processing_status}")
        _logger.info(f"[SWIFT AUTO] ✅ Примечания: {self.processing_notes}")

    def _normalize_currency(self, currency):
        """Нормализация валютных кодов для сравнения с расширенным набором вариантов"""
        if not currency:
            return ""
        
        # Словарь соответствия различных вариантов валют
        currency_mapping = {
            # EUR варианты
            'eur': 'eur',
            'euro': 'eur',
            'euros': 'eur',
            'евро': 'eur',
            '€': 'eur',
            'eur.': 'eur',
            'euro.': 'eur',
            
            # USD варианты  
            'usd': 'usd',
            'dollar': 'usd',
            'dollars': 'usd',
            'доллар': 'usd',
            'доллары': 'usd',
            '$': 'usd',
            'usd.': 'usd',
            'dollar.': 'usd',
            'us dollar': 'usd',
            'us dollars': 'usd',
            
            # CNY варианты
            'cny': 'cny',
            'yuan': 'cny',
            'rmb': 'cny',
            'юань': 'cny',
            '¥': 'cny',
            'cny.': 'cny',
            'yuan.': 'cny',
            'chinese yuan': 'cny',
            
            # AED варианты
            'aed': 'aed',
            'dirham': 'aed',
            'dirhams': 'aed',
            'дирхам': 'aed',
            'дирхамы': 'aed',
            'dh': 'aed',
            'aed.': 'aed',
            'dirham.': 'aed',
            'uae dirham': 'aed',
            
            # RUB варианты
            'rub': 'rub',
            'ruble': 'rub',
            'rubles': 'rub',
            'рубль': 'rub',
            'рубли': 'rub',
            '₽': 'rub',
            'rub.': 'rub',
            'ruble.': 'rub',
            'russian ruble': 'rub',
            
            # GBP варианты
            'gbp': 'gbp',
            'pound': 'gbp',
            'pounds': 'gbp',
            'фунт': 'gbp',
            'фунты': 'gbp',
            '£': 'gbp',
            'gbp.': 'gbp',
            'pound.': 'gbp',
            'british pound': 'gbp',
            
            # JPY варианты
            'jpy': 'jpy',
            'yen': 'jpy',
            'йена': 'jpy',
            'йены': 'jpy',
            'jpy.': 'jpy',
            'yen.': 'jpy',
            'japanese yen': 'jpy',
            
            # CHF варианты
            'chf': 'chf',
            'franc': 'chf',
            'francs': 'chf',
            'франк': 'chf',
            'франки': 'chf',
            'chf.': 'chf',
            'franc.': 'chf',
            'swiss franc': 'chf',
            
            # CAD варианты
            'cad': 'cad',
            'canadian dollar': 'cad',
            'canadian dollars': 'cad',
            'cad.': 'cad',
            
            # KZT варианты
            'kzt': 'kzt',
            'tenge': 'kzt',
            'тенге': 'kzt',
            'kzt.': 'kzt',
            'tenge.': 'kzt',
            'kazakhstani tenge': 'kzt',
            '₸': 'kzt',
            
            # TRY варианты
            'try': 'try',
            'lira': 'try',
            'лира': 'try',
            'try.': 'try',
            'lira.': 'try',
            'turkish lira': 'try',
        }
        
        # Нормализуем входную строку
        normalized = currency.strip().lower()
        # Убираем лишние пробелы
        normalized = ' '.join(normalized.split())
        
        return currency_mapping.get(normalized, normalized)

    def _check_amount_match(self, zayavka, swift_amount, tolerance=0.01):
        """
        Проверяет совпадение суммы SWIFT документа с различными полями суммы в заявке
        
        Args:
            zayavka: Запись заявки
            swift_amount: Сумма из SWIFT документа
            tolerance: Допустимая погрешность при сравнении (по умолчанию 0.01)
            
        Returns:
            dict: {'match': bool, 'details': str, 'matched_field': str}
        """
        if not swift_amount:
            return {'match': False, 'details': 'Сумма в SWIFT документе не указана', 'matched_field': None}
        
        # Приоритетный список полей сумм для проверки
        amount_fields = [
            ('amount', 'Основная сумма заявки'),
            ('application_amount_rub_contract', 'Заявка по курсу в рублях по договору'),
            ('total_client', 'Итого Клиент'),
            ('total_sber', 'Итого Сбербанк'),
            ('total_sovok', 'Итого Совкомбанк'),
            ('contract_reward', 'Вознаграждение по договору'),
            ('total_fact', 'Итого факт'),
            ('equivalent_amount_usd', 'Эквивалентная сумма в USD'),
            ('fin_res_client_real_rub', 'Финансовый результат клиент в рублях'),
            ('fin_res_sber_real_rub', 'Финансовый результат Сбер в рублях'),
        ]
        
        _logger.info(f"[AMOUNT MATCH] Проверяем сумму SWIFT {swift_amount} против полей заявки {zayavka.id}")
        
        # Проверяем каждое поле по приоритету
        for field_name, field_description in amount_fields:
            if hasattr(zayavka, field_name):
                zayavka_amount = getattr(zayavka, field_name, None)
                
                if zayavka_amount is not None and isinstance(zayavka_amount, (int, float)):
                    difference = abs(float(swift_amount) - float(zayavka_amount))
                    
                    _logger.info(f"[AMOUNT MATCH] Поле '{field_name}' ({field_description}): "
                               f"SWIFT={swift_amount}, Заявка={zayavka_amount}, Разница={difference:.4f}")
                    
                    if difference <= tolerance:
                        details = f"Совпадение по полю '{field_name}' ({field_description}): SWIFT={swift_amount}, Заявка={zayavka_amount}, Разница={difference:.4f}"
                        return {'match': True, 'details': details, 'matched_field': field_name}
        
        # УБИРАЕМ МЯГКИЕ КРИТЕРИИ - они приводят к неправильному связыванию!
        # Требуем точного совпадения суммы (с допуском только 0.01)
        _logger.info("[AMOUNT MATCH] Точного совпадения не найдено. Мягкие критерии ОТКЛЮЧЕНЫ для предотвращения ошибок.")
        
        # Собираем информацию о всех проверенных полях для детального отчета
        checked_fields = []
        for field_name, field_description in amount_fields:
            if hasattr(zayavka, field_name):
                zayavka_amount = getattr(zayavka, field_name, None)
                if zayavka_amount is not None:
                    checked_fields.append(f"{field_name}={zayavka_amount}")
        
        details = f"Сумма не совпадает ни с одним полем. SWIFT={swift_amount}, Проверенные поля заявки: {', '.join(checked_fields)}"
        return {'match': False, 'details': details, 'matched_field': None}

    def _validate_zayavka_basic_conditions(self, zayavka):
        """Базовая проверка условий: валюта, сумма и отсутствие прикрепленных SWIFT файлов"""
        if not zayavka:
            return False
        
        # СТРОГАЯ проверка валюты - оба поля должны быть заполнены и совпадать
        if not self.currency:
            _logger.info(f"[SWIFT AUTO] Заявка {zayavka.id} отклонена: валюта не указана в SWIFT документе")
            return False
        
        if not zayavka.currency:
            _logger.info(f"[SWIFT AUTO] Заявка {zayavka.id} отклонена: валюта не указана в заявке")
            return False
        
        # УЛУЧШЕННАЯ проверка валюты с нормализацией
        swift_currency_normalized = self._normalize_currency(self.currency)
        zayavka_currency_normalized = self._normalize_currency(zayavka.currency)
        
        if swift_currency_normalized != zayavka_currency_normalized:
            _logger.info(f"[SWIFT AUTO] Заявка {zayavka.id} отклонена: валюта не совпадает (SWIFT: {self.currency} -> {swift_currency_normalized}, Заявка: {zayavka.currency} -> {zayavka_currency_normalized})")
            return False
        
        # СТРОГАЯ проверка суммы
        if not self.amount:
            _logger.info(f"[SWIFT AUTO] Заявка {zayavka.id} отклонена: сумма не указана в SWIFT документе")
            return False
        
        # Проверяем сумму по приоритетному списку полей заявки
        amount_match_result = self._check_amount_match(zayavka, self.amount)
        if not amount_match_result['match']:
            _logger.info(f"[SWIFT AUTO] Заявка {zayavka.id} отклонена: сумма не совпадает. {amount_match_result['details']}")
            return False
        else:
            _logger.info(f"[SWIFT AUTO] Заявка {zayavka.id}: сумма совпадает. {amount_match_result['details']}")
        
        # Проверка отсутствия прикрепленных SWIFT файлов
        if zayavka.swift_attachments:
            _logger.info(f"[SWIFT AUTO] Заявка {zayavka.id} отклонена: уже есть прикрепленные SWIFT документы ({len(zayavka.swift_attachments)} файлов)")
            return False
        
        # Проверка статуса заявки (логируем, но не блокируем)
        if zayavka.status == '21':
            _logger.warning(f"[SWIFT AUTO] ⚠️  Заявка {zayavka.id} имеет статус '21' (закрыта), но может быть связана")
        
        _logger.info(f"[SWIFT AUTO] Заявка {zayavka.id} прошла все базовые проверки: валюта={zayavka.currency}, сумма={zayavka.amount}, статус={zayavka.status}, SWIFT файлов=0")
        return True

    def _find_matching_zayavka(self):
        """Поиск существующей заявки по плательщику субагента с дополнительными проверками валюты, суммы и отсутствия файлов"""
        
        # ПРИОРИТЕТНЫЙ ПОИСК: Если указан номер заявки, ищем по нему в первую очередь
        if self.application_sequence:
            _logger.info(f"[SWIFT AUTO] 🎯 Найден номер заявки в SWIFT документе: '{self.application_sequence}'. Ищем точное совпадение.")
            try:
                # Ищем по полю application_sequence
                zayavka_by_seq = self.env['amanat.zayavka'].search([
                    ('application_sequence', '=', self.application_sequence)
                ], limit=1)
                
                if zayavka_by_seq:
                    _logger.info(f"[SWIFT AUTO] ✅ Найдена заявка {zayavka_by_seq.id} по номеру заявки '{self.application_sequence}'")
                    
                    # Проверяем базовые условия (валюта, сумма, отсутствие SWIFT файлов)
                    def _validate_zayavka_conditions_strict(zayavka):
                        return self._validate_zayavka_basic_conditions(zayavka)
                    
                    if _validate_zayavka_conditions_strict(zayavka_by_seq):
                        _logger.info(f"[SWIFT AUTO] ✅ Заявка {zayavka_by_seq.id} прошла все проверки по номеру заявки")
                        return zayavka_by_seq
                    else:
                        _logger.warning(f"[SWIFT AUTO] ⚠️ Заявка {zayavka_by_seq.id} найдена по номеру, но не прошла проверки валюты/суммы/SWIFT файлов")
                else:
                    _logger.info(f"[SWIFT AUTO] ❌ Заявка с номером '{self.application_sequence}' не найдена")
            except Exception as e:
                _logger.error(f"[SWIFT AUTO] Ошибка поиска по номеру заявки: {e}")
        
        if not self.payer_subagent:
            _logger.error(f"[SWIFT AUTO] ❌ Плательщик субагента не указан в SWIFT документе {self.id}")
            return None
        
        # Используем централизованную функцию для проверки условий
        
        # Сначала пробуем старую логику для точных совпадений
        # 1. Точное совпадение с проверками - используем правильное поле Many2many
        try:
            # Пробуем разные возможные поля для плательщиков субагентов
            search_domains = [
                ('subagent_payer_ids.name', '=', self.payer_subagent),  # Основное поле
                ('payer_ids.name', '=', self.payer_subagent),           # Альтернативное поле
            ]
            
            zayavka = None
            for domain in search_domains:
                try:
                    zayavka = self.env['amanat.zayavka'].search([domain], limit=1)
                    if zayavka:
                        _logger.info(f"[SWIFT AUTO] Заявка найдена через домен: {domain}")
                        break
                except Exception as domain_error:
                    _logger.warning(f"[SWIFT AUTO] Ошибка поиска с доменом {domain}: {domain_error}")
                    continue
            
            if zayavka and self._validate_zayavka_basic_conditions(zayavka):
                _logger.info(f"[SWIFT AUTO] Найдена подходящая заявка по точному совпадению: {zayavka.id}")
                return zayavka
            elif zayavka:
                _logger.info(f"[SWIFT AUTO] Заявка {zayavka.id} найдена по точному совпадению, но не прошла дополнительные проверки")
        
        except Exception as e:
            _logger.warning(f"[SWIFT AUTO] Ошибка точного поиска плательщика: {e}")
        
        # 2. Нечеткий поиск ilike
        try:
            search_domains_ilike = [
                ('subagent_payer_ids.name', 'ilike', self.payer_subagent),
                ('payer_ids.name', 'ilike', self.payer_subagent),
            ]
            
            zayavka = None
            for domain in search_domains_ilike:
                try:
                    zayavka = self.env['amanat.zayavka'].search([domain], limit=1)
                    if zayavka:
                        _logger.info(f"[SWIFT AUTO] Заявка найдена через ilike домен: {domain}")
                        break
                except Exception as domain_error:
                    _logger.warning(f"[SWIFT AUTO] Ошибка ilike поиска с доменом {domain}: {domain_error}")
                    continue
        
            if zayavka and self._validate_zayavka_basic_conditions(zayavka):
                _logger.info(f"[SWIFT AUTO] Найдена подходящая заявка по ilike поиску: {zayavka.id}")
                return zayavka
            elif zayavka:
                _logger.info(f"[SWIFT AUTO] Заявка {zayavka.id} найдена по ilike поиску, но не прошла дополнительные проверки")
        
        except Exception as e:
            _logger.warning(f"[SWIFT AUTO] Ошибка нечеткого поиска плательщика: {e}")
        
        # 3. Улучшенный алгоритм нечеткого поиска - ищем среди кандидатов, которые проходят строгие проверки
        _logger.info(f"[SWIFT AUTO] Переходим к улучшенному нечеткому поиску для плательщика '{self.payer_subagent}'")
        
        try:
            best_zayavka = self._find_best_matching_zayavka_with_validation(self._validate_zayavka_basic_conditions)
            
            if best_zayavka:
                _logger.info(f"[SWIFT AUTO] ✅ Найдена подходящая заявка с улучшенным алгоритмом поиска: {best_zayavka.id}")
                return best_zayavka
        
        except Exception as e:
            _logger.error(f"[SWIFT AUTO] Ошибка улучшенного нечеткого поиска: {e}")
        
        # 4. УБИРАЕМ МЯГКУЮ ВАЛИДАЦИЮ - она приводит к неправильному связыванию!
        # Если строгий поиск не дал результата, НЕ привязываем документ к заявке
        _logger.warning(f"[SWIFT AUTO] ❌ Заявка не найдена строгими методами поиска для плательщика '{self.payer_subagent}'")
        _logger.warning("[SWIFT AUTO] ❌ SWIFT документ НЕ БУДЕТ привязан к заявке для предотвращения ошибочного связывания")
        _logger.info(f"[SWIFT AUTO] Данные SWIFT документа: валюта={self.currency}, сумма={self.amount}, плательщик='{self.payer_subagent}'")
        return None

    def _find_best_matching_zayavka_by_payer_name(self):
        """Улучшенный алгоритм поиска ближайшего совпадения по имени плательщика субагента"""
        import re
        from difflib import SequenceMatcher
        
        if not self.payer_subagent:
            return None
        
        def _normalize_string(s):
            """Нормализация строки для сравнения"""
            if not s:
                return ""
            # Приводим к нижнему регистру, убираем лишние пробелы и знаки препинания
            normalized = re.sub(r'[^\w\s]', '', s.lower()).strip()
            normalized = re.sub(r'\s+', ' ', normalized)  # Заменяем множественные пробелы на одинарные
            return normalized
        
        def _calculate_similarity(str1, str2):
            """Вычисляем сходство между двумя строками (0.0 - 1.0)"""
            return SequenceMatcher(None, str1, str2).ratio()
        
        def _check_token_overlap(tokens1, tokens2):
            """Проверяем пересечение токенов между двумя наборами"""
            if not tokens1 or not tokens2:
                return 0.0
            
            common_tokens = set(tokens1) & set(tokens2)
            total_tokens = len(set(tokens1) | set(tokens2))
            
            if total_tokens == 0:
                return 0.0
            
            return len(common_tokens) / total_tokens
        
        # Нормализуем исходное имя плательщика
        normalized_payer = _normalize_string(self.payer_subagent)
        payer_tokens = set(normalized_payer.split())
        
        _logger.info(f"[SWIFT AUTO FUZZY] Ищем ближайшее совпадение для плательщика: '{self.payer_subagent}' (нормализовано: '{normalized_payer}')")
        _logger.info(f"[SWIFT AUTO FUZZY] Токены плательщика: {payer_tokens}")
        
        # Получаем все заявки с плательщиками субагентов
        all_zayavkas = self.env['amanat.zayavka'].search([
            ('subagent_payer_ids', '!=', False)
        ])
        
        best_match = None
        best_score = 0.0
        candidates = []
        
        for zayavka in all_zayavkas:
            for payer in zayavka.subagent_payer_ids:
                if not payer.name:
                    continue
                
                normalized_candidate = _normalize_string(payer.name)
                candidate_tokens = set(normalized_candidate.split())
                
                # Рассчитываем различные метрики сходства
                string_similarity = _calculate_similarity(normalized_payer, normalized_candidate)
                token_overlap = _check_token_overlap(payer_tokens, candidate_tokens)
                
                # Итоговый скор - взвешенная сумма метрик
                final_score = (string_similarity * 0.6) + (token_overlap * 0.4)
                
                candidates.append({
                    'zayavka': zayavka,
                    'payer_name': payer.name,
                    'normalized_name': normalized_candidate,
                    'string_similarity': string_similarity,
                    'token_overlap': token_overlap,
                    'final_score': final_score
                })
                
                if final_score > best_score:
                    best_score = final_score
                    best_match = zayavka
        
        # Логирование результатов
        _logger.info(f"[SWIFT AUTO FUZZY] Найдено кандидатов: {len(candidates)}")
        
        # Сортируем кандидатов по скору для логирования топ-5
        top_candidates = sorted(candidates, key=lambda x: x['final_score'], reverse=True)[:5]
        
        for i, candidate in enumerate(top_candidates, 1):
            _logger.info(f"[SWIFT AUTO FUZZY] Топ-{i}: Заявка {candidate['zayavka'].id}, "
                        f"плательщик '{candidate['payer_name']}', "
                        f"строковое сходство: {candidate['string_similarity']:.3f}, "
                        f"пересечение токенов: {candidate['token_overlap']:.3f}, "
                        f"итоговый скор: {candidate['final_score']:.3f}")
        
        # Устанавливаем СТРОГИЙ минимальный порог для принятия совпадения
        # Увеличен с 0.3 до 0.7 для предотвращения ошибочного связывания
        min_threshold = float(self.env['ir.config_parameter'].sudo().get_param(
            'amanat.swift_fuzzy_matching_threshold', '0.7'
        ))
        
        if best_score >= min_threshold and best_match:
            _logger.info(f"[SWIFT AUTO FUZZY] ✅ Лучшее совпадение найдено: заявка {best_match.id}, скор: {best_score:.3f}")
            return best_match
        else:
            _logger.info(f"[SWIFT AUTO FUZZY] ❌ Совпадения не найдены. Лучший скор: {best_score:.3f}, минимальный порог: {min_threshold}")
            return None

    def _find_best_matching_zayavka_with_validation(self, validation_func):
        """Улучшенный алгоритм поиска с учетом валидации заявок и нечеткого сопоставления"""
        import re
        from difflib import SequenceMatcher
        
        if not self.payer_subagent:
            return None
        
        def _normalize_string(s):
            """Расширенная нормализация строки для сравнения"""
            if not s:
                return ""
            # Убираем знаки препинания и специальные символы
            normalized = re.sub(r'[^\w\s]', '', s.lower()).strip()
            # Убираем лишние пробелы
            normalized = re.sub(r'\s+', ' ', normalized)
            # Убираем распространенные сокращения и слова-паразиты
            stop_words = ['ltd', 'llc', 'inc', 'corp', 'company', 'co', 'limited', 'ооо', 'зао', 'оао', 'ип']
            words = normalized.split()
            words = [word for word in words if word not in stop_words]
            return ' '.join(words)
        
        def _calculate_similarity(str1, str2):
            """Вычисляем сходство между двумя строками (0.0 - 1.0)"""
            return SequenceMatcher(None, str1, str2).ratio()
        
        def _calculate_fuzzy_similarity(str1, str2):
            """Расширенная функция нечеткого сопоставления"""
            if not str1 or not str2:
                return 0.0
            
            # 1. Обычное сходство строк
            basic_similarity = _calculate_similarity(str1, str2)
            
            # 2. Сходство по токенам (слова)
            tokens1 = set(str1.split())
            tokens2 = set(str2.split())
            
            if not tokens1 or not tokens2:
                return basic_similarity
            
            # Пересечение токенов
            common_tokens = tokens1 & tokens2
            all_tokens = tokens1 | tokens2
            token_similarity = len(common_tokens) / len(all_tokens) if all_tokens else 0.0
            
            # 3. Частичное совпадение токенов (подстроки)
            partial_matches = 0
            total_comparisons = 0
            
            for token1 in tokens1:
                for token2 in tokens2:
                    total_comparisons += 1
                    # Если один токен содержится в другом
                    if token1 in token2 or token2 in token1:
                        partial_matches += 1
                    # Или если токены очень похожи
                    elif len(token1) >= 3 and len(token2) >= 3:
                        token_sim = _calculate_similarity(token1, token2)
                        if token_sim >= 0.8:
                            partial_matches += 0.8
            
            partial_similarity = partial_matches / total_comparisons if total_comparisons > 0 else 0.0
            
            # 4. Итоговый скор - взвешенная сумма всех метрик
            final_score = (basic_similarity * 0.4) + (token_similarity * 0.4) + (partial_similarity * 0.2)
            
            return min(final_score, 1.0)  # Ограничиваем максимум единицей
        
        def _check_token_overlap(tokens1, tokens2):
            """Проверяем пересечение токенов между двумя наборами"""
            if not tokens1 or not tokens2:
                return 0.0
            
            common_tokens = set(tokens1) & set(tokens2)
            total_tokens = len(set(tokens1) | set(tokens2))
            
            if total_tokens == 0:
                return 0.0
            
            return len(common_tokens) / total_tokens
        
        # Нормализуем исходное имя плательщика
        normalized_payer = _normalize_string(self.payer_subagent)
        payer_tokens = set(normalized_payer.split())
        
        _logger.info(f"[SWIFT AUTO FUZZY VALID] Ищем ближайшее совпадение для плательщика: '{self.payer_subagent}' с валидацией")
        
        # Получаем все заявки с плательщиками субагентов
        all_zayavkas = self.env['amanat.zayavka'].search([
            ('subagent_payer_ids', '!=', False)
        ])
        
        best_match = None
        best_score = 0.0
        valid_candidates = []
        
        for zayavka in all_zayavkas:
            # Сначала проверяем, проходит ли заявка валидацию
            if not validation_func(zayavka):
                continue
                
            for payer in zayavka.subagent_payer_ids:
                if not payer.name:
                    continue
                
                normalized_candidate = _normalize_string(payer.name)
                candidate_tokens = set(normalized_candidate.split())
                
                # Используем улучшенную функцию нечеткого сопоставления
                final_score = _calculate_fuzzy_similarity(normalized_payer, normalized_candidate)
                
                # Дополнительно рассчитываем отдельные метрики для логирования
                string_similarity = _calculate_similarity(normalized_payer, normalized_candidate)
                token_overlap = _check_token_overlap(payer_tokens, candidate_tokens)
                
                valid_candidates.append({
                    'zayavka': zayavka,
                    'payer_name': payer.name,
                    'final_score': final_score,
                    'string_similarity': string_similarity,
                    'token_overlap': token_overlap
                })
                
                if final_score > best_score:
                    best_score = final_score
                    best_match = zayavka
        
        # Логирование результатов
        _logger.info(f"[SWIFT AUTO FUZZY VALID] Найдено валидных кандидатов: {len(valid_candidates)}")
        
        # Сортируем кандидатов по скору для логирования топ-3
        top_candidates = sorted(valid_candidates, key=lambda x: x['final_score'], reverse=True)[:3]
        
        for i, candidate in enumerate(top_candidates, 1):
            _logger.info(f"[SWIFT AUTO FUZZY VALID] Топ-{i}: Заявка {candidate['zayavka'].id}, "
                        f"плательщик '{candidate['payer_name']}', "
                        f"скор: {candidate['final_score']:.3f}")
        
        # Устанавливаем СТРОГИЙ минимальный порог
        min_threshold = float(self.env['ir.config_parameter'].sudo().get_param(
            'amanat.swift_fuzzy_matching_threshold', '0.7'
        ))
        
        if best_score >= min_threshold and best_match:
            _logger.info(f"[SWIFT AUTO FUZZY VALID] ✅ Лучшее валидное совпадение найдено: заявка {best_match.id}, скор: {best_score:.3f}")
            return best_match
        else:
            _logger.info(f"[SWIFT AUTO FUZZY VALID] ❌ Валидные совпадения не найдены. Лучший скор: {best_score:.3f}, порог: {min_threshold}")
            return None

    def _upload_document_to_zayavka(self, zayavka):
        """Загрузка SWIFT документа в заявку"""
        _logger.info(f"[SWIFT AUTO] Начинаем загрузку файла в заявку {zayavka.id}")
        _logger.info(f"[SWIFT AUTO] Информация о заявке: ID={zayavka.id}, валюта={zayavka.currency}, сумма={zayavka.amount}")
        _logger.info(f"[SWIFT AUTO] Текущие SWIFT файлы в заявке: {len(zayavka.swift_attachments)} файлов")
        
        try:
            # Создаем attachment
            attachment_vals = {
                'name': self.swift_file_name or f'SWIFT_{self.swift_code or "document"}_{self.id}.pdf',
                'type': 'binary',
                'datas': self.swift_file,
                'res_model': 'amanat.zayavka',
                'res_id': zayavka.id,
                'mimetype': 'application/pdf',
                'description': f'SWIFT документ от {self.create_date}, плательщик: {self.payer_subagent}'
            }
            
            _logger.info(f"[SWIFT AUTO] Создаем attachment с данными: {attachment_vals}")
            attachment = self.env['ir.attachment'].create(attachment_vals)
            _logger.info(f"[SWIFT AUTO] ✅ Attachment создан успешно, ID: {attachment.id}")
            
            # Добавляем attachment к заявке в поле swift_attachments (вкладка SWIFT)
            _logger.info(f"[SWIFT AUTO] Добавляем attachment {attachment.id} к заявке {zayavka.id} в поле swift_attachments")
            zayavka.write({
                'swift_attachments': [(4, attachment.id)]  # (4, id) - добавить связь
            })
            _logger.info(f"[SWIFT AUTO] ✅ Attachment добавлен к заявке. Количество SWIFT файлов теперь: {len(zayavka.swift_attachments)}")
            
            _logger.info(f"[SWIFT AUTO] ✅ Документ успешно загружен в заявку {zayavka.id}, attachment ID: {attachment.id}")
            return attachment
            
        except Exception as e:
            _logger.error(f"[SWIFT AUTO] Ошибка при загрузке документа в заявку: {str(e)}")
            return None



    @api.depends('payer_subagent', 'currency', 'amount')
    def _compute_zayavka_id(self):
        """Находим связанную заявку с учетом всех проверок: плательщик субагента, валюта, сумма, отсутствие SWIFT файлов"""
        for record in self:
            if record.payer_subagent and not record.zayavka_id:
                # Используем нашу строгую логику поиска с проверками
                zayavka = record._find_matching_zayavka()
                record.zayavka_id = zayavka if zayavka else False
                
                if zayavka:
                    _logger.info(f"[SWIFT AUTO COMPUTE] Заявка {zayavka.id} автоматически связана с SWIFT документом {record.id} через compute метод")
                else:
                    _logger.info(f"[SWIFT AUTO COMPUTE] Подходящая заявка не найдена для SWIFT документа {record.id} (плательщик: {record.payer_subagent}, валюта: {record.currency}, сумма: {record.amount})")
            elif not record.payer_subagent:
                record.zayavka_id = False

    def action_reprocess_document(self):
        """Кнопка для повторной обработки документа"""
        self.ensure_one()
        try:
            self.processing_status = 'pending'
            self.processing_notes = 'Повторная обработка запущена вручную'
            self._process_swift_document_automation()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Документ успешно переобработан',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Ошибка при переобработке: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_test_fuzzy_matching(self):
        """Тестирование алгоритма нечеткого поиска"""
        self.ensure_one()
        
        if not self.payer_subagent:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Не указан плательщик субагента для тестирования',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        try:
            # Запускаем тестирование алгоритма - используем основной метод поиска
            best_match = self._find_matching_zayavka()
            
            if best_match:
                # Получаем информацию о найденной заявке
                try:
                    payer_names = [p.name for p in best_match.subagent_payer_ids if p.name]
                except Exception as e:
                    _logger.warning(f"[SWIFT AUTO FUZZY] Ошибка получения плательщиков субагентов: {e}")
                    payer_names = ["Не удалось получить список плательщиков"]
                
                swift_curr_norm = self._normalize_currency(self.currency)
                zayavka_curr_norm = self._normalize_currency(best_match.currency)
                
                message = f"✅ Найдена заявка {best_match.id} ({best_match.zayavka_num})\n"
                message += f"Плательщики: {', '.join(payer_names[:3])}{'...' if len(payer_names) > 3 else ''}\n"
                message += f"Валюта: {best_match.currency} (норм: {zayavka_curr_norm}) vs SWIFT: {self.currency} (норм: {swift_curr_norm})\n"
                message += f"Сумма: {best_match.amount} vs SWIFT: {self.amount}\n"
                message += f"Статус: {best_match.status}\n"
                message += f"SWIFT файлов: {len(best_match.swift_attachments) if best_match.swift_attachments else 0}"
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Результат поиска заявки (ИСПРАВЛЕННЫЙ алгоритм)',
                        'message': message,
                        'type': 'success',
                        'sticky': True,
                    }
                }
            else:
                swift_curr_norm = self._normalize_currency(self.currency)
                message = '❌ Подходящая заявка не найдена\n'
                message += f'Плательщик: "{self.payer_subagent}"\n'
                message += f'Валюта: {self.currency} (норм: {swift_curr_norm})\n'
                message += f'Сумма: {self.amount}\n'
                message += 'Проверьте логи для подробной диагностики.'
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Результат поиска заявки',
                        'message': message,
                        'type': 'warning',
                        'sticky': True,
                    }
                }
        except Exception as e:
            _logger.error(f"Ошибка при тестировании нечеткого поиска: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Ошибка при тестировании: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_test_strict_matching(self):
        """Тестирование строгого алгоритма поиска заявок"""
        self.ensure_one()
        
        _logger.info(f"[SWIFT STRICT TEST] 🧪 Тестируем строгий алгоритм для SWIFT документа {self.id}")
        _logger.info(f"[SWIFT STRICT TEST] Данные: плательщик='{self.payer_subagent}', валюта={self.currency}, сумма={self.amount}, номер заявки='{self.application_sequence}'")
        
        # Сбрасываем текущую связь для чистого теста
        old_zayavka_id = self.zayavka_id.id if self.zayavka_id else None
        self.zayavka_id = False
        
        try:
            # Запускаем строгий поиск
            found_zayavka = self._find_matching_zayavka()
            
            if found_zayavka:
                message = f"✅ СТРОГИЙ АЛГОРИТМ: Найдена заявка {found_zayavka.id}\n"
                message += f"Номер заявки: {found_zayavka.zayavka_num or 'Не указан'}\n"
                message += f"Валюта: {found_zayavka.currency}\n"
                message += f"Сумма: {found_zayavka.amount}\n"
                message += f"SWIFT файлов: {len(found_zayavka.swift_attachments) if found_zayavka.swift_attachments else 0}\n"
                message += f"Статус: {found_zayavka.status}"
                
                # Устанавливаем найденную заявку
                self.zayavka_id = found_zayavka.id
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Тест строгого алгоритма',
                        'message': message,
                        'type': 'success',
                        'sticky': True,
                    }
                }
            else:
                message = "❌ СТРОГИЙ АЛГОРИТМ: Подходящая заявка НЕ найдена\n"
                message += f"Плательщик: '{self.payer_subagent}'\n"
                message += f"Валюта: {self.currency}\n"
                message += f"Сумма: {self.amount}\n"
                message += f"Номер заявки: '{self.application_sequence}'\n"
                message += "✅ SWIFT документ НЕ будет привязан (правильное поведение)"
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Тест строгого алгоритма',
                        'message': message,
                        'type': 'warning',
                        'sticky': True,
                    }
                }
                
        except Exception as e:
            _logger.error(f"[SWIFT STRICT TEST] Ошибка при тестировании: {str(e)}")
            
            # Восстанавливаем старую связь при ошибке
            if old_zayavka_id:
                self.zayavka_id = old_zayavka_id
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Ошибка при тестировании: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }
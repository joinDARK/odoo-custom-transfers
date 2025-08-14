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

    def _find_matching_zayavka(self):
        """Поиск существующей заявки по плательщику субагента с дополнительными проверками валюты, суммы и отсутствия файлов"""
        if not self.payer_subagent:
            _logger.error(f"[SWIFT AUTO] ❌ Плательщик субагента не указан в SWIFT документе {self.id}")
            return None
        
        # Функция для проверки дополнительных условий
        def _validate_zayavka_conditions(zayavka):
            """Проверяет совпадение валюты, суммы и отсутствие прикрепленных SWIFT файлов"""
            if not zayavka:
                return False
            
            # СТРОГАЯ проверка валюты - оба поля должны быть заполнены и совпадать
            if not self.currency:
                _logger.info(f"[SWIFT AUTO] Заявка {zayavka.id} отклонена: валюта не указана в SWIFT документе")
                return False
            
            if not zayavka.currency:
                _logger.info(f"[SWIFT AUTO] Заявка {zayavka.id} отклонена: валюта не указана в заявке")
                return False
            
            if self.currency.lower() != zayavka.currency.lower():
                _logger.info(f"[SWIFT AUTO] Заявка {zayavka.id} отклонена: валюта не совпадает (SWIFT: {self.currency}, Заявка: {zayavka.currency})")
                return False
            
            # СТРОГАЯ проверка суммы - оба поля должны быть заполнены и совпадать
            if not self.amount:
                _logger.info(f"[SWIFT AUTO] Заявка {zayavka.id} отклонена: сумма не указана в SWIFT документе")
                return False
            
            if not zayavka.amount:
                _logger.info(f"[SWIFT AUTO] Заявка {zayavka.id} отклонена: сумма не указана в заявке")
                return False
            
            if abs(self.amount - zayavka.amount) > 0.01:  # допускаем погрешность в 0.01
                _logger.info(f"[SWIFT AUTO] Заявка {zayavka.id} отклонена: сумма не совпадает (SWIFT: {self.amount}, Заявка: {zayavka.amount})")
                return False
            
            # Проверка отсутствия прикрепленных SWIFT файлов
            if zayavka.swift_attachments:
                _logger.info(f"[SWIFT AUTO] Заявка {zayavka.id} отклонена: уже есть прикрепленные SWIFT документы ({len(zayavka.swift_attachments)} файлов)")
                return False
            
            _logger.info(f"[SWIFT AUTO] Заявка {zayavka.id} прошла все проверки: валюта={zayavka.currency}, сумма={zayavka.amount}, SWIFT файлов=0")
            return True
        
        # Сначала пробуем старую логику для точных совпадений
        # 1. Точное совпадение с проверками
        zayavka = self.env['amanat.zayavka'].search([
            ('subagent_payer_ids.name', '=', self.payer_subagent)
        ], limit=1)
        
        if zayavka and _validate_zayavka_conditions(zayavka):
            _logger.info(f"[SWIFT AUTO] Найдена подходящая заявка по точному совпадению: {zayavka.id}")
            return zayavka
        elif zayavka:
            _logger.info(f"[SWIFT AUTO] Заявка {zayavka.id} найдена по точному совпадению, но не прошла дополнительные проверки")
        
        # 2. Нечеткий поиск ilike
        zayavka = self.env['amanat.zayavka'].search([
            ('subagent_payer_ids.name', 'ilike', self.payer_subagent)
        ], limit=1)
        
        if zayavka and _validate_zayavka_conditions(zayavka):
            _logger.info(f"[SWIFT AUTO] Найдена подходящая заявка по ilike поиску: {zayavka.id}")
            return zayavka
        elif zayavka:
            _logger.info(f"[SWIFT AUTO] Заявка {zayavka.id} найдена по ilike поиску, но не прошла дополнительные проверки")
        
        # 3. Улучшенный алгоритм нечеткого поиска - ищем среди кандидатов, которые проходят проверки
        best_zayavka = self._find_best_matching_zayavka_with_validation(_validate_zayavka_conditions)
        
        if best_zayavka:
            _logger.info(f"[SWIFT AUTO] Найдена подходящая заявка с улучшенным алгоритмом поиска: {best_zayavka.id}")
            return best_zayavka
        
        _logger.warning(f"[SWIFT AUTO] Подходящая заявка не найдена для плательщика субагента '{self.payer_subagent}' с учетом проверок валюты, суммы и отсутствия SWIFT файлов")
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
        
        # Устанавливаем минимальный порог для принятия совпадения
        # Можно вынести в системные параметры для гибкой настройки
        min_threshold = float(self.env['ir.config_parameter'].sudo().get_param(
            'amanat.swift_fuzzy_matching_threshold', '0.3'
        ))
        
        if best_score >= min_threshold and best_match:
            _logger.info(f"[SWIFT AUTO FUZZY] ✅ Лучшее совпадение найдено: заявка {best_match.id}, скор: {best_score:.3f}")
            return best_match
        else:
            _logger.info(f"[SWIFT AUTO FUZZY] ❌ Совпадения не найдены. Лучший скор: {best_score:.3f}, минимальный порог: {min_threshold}")
            return None

    def _find_best_matching_zayavka_with_validation(self, validation_func):
        """Улучшенный алгоритм поиска с учетом валидации заявок"""
        import re
        from difflib import SequenceMatcher
        
        if not self.payer_subagent:
            return None
        
        def _normalize_string(s):
            """Нормализация строки для сравнения"""
            if not s:
                return ""
            normalized = re.sub(r'[^\w\s]', '', s.lower()).strip()
            normalized = re.sub(r'\s+', ' ', normalized)
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
                
                # Рассчитываем метрики сходства
                string_similarity = _calculate_similarity(normalized_payer, normalized_candidate)
                token_overlap = _check_token_overlap(payer_tokens, candidate_tokens)
                
                # Итоговый скор
                final_score = (string_similarity * 0.6) + (token_overlap * 0.4)
                
                valid_candidates.append({
                    'zayavka': zayavka,
                    'payer_name': payer.name,
                    'final_score': final_score
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
        
        # Устанавливаем минимальный порог
        min_threshold = float(self.env['ir.config_parameter'].sudo().get_param(
            'amanat.swift_fuzzy_matching_threshold', '0.3'
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
                payer_names = [p.name for p in best_match.subagent_payer_ids if p.name]
                message = f"Найдена заявка {best_match.id}.\nПлательщики: {', '.join(payer_names)}\nВалюта: {best_match.currency}\nСумма: {best_match.amount}"
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Результат нечеткого поиска',
                        'message': message,
                        'type': 'success',
                        'sticky': True,
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Результат нечеткого поиска',
                        'message': f'Подходящая заявка не найдена для плательщика "{self.payer_subagent}"',
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
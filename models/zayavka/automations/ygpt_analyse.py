import requests
import logging
import base64
import json
import os
from dotenv import load_dotenv  # отключено: используем конфиг Odoo/ENV напрямую
from odoo import models

_logger = logging.getLogger(__name__)

# Загружаем переменные окружения из .env (если файл присутствует)
load_dotenv()

URL = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'
OCR_URL = 'https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText'
PROMPT = """
Проанализируй документ и выдай мне информацию

сумма
валюта
кто платит
кому платят
страна получателя
свифт код
назначение платежа
номер заявки (application number)
дата подачи заявки
номер контракта от <дата_если_есть>
адрес получателя (бенефициара)
наименование банка получателя (бенефициара)
адрес банка получателя
iban/acc

После этого сопоставь полученные данные и выдай мне информацию в формате json

сумма - amount
валюта - currency
кто платит - subagent_payer_ids
кому платят - exporter_importer_name
страна получателя - country_id
свифт код - bank_swift
назначение платежа - payment_purpose
номер заявки - application_sequence
дата подачи заявки - payment_date
номер контракта от <дата_если_есть> - contract_number
адрес получателя (бенефициара) - beneficiary_address
наименование банка получателя (бенефициара) - beneficiary_bank_name
адрес банка получателя - bank_address
iban/acc - iban_accc

выдаем только первоначальную валюту без эквивалента
если не указано, то оставляй пустоту
"""
UPDATE_FIELDS = [
    'amount',
    'currency', 
    'subagent_payer_ids',
    'subagent_ids',
    'exporter_importer_name',
    'country_id',
    'bank_swift',
    'payment_purpose',
    'application_sequence',
    'payment_date',
    'contract_number',
    'beneficiary_address',
    'beneficiary_bank_name',
    'bank_address',
    'iban_accc',
    'deal_type',
    'instruction_number',
    'rate_field',
    'agent_contract_date',
    'instruction_signed_date',
    'client_id',
    'agent_id',
    'hand_reward_percent',
    'rate_fixation_date'
]
FIELD_MAPPING = {
    'amount': 'amount',  # Сумма заявки (строка 965)
    'currency': 'currency',  # Валюта (строка 895)
    'subagent_payer_ids': None,  # Это Many2many поле к amanat.payer, обработаем отдельно
    'exporter_importer_name': 'exporter_importer_name',  # Наименование покупателя/продавца (строка 82)
    'country_id': None,  # Это Many2one поле, обработаем отдельно 
    'agent_id': None,  # Это Many2one поле, обработаем отдельно
    'bank_swift': 'bank_swift',  # SWIFT код банка (строка 84)
    'payment_purpose': 'payment_purpose',  # Назначение платежа (строка 1214)
    'application_sequence': 'application_sequence',  # Порядковый номер заявления (строка 1228)
    'payment_date': 'payment_date',  # Дата платежа - нужно определить правильное поле
    'contract_number': 'contract_number',  # Номер контракта
    'beneficiary_address': 'beneficiary_address',  # Адрес получателя (бенефициара)
    'beneficiary_bank_name': 'beneficiary_bank_name',  # Наименование банка получателя
    'bank_address': 'bank_address',  # Адрес банка получателя
    'iban_accc': 'iban_accc',  # IBAN/ACC
    'deal_type': 'deal_type',  # Тип сделки
    'instruction_number': 'instruction_number', # Номер поручения
    'rate_field': 'rate_field', # Курс
    'agent_contract_date': 'agent_contract_date',  # Дата контракта агента
    'instruction_signed_date': 'instruction_signed_date',  # Дата подписания поручения
    'client_id': None,  # Это Many2one поле, обработаем отдельно
    'hand_reward_percent': 'hand_reward_percent', # % Вознаграждения
    'rate_fixation_date': 'rate_fixation_date', # Дата фиксации курса
}

def _get_yandex_gpt_config(env, prompt_type=None):
    """Возвращает конфиг YandexGPT из системных параметров с фолбэком к ENV."""
    try:
        icp = env['ir.config_parameter'].sudo()
        api_key = icp.get_param('amanat.ygpt.api_key') or os.getenv('YANDEX_GPT_API_KEY', '')
        folder_id = icp.get_param('amanat.ygpt.folder_id') or os.getenv('YANDEX_GPT_FOLDER_ID', '')
        match prompt_type:
            case 'zayavka':
                prompt = icp.get_param('amanat.ygpt.prompt_for_zayavka_analyse') or PROMPT
            case 'sber_screen':
                prompt = icp.get_param('amanat.ygpt.prompt_for_sber_screen_analyse') or PROMPT
            case 'assignment':
                prompt = icp.get_param('amanat.ygpt.prompt_for_assignment_analyse') or PROMPT
            case _:
                prompt = PROMPT

        _logger.info(f"[_get_yandex_gpt_config] prompt: {prompt}")
        return {
            'api_key': api_key or '',
            'folder_id': folder_id or '',
            'prompt': prompt or PROMPT,
        }
    except Exception as e:
        _logger.error(f"[_get_yandex_gpt_config] Ошибка получения конфигурации: {e}")
        return {
            'api_key': os.getenv('YANDEX_GPT_API_KEY', ''),
            'folder_id': os.getenv('YANDEX_GPT_FOLDER_ID', ''),
            'prompt': PROMPT,
        }

def _make_headers(api_key, folder_id):
    return {
        "Authorization": f"Api-Key {api_key}",
        "Content-Type": "application/json",
        "X-Folder-Id": folder_id,
    }

class ZayavkaYandexGPTAnalyse(models.Model):
    _inherit = 'amanat.zayavka'

    # Внешние методы
    def _notify_user_simple(self, title, message, warning=False, sticky=False):
        """Отправляет пользователю простое UI-уведомление через bus.bus (не почта)."""
        try:
            partner = self.env.user.partner_id
            payload = {
                'title': str(title) if title is not None else 'Уведомление',
                'message': str(message) if message is not None else '',
                'sticky': bool(sticky),
                'warning': bool(warning),
            }
            # Для Odoo 18 требуется указывать тип сообщения вторым аргументом
            self.env['bus.bus']._sendone(partner, 'simple_notification', payload)
        except Exception as notify_err:
            _logger.warning(f"[_notify_user_simple] Не удалось отправить уведомление пользователю: {notify_err}")

    def analyze_document_with_yandex_gpt(self, content, prompt_type="zayavka"):
        try:

            # Подготавливаем содержимое: поддержка как JSON/словаря, так и обычного текста
            prepared_text = None
            label = "Документ для анализа"

            try:
                # Если передан dict/list — сериализуем в JSON
                if isinstance(content, (dict, list)):
                    prepared_text = json.dumps(content, ensure_ascii=False)
                else:
                    text = str(content)
                    stripped = text.strip()
                    # Эвристика: если похоже на JSON, оставляем как есть и считаем документом
                    if (stripped.startswith('{') and stripped.endswith('}')) or (stripped.startswith('[') and stripped.endswith(']')):
                        prepared_text = text
                    else:
                        # Иначе это свободный текст
                        label = "Текст для анализа"
                        prepared_text = text
            except Exception:
                # На всякий случай используем строковое представление
                label = "Текст для анализа"
                prepared_text = str(content)

            # Формируем сообщение для GPT
            user_message = f"{label}:\n{prepared_text}"

            cfg = _get_yandex_gpt_config(self.env, prompt_type)
            if not cfg['api_key'] or not cfg['folder_id']:
                self._notify_user_simple(
                    title="YandexGPT",
                    message="Не настроены API ключ и/или Folder ID в Настройках (YandexGPT)",
                    warning=True,
                    sticky=True,
                )
                _logger.error("[analyze_document_with_yandex_gpt] Не настроены ygpt_api_key/ygpt_folder_id")
                return None

            data = {
                "modelUri": f"gpt://{cfg['folder_id']}/yandexgpt/latest",
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.3,
                    "maxTokens": "2000"
                },
                "messages": [
                    {"role": "system", "text": cfg['prompt']},
                    {"role": "user", "text": user_message}
                ]
            }

            headers = _make_headers(cfg['api_key'], cfg['folder_id'])
            response = requests.post(URL, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                # Извлекаем текст ответа
                if 'result' in result and 'alternatives' in result['result']:
                    alternatives = result['result']['alternatives']
                    if alternatives and len(alternatives) > 0:
                        gpt_response = alternatives[0]['message']['text']
                        
                        # Выводим ответ нейронки в логер
                        _logger.info(f"[analyze_document_with_yandex_gpt] YandexGPT АНАЛИЗ СОДЕРЖИМОГО для заявки {self.zayavka_id}:\n{gpt_response}")
                        
                        # Парсим ответ и обновляем поля заявки
                        self._update_fields_from_gpt_response(gpt_response)
                        
                        return gpt_response
                else:
                    _logger.warning(f"[analyze_document_with_yandex_gpt] Неожиданная структура ответа от YandexGPT: {result}")
            else:
                _logger.error(f"[analyze_document_with_yandex_gpt] Ошибка API YandexGPT: {response.status_code} - {response.text}")
                
        except Exception as e:
            _logger.error(f"[analyze_document_with_yandex_gpt] Ошибка при анализе документа с YandexGPT: {str(e)}")
            
        return None
    
    def analyze_screen_sber_images_with_yandex_gpt(self):
        """
        Анализирует изображения из screen_sber_attachments с помощью Yandex Vision OCR API
        """
        try:
            # Получаем изображения в base64
            images_data = self._get_screen_sber_images_base64()
            
            if not images_data:
                _logger.warning("[analyze_screen_sber_images_with_yandex_gpt] Нет изображений для анализа в screen_sber_attachments")
                return None
            
            # Анализируем каждое изображение
            all_recognized_text = []
            
            for i, image_info in enumerate(images_data, 1):
                _logger.info(f"[analyze_screen_sber_images_with_yandex_gpt] Анализируем изображение {i}/{len(images_data)}: {image_info['name']}")
                
                recognized_text = self._send_image_to_yandex_gpt_vision(image_info)
                if recognized_text:
                    all_recognized_text.append({
                        'image_name': image_info['name'],
                        'recognized_text': recognized_text
                    })
                    _logger.info(f"[analyze_screen_sber_images_with_yandex_gpt] Распознан текст из {image_info['name']}:\n{recognized_text}")
                    
                    # Отправляем распознанный текст в YandexGPT для анализа
                    _logger.info(f"[analyze_screen_sber_images_with_yandex_gpt] Отправляем текст из {image_info['name']} в YandexGPT для анализа...")
                    self.analyze_document_with_yandex_gpt(recognized_text, "sber_screen")
                    
                else:
                    _logger.warning(f"[analyze_screen_sber_images_with_yandex_gpt] Не удалось распознать текст из {image_info['name']}")
            
            # Выводим общий результат
            if all_recognized_text:
                _logger.info(f"[analyze_screen_sber_images_with_yandex_gpt] Успешно обработано {len(all_recognized_text)} изображений")
                _logger.info("[analyze_screen_sber_images_with_yandex_gpt] Все изображения прошли полный цикл: OCR -> YandexGPT -> Обновление полей заявки")
                for result in all_recognized_text:
                    _logger.info(f"[analyze_screen_sber_images_with_yandex_gpt] {result['image_name']}:\n{result['recognized_text']}\n" + "="*50)
            else:
                _logger.warning("[analyze_screen_sber_images_with_yandex_gpt] Не удалось распознать текст ни из одного изображения")
                
            return all_recognized_text
            
        except Exception as e:
            _logger.error(f"[analyze_screen_sber_images_with_yandex_gpt] Ошибка при анализе изображений screen_sber с Yandex Vision OCR: {str(e)}")
            
        return None

    def zayavka_analyse_with_yandex_gpt(self):
        """
        Анализирует заявку с помощью YandexGPT
        """
        attachments = self.zayavka_attachments
        if not attachments:
            _logger.info(f"Заявка {self.id}: нет вложений в 'zayavka_attachments' — пропускаем анализ документов")
            return self
        attachment = attachments[0]
            
        # Пробуем анализировать каждое вложение
        analyzed_any = False
        text = None
        
        # Сначала пробуем как DOCX
        try:
            text = self.extract_text_from_docx_attachment(attachment)
            if text:
                _logger.info(f"Заявка {self.id}: извлечён текст из DOCX '{attachment.name}'")
        except Exception as e:
            _logger.debug(f"Заявка {self.id}: не удалось обработать '{attachment.name}' как DOCX: {str(e)}")
        
        # Если не DOCX, пробуем как Excel
        if not text:
            try:
                text = self.extract_text_from_excel_attachment(attachment)
                if text:
                    _logger.info(f"Заявка {self.id}: извлечён текст из Excel '{attachment.name}'")
            except Exception as e:
                _logger.debug(f"Заявка {self.id}: не удалось обработать '{attachment.name}' как Excel: {str(e)}")
        
        # Если не DOCX, пробуем как старый DOC
        if not text:
            try:
                text = self.extract_text_from_doc_attachment(attachment)
                if text:
                    _logger.info(f"Заявка {self.id}: извлечён текст из DOC '{attachment.name}'")
            except Exception as e:
                _logger.debug(f"Заявка {self.id}: не удалось обработать '{attachment.name}' как DOC: {str(e)}")

        # Если текст извлечён, отправляем на анализ
        if text:
            try:
                self.analyze_document_with_yandex_gpt(text)
                analyzed_any = True
                _logger.info(f"Заявка {self.id}: успешно проанализирован документ '{attachment.name}'")
            except Exception as e:
                _logger.error(f"Заявка {self.id}: ошибка анализа документа '{attachment.name}': {str(e)}")
        else:
            # Если не удалось извлечь текст из DOCX/Excel, пробуем PDF через OCR
            try:
                self.analyze_pdf_attachments_with_yandex_gpt(attachment)
                analyzed_any = True
                _logger.info(f"Заявка {self.id}: успешно проанализирован PDF '{attachment.name}' через OCR")
            except Exception as e:
                _logger.error(f"Заявка {self.id}: ошибка анализа PDF '{attachment.name}': {str(e)}")
    
        if not analyzed_any:
            _logger.info(f"Заявка {self.id}: подходящих документов (DOCX/DOC/Excel) с текстом не найдено — анализ пропущен")

    def analyze_assignment_with_yandex_gpt(self):
        attachments = self.assignment_attachments
        if not attachments:
            _logger.info(f"Заявка {self.id}: нет вложений в 'assignment_attachments' — пропускаем анализ документов")
            return self
        else:
            attachment = attachments[0]
            analyzed_any = False
            
            text = None
            
            # Сначала пробуем как DOCX
            try:
                text = self.extract_text_from_docx_attachment(attachment)
                if text:
                    _logger.info(f"Заявка {self.id}: извлечён текст из DOCX '{attachment.name}'")
            except Exception as e:
                _logger.debug(f"Заявка {self.id}: не удалось обработать '{attachment.name}' как DOCX: {str(e)}")
            
            # Если не DOCX, пробуем как старый DOC
            if not text:
                try:
                    text = self.extract_text_from_doc_attachment(attachment)
                    if text:
                        _logger.info(f"Заявка {self.id}: извлечён текст из DOC '{attachment.name}'")
                except Exception as e:
                    _logger.debug(f"Заявка {self.id}: не удалось обработать '{attachment.name}' как DOC: {str(e)}")
            
            # Если не DOCX и не DOC, пробуем как Excel
            if not text:
                try:
                    text = self.extract_text_from_excel_attachment(attachment)
                    if text:
                        _logger.info(f"Заявка {self.id}: извлечён текст из Excel '{attachment.name}'")
                except Exception as e:
                    _logger.debug(f"Заявка {self.id}: не удалось обработать '{attachment.name}' как Excel: {str(e)}")

            # Если текст извлечён, отправляем на анализ
            if text:
                try:
                    self.analyze_document_with_yandex_gpt(text, "assignment")
                    analyzed_any = True
                    _logger.info(f"Заявка {self.id}: успешно проанализирован документ '{attachment.name}'")
                except Exception as e:
                    _logger.error(f"Заявка {self.id}: ошибка анализа документа '{attachment.name}': {str(e)}")
            else:
                # Если не удалось извлечь текст из DOCX/Excel, пробуем PDF через OCR
                try:
                    self.analyze_pdf_attachments_with_yandex_gpt(attachment, "assignment")
                    analyzed_any = True
                    _logger.info(f"Заявка {self.id}: успешно проанализирован PDF '{attachment.name}' через OCR")
                except Exception as e:
                    _logger.error(f"Заявка {self.id}: ошибка анализа PDF '{attachment.name}': {str(e)}")

            if not analyzed_any:
                _logger.info(f"Заявка {self.id}: подходящих документов (DOCX/DOC/Excel) с текстом не найдено — анализ пропущен")

    def analyze_pdf_attachments_with_yandex_gpt(self, attachment, prompt_type="zayavka"):
        """
        Анализирует PDF-файлы из zayavka_attachments с помощью Yandex Vision OCR API и выводит распознанный текст.
        Дополнительно отправляет распознанный текст в YandexGPT для структурного анализа.
        """
        try:
            pdfs_data = self._get_pdf_attachments_base64(attachment)

            if not pdfs_data:
                _logger.warning("[analyze_pdf_attachments_with_yandex_gpt] Нет PDF-файлов для анализа в zayavka_attachments")
                return None

            all_results = []

            for i, pdf_info in enumerate(pdfs_data, 1):
                _logger.info(f"[analyze_pdf_attachments_with_yandex_gpt] Анализируем PDF {i}/{len(pdfs_data)}: {pdf_info['name']}")

                recognized_text = self._send_image_to_yandex_gpt_vision(pdf_info)
                if recognized_text:
                    all_results.append({
                        'pdf_name': pdf_info['name'],
                        'recognized_text': recognized_text,
                    })

                    # Отправляем распознанный текст в YandexGPT для структурного анализа
                    try:
                        self.analyze_document_with_yandex_gpt(recognized_text, prompt_type)
                    except Exception as gpt_err:
                        _logger.warning(f"[analyze_pdf_attachments_with_yandex_gpt] Не удалось отправить распознанный PDF-текст в YandexGPT: {gpt_err}")
                else:
                    _logger.warning(f"[analyze_pdf_attachments_with_yandex_gpt] Не удалось распознать текст из {pdf_info['name']}")

            if all_results:
                _logger.info(f"[analyze_pdf_attachments_with_yandex_gpt] Успешно обработано PDF: {len(all_results)}")
                for result in all_results:
                    _logger.info(f"[analyze_pdf_attachments_with_yandex_gpt] {result['pdf_name']}:\n{result['recognized_text']}\n" + "="*50)
            else:
                _logger.warning("[analyze_pdf_attachments_with_yandex_gpt] Не удалось распознать текст ни из одного PDF")

            return all_results

        except Exception as e:
            _logger.error(f"[analyze_pdf_attachments_with_yandex_gpt] Ошибка при анализе PDF-файлов с Yandex Vision OCR: {str(e)}")
            return None

    # Внутренние методы
    def _update_fields_from_gpt_response(self, gpt_response):
        """
        Парсит ответ YandexGPT и обновляет поля заявки
        """
        try:
            import json
            import re
            
            # Извлекаем JSON из ответа (ищем блок между ``` или просто JSON)
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', gpt_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Если нет блока кода, пробуем найти JSON в тексте
                json_match = re.search(r'\{.*?\}', gpt_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    _logger.warning(f"[_update_fields_from_gpt_response] Не удалось найти JSON в ответе YandexGPT: {gpt_response}")
                    return

            # Парсим JSON
            try:
                parsed_data = json.loads(json_str)
            except json.JSONDecodeError as e:
                _logger.error(f"[_update_fields_from_gpt_response] Ошибка парсинга JSON из ответа YandexGPT: {e}\nJSON: {json_str}")
                return

            # Подготавливаем данные для обновления
            update_values = {}
            
            for json_key, model_field in FIELD_MAPPING.items():
                if json_key in parsed_data and parsed_data[json_key] and model_field:
                    value = parsed_data[json_key]
                    
                    # Специальная обработка для разных типов полей
                    try:
                        if model_field in ['amount', 'rate_field'] and value:
                            # Конвертируем в float, убираем пробелы и запятые
                            try:
                                clean_value = str(value).replace(',', '.').replace(' ', '')
                                update_values[model_field] = float(clean_value)
                            except (ValueError, TypeError):
                                _logger.warning(f"[_update_fields_from_gpt_response] Не удалось конвертировать число '{value}' для поля '{model_field}'")
                                continue

                        elif model_field == 'currency' and value:
                            # Для поля валюты нужно преобразовать в правильный код
                            currency_mapping = {
                                'CNY': 'cny',
                                'USD': 'usd', 
                                'EUR': 'euro',
                                'EURO': 'euro',
                                'RUB': 'rub',
                                'AED': 'aed',
                                'THB': 'thb',
                                'IDR': 'idr',
                                'INR': 'inr',
                                'USDT': 'usdt'
                            }
                            currency_code = currency_mapping.get(str(value).upper(), str(value).lower())
                            update_values[model_field] = currency_code

                        elif model_field == 'deal_type' and value:
                            value = str(value).lower()

                            deal_type_mapping = {
                                'импорт': 'import',
                                'экспорт': 'export',
                                'экспорт-возврат': 'export_return',
                                'импорт-возврат': 'import_return',
                            }
                            deal_type_code = deal_type_mapping.get(value, value)
                            update_values[model_field] = deal_type_code
                        
                        elif model_field in ['payment_date', 'agent_contract_date', 'instruction_signed_date', 'rate_fixation_date'] and value:
                            # Для полей дат нужно преобразовать строку в дату
                            try:
                                from datetime import datetime
                                # Пробуем разные форматы дат
                                date_formats = ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']
                                parsed_date = None
                                
                                date_str = str(value).strip()
                                for date_format in date_formats:
                                    try:
                                        parsed_date = datetime.strptime(date_str, date_format).date()
                                        break
                                    except ValueError:
                                        continue
                                
                                if parsed_date:
                                    update_values[model_field] = parsed_date
                                else:
                                    _logger.warning(f"[_update_fields_from_gpt_response] Не удалось распознать формат даты '{value}' для поля '{model_field}'")
                            except Exception as e:
                                _logger.error(f"[_update_fields_from_gpt_response] Ошибка при обработке даты '{value}' для поля '{model_field}': {str(e)}")
                        
                        else:
                            # Для текстовых полей сохраняем как строку
                            update_values[model_field] = str(value)
                            
                    except Exception as field_error:
                        _logger.error(f"[_update_fields_from_gpt_response] Ошибка при обработке поля '{model_field}' со значением '{value}': {str(field_error)}")
                        continue
            
            # Обработка специальных полей Many2one и Many2many
            special_warnings = self._handle_special_fields(parsed_data, update_values)

            # Обновляем поля, если есть что обновлять
            if update_values:
                # Фильтруем только существующие поля модели
                existing_fields = set(self._fields.keys())
                filtered_values = {k: v for k, v in update_values.items() if k in existing_fields}
                
                if filtered_values:
                    # Перед записью выбираем только те поля, которые пустые. Заполненные — не трогаем.
                    fields_to_write = {}
                    skipped_pairs = []  # [(rus_name, new_display)]

                    # Сопоставление model_field -> json_key для извлечения "значения из анализа"
                    model_to_json_key = {}
                    try:
                        model_to_json_key = {mf: jk for jk, mf in FIELD_MAPPING.items() if mf}
                        # Поля, у которых mf=None, но которые есть в модели и в parsed_data
                        model_to_json_key.setdefault('country_id', 'country_id')
                        model_to_json_key.setdefault('subagent_payer_ids', 'subagent_payer_ids')
                    except Exception:
                        model_to_json_key = {}

                    for field_name, new_value in filtered_values.items():
                        try:
                            field = self._fields.get(field_name)
                            current_value = getattr(self, field_name)

                            def _format_rel_value(val):
                                try:
                                    if not val:
                                        return "(пусто)"
                                    if hasattr(val, 'id') and hasattr(val, 'name'):
                                        return f"{val.id} | {val.name}"
                                    if hasattr(val, 'ids'):
                                        ids_list = list(val.ids)
                                        names = []
                                        for rec in val:
                                            name_val = getattr(rec, 'name', None)
                                            names.append(str(name_val) if name_val is not None else str(rec.id))
                                        return f"ids={ids_list}, names={names}"
                                except Exception:
                                    return str(val)
                                return str(val)

                            def _format_new_value(field_def, value):
                                try:
                                    if isinstance(value, list) and value and isinstance(value[0], tuple):
                                        ids_agg = []
                                        for cmd in value:
                                            if isinstance(cmd, tuple) and len(cmd) >= 3 and isinstance(cmd[2], (list, tuple)):
                                                ids_agg.extend(list(cmd[2]))
                                        return f"commands={value}, ids={ids_agg}" if ids_agg else f"commands={value}"
                                    return str(value)
                                except Exception:
                                    return str(value)

                            formatted_current = _format_rel_value(current_value) if field else str(current_value)
                            formatted_new = _format_new_value(field, new_value)

                            # Определение «пустоты» для поля (включая псевдопустые значения)
                            def _is_effectively_empty(val, field_name_inner):
                                try:
                                    _logger.info(f"[_is_effectively_empty] {field_name_inner} — {val}")
                                    if not val:
                                        return True
                                except Exception:
                                    return False

                            is_empty = _is_effectively_empty(current_value, field_name)

                            if is_empty:
                                _logger.info(f"[_update_fields_from_gpt_response] Поле '{field_name}' пустое. Будет установлено новое значение: '{formatted_new}'")
                                fields_to_write[field_name] = new_value
                            else:
                                # Человекочитаемая метка поля
                                field_label = self._get_field_label(field_name)
                                # Значение из анализа
                                analysis_value = None
                                try:
                                    json_key = model_to_json_key.get(field_name)
                                    if json_key and json_key in parsed_data:
                                        analysis_value = parsed_data.get(json_key)
                                except Exception:
                                    analysis_value = None

                                # Спец-обработка для subagent_ids (берём человеко-читаемое имя из команд, если есть)
                                if field_name == 'subagent_ids' and analysis_value in (None, ''):
                                    try:
                                        ids_from_cmds = []
                                        if isinstance(new_value, list):
                                            for cmd in new_value:
                                                if isinstance(cmd, tuple) and len(cmd) >= 3 and isinstance(cmd[2], (list, tuple)):
                                                    ids_from_cmds.extend(list(cmd[2]))
                                        if ids_from_cmds:
                                            names = self.env['amanat.contragent'].browse(ids_from_cmds).mapped('name')
                                            if names:
                                                analysis_value = ', '.join([str(n) for n in names if n])
                                    except Exception:
                                        pass

                                # Fallback на отформатированное новое значение
                                if analysis_value in (None, ''):
                                    analysis_value = formatted_new

                                skipped_pairs.append((field_label, str(analysis_value)))
                                _logger.warning(f"[_update_fields_from_gpt_response] Поле '{field_name}' уже заполнено (текущее='{formatted_current}'). Пропускаем обновление.")
                        except Exception as log_err:
                            _logger.warning(f"[_update_fields_from_gpt_response] Ошибка при подготовке обновления поля '{field_name}': {log_err}")

                    if fields_to_write:
                        self.write(fields_to_write)
                        updated_fields = ', '.join(f"{k}: {v}" for k, v in fields_to_write.items())
                        _logger.info(f"[_update_fields_from_gpt_response] Обновлены поля заявки {self.zayavka_id}: {updated_fields}")
                    else:
                        _logger.info("[_update_fields_from_gpt_response] Все целевые поля уже были заполнены. Запись не выполнялась.")

                    # Уведомление пользователю в читабельном виде
                    if skipped_pairs or special_warnings:
                        lines = []
                        if skipped_pairs:
                            lines.append("Уже заполнены следующие поля:")
                            for rus_name, new_disp in skipped_pairs:
                                lines.append(f"- {rus_name} — {new_disp}")
                        if special_warnings:
                            lines.append("Предупреждения:")
                            for w in special_warnings:
                                lines.append(f"- {w}")
                        msg = "\n".join(lines)
                        self._notify_user_simple(title="YandexGPT", message=msg, warning=True, sticky=True)
                else:
                    _logger.warning(f"[_update_fields_from_gpt_response] Ни одно из полей не найдено в модели: {list(update_values.keys())}")
                    self._notify_user_simple(title="YandexGPT", message="Ни одно из полученных полей не найдено в модели заявки.", warning=True, sticky=True)
            else:
                _logger.info("[_update_fields_from_gpt_response] Нет данных для обновления в ответе YandexGPT")
                
        except Exception as e:
            _logger.error(f"[_update_fields_from_gpt_response] Ошибка при обновлении полей из ответа YandexGPT: {str(e)}")

    def _get_field_label(self, field_name):
        """Возвращает человеко-читаемое название поля (field.string)."""
        try:
            field = self._fields.get(field_name)
            if field is not None:
                label = getattr(field, 'string', None)
                if label:
                    return str(label)
            # Резервный способ через fields_get
            try:
                info = self.fields_get([field_name]) or {}
                label = (info.get(field_name) or {}).get('string')
                if label:
                    return str(label)
            except Exception:
                pass
        except Exception:
            pass
        return str(field_name)

    def _handle_special_fields(self, parsed_data, update_values):
        """
        Обработка специальных полей Many2one и Many2many
        """
        warnings = []
        try:
            # Обработка country_id (Many2one к amanat.country)
            if 'country_id' in parsed_data and parsed_data['country_id']:
                country_name = str(parsed_data['country_id']).strip()
                
                # Используем улучшенный поиск страны
                country = self._advanced_country_search(country_name)
                
                if country:
                    update_values['country_id'] = country.id
                else:
                    label_country = self._get_field_label('country_id')
                    msg = f"{label_country}: '{country_name}' не найдена"
                    warnings.append(msg)
                    _logger.warning(f"[_handle_special_fields] {msg}")
            
            # Обработка subagent_payer_ids (Many2many к amanat.payer)
            if 'subagent_payer_ids' in parsed_data and parsed_data['subagent_payer_ids']:
                payer_name = str(parsed_data['subagent_payer_ids']).strip()
                
                # Используем улучшенный поиск плательщика
                payer = self._advanced_payer_search(payer_name)
                
                if payer:
                    # Очищаем поле subagent_payer_ids и добавляем нового плательщика
                    update_values['subagent_payer_ids'] = [(6, 0, [payer.id])]  # (6, 0, ids) - заменить все записи
                    # Теперь ищем связанного контрагента для subagent_ids
                    if payer.contragents_ids:
                        # Берем первого связанного контрагента
                        contragent = payer.contragents_ids[0]
                        # Очищаем поле subagent_ids и добавляем нового контрагента
                        update_values['subagent_ids'] = [(6, 0, [contragent.id])]  # (6, 0, ids) - заменить все записи
                    else:
                        label_subagent = self._get_field_label('subagent_ids')
                        msg = f"{label_subagent}: у плательщика '{payer.name}' нет связанных контрагентов"
                        warnings.append(msg)
                        _logger.warning(f"[_handle_special_fields] {msg}")
                        
                else:
                    label_payer = self._get_field_label('subagent_payer_ids')
                    label_subagent = self._get_field_label('subagent_ids')
                    msg = f"{label_payer}/{label_subagent}: плательщик '{payer_name}' не найден"
                    warnings.append(msg)
                    _logger.warning(f"[_handle_special_fields] {msg}")
                        
            if 'agent_id' in parsed_data and parsed_data['agent_id']:
                agent_name = str(parsed_data['agent_id']).strip()
                
                # Используем улучшенный поиск контрагента для агента
                agent = self._advanced_contragent_search(agent_name, context_type="агент")
                
                if agent:
                    update_values['agent_id'] = agent.id
                else:
                    _logger.warning(f"[_handle_special_fields] Не найден агент: {agent_name}")
            
            if 'client_id' in parsed_data and parsed_data['client_id']:
                client_name = str(parsed_data['client_id']).strip()
                
                # Используем улучшенный поиск контрагента для клиента
                client = self._advanced_contragent_search(client_name, context_type="клиент")
                
                if client:
                    update_values['client_id'] = client.id
                else:
                    _logger.warning(f"[_handle_special_fields] Не найден клиент: {client_name}")
            
        except Exception as e:
            _logger.error(f"[_handle_special_fields] Ошибка при обработке специальных полей: {str(e)}")                                   
        return warnings

    def _get_screen_sber_images_base64(self):
        """
        Получает изображения из поля screen_sber_attachments и кодирует их в base64
        """
        try:
            images_data = []
            
            if not self.screen_sber_attachments:
                _logger.info("[_get_screen_sber_images_base64] Нет изображений в поле screen_sber_attachments")
                return images_data
            
            # Поддерживаемые форматы изображений
            supported_formats = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']
            
            for attachment in self.screen_sber_attachments:
                try:
                    # Проверяем что это изображение
                    if not attachment.mimetype or not attachment.mimetype.startswith('image/'):
                        _logger.warning(f"[_get_screen_sber_images_base64] Файл {attachment.name} не является изображением (mimetype: {attachment.mimetype})")
                        continue
                    
                    # Получаем расширение файла
                    file_extension = attachment.name.lower().split('.')[-1] if '.' in attachment.name else ''
                    if file_extension not in supported_formats:
                        _logger.warning(f"[_get_screen_sber_images_base64] Неподдерживаемый формат изображения: {file_extension} для файла {attachment.name}")
                        continue
                    
                    # Получаем данные файла
                    image_data = base64.b64decode(attachment.datas)
                    
                    # Кодируем в base64 (повторно, так как attachment.datas уже в base64)
                    image_base64 = attachment.datas.decode('utf-8') if isinstance(attachment.datas, bytes) else attachment.datas
                    
                    images_data.append({
                        'name': attachment.name,
                        'mimetype': attachment.mimetype,
                        'size': len(image_data),
                        'base64': image_base64
                    })
                    
                    _logger.info(f"[_get_screen_sber_images_base64] Подготовлено изображение: {attachment.name} ({attachment.mimetype}, {len(image_data)} байт)")
                    
                except Exception as e:
                    _logger.error(f"[_get_screen_sber_images_base64] Ошибка при обработке изображения {attachment.name}: {str(e)}")
                    continue
            
            _logger.info(f"[_get_screen_sber_images_base64] Всего подготовлено изображений: {len(images_data)}")
            return images_data
            
        except Exception as e:
            _logger.error(f"[_get_screen_sber_images_base64] Ошибка при получении изображений screen_sber: {str(e)}")
            return []

    def _get_pdf_attachments_base64(self, attachment):
        """
        Собирает PDF из поля zayavka_attachments и возвращает список dict с полями name, mimetype, base64.
        """
        try:
            pdfs = []
            if not attachment:
                _logger.warning("[_get_pdf_attachments_base64] Нет вложения")
                return []
            try:
                is_pdf = (attachment.mimetype == 'application/pdf') or ((attachment.name or '').lower().endswith('.pdf'))
                if not is_pdf:
                    return []
                if not attachment.datas:
                    _logger.warning(f"[_get_pdf_attachments_base64] У вложения {attachment.name} отсутствуют данные")
                    return []
                base64_data = attachment.datas.decode('utf-8') if isinstance(attachment.datas, bytes) else attachment.datas
                pdfs.append({
                    'name': attachment.name,
                    'mimetype': 'application/pdf',
                    'base64': base64_data,
                })
            except Exception as one_err:
                _logger.error(f"[_get_pdf_attachments_base64] Ошибка при обработке вложения {getattr(attachment, 'name', 'unknown')}: {one_err}")

            _logger.info(f"[_get_pdf_attachments_base64] Всего подготовлено PDF: {len(pdfs)}")
            return pdfs
        except Exception as e:
            _logger.error(f"[_get_pdf_attachments_base64] Ошибка при получении PDF из zayavka_attachments: {str(e)}")
            return []

    def _send_image_to_yandex_gpt_vision(self, image_info):
        """
        Отправляет одно изображение в Yandex Vision OCR API для распознавания текста
        """
        try:
            cfg = _get_yandex_gpt_config(self.env)
            if not cfg['api_key'] or not cfg['folder_id']:
                _logger.error("[_send_image_to_yandex_gpt_vision] Не настроены ygpt_api_key/ygpt_folder_id")
                return None

            headers = _make_headers(cfg['api_key'], cfg['folder_id'])
            headers['x-data-logging-enabled'] = 'true'

            # Формируем данные для OCR API
            data = {
                "mimeType": image_info['mimetype'],
                "languageCodes": ["ru", "en"],
                "content": image_info['base64']
            }

            response = requests.post(url=OCR_URL, headers=headers, data=json.dumps(data), timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                
                # Извлекаем распознанный текст из ответа OCR API
                recognized_text = ""
                if 'result' in result and 'textAnnotation' in result['result']:
                    text_annotation = result['result']['textAnnotation']
                    if 'fullText' in text_annotation:
                        recognized_text = text_annotation['fullText']
                    elif 'blocks' in text_annotation:
                        # Если fullText нет, собираем текст из блоков
                        text_parts = []
                        for block in text_annotation['blocks']:
                            if 'lines' in block:
                                for line in block['lines']:
                                    if 'words' in line:
                                        line_words = []
                                        for word in line['words']:
                                            if 'text' in word:
                                                line_words.append(word['text'])
                                        if line_words:
                                            text_parts.append(' '.join(line_words))
                        recognized_text = '\n'.join(text_parts)
                
                return recognized_text.strip() if recognized_text else None
                
            else:
                _logger.error(f"[_send_image_to_yandex_gpt_vision] Ошибка API Yandex Vision OCR: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            _logger.error(f"[_send_image_to_yandex_gpt_vision] Ошибка при отправке изображения в Yandex Vision OCR: {str(e)}")
            return None
    
    def _normalize_payer_name(self, name):
        """
        Нормализует название плательщика для поиска.
        Убирает лишние символы, приводит к нижнему регистру, убирает лишние пробелы.
        """
        if not name:
            return ""
        
        import re
        
        # Приводим к строке и убираем лишние пробелы
        normalized = str(name).strip()
        
        # Убираем множественные пробелы и заменяем их одним
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Убираем специальные символы, оставляем только буквы, цифры, пробелы и основные знаки препинания
        normalized = re.sub(r'[^\w\s\-\.\,\(\)]', '', normalized, flags=re.UNICODE)
        
        # Приводим к нижнему регистру для поиска
        normalized = normalized.lower()
        
        return normalized
    
    def _advanced_payer_search(self, search_text):
        """
        Расширенный поиск плательщика с несколькими стратегиями:
        1. Точное совпадение (после нормализации)
        2. Поиск по началу строки
        3. Поиск по содержанию
        4. Поиск по ИНН (если текст похож на ИНН)
        """
        if not search_text:
            return None
            
        search_normalized = self._normalize_payer_name(search_text)
        if not search_normalized:
            return None
            
        _logger.info(f"[_advanced_payer_search] Поиск плательщика: '{search_text}' -> нормализовано: '{search_normalized}'")
        
        # Получаем всех плательщиков для поиска
        all_payers = self.env['amanat.payer'].search([])
        
        # Стратегия 1: Точное совпадение (после нормализации)
        for payer in all_payers:
            if payer.name:
                payer_normalized = self._normalize_payer_name(payer.name)
                if payer_normalized == search_normalized:
                    _logger.info(f"[_advanced_payer_search] Найден точный матч: '{payer.name}' (ID: {payer.id})")
                    return payer
        
        # Стратегия 2: Поиск по ИНН (если поисковый текст похож на ИНН - только цифры, длина 10 или 12)
        import re
        if re.match(r'^\d{10}$|^\d{12}$', search_text.strip()):
            payer_by_inn = all_payers.filtered(lambda p: p.inn and p.inn.strip() == search_text.strip())
            if payer_by_inn:
                _logger.info(f"[_advanced_payer_search] Найден по ИНН: '{payer_by_inn[0].name}' (ID: {payer_by_inn[0].id})")
                return payer_by_inn[0]
        
        # Стратегия 3: Поиск по началу строки
        exact_start_matches = []
        for payer in all_payers:
            if payer.name:
                payer_normalized = self._normalize_payer_name(payer.name)
                if payer_normalized.startswith(search_normalized):
                    exact_start_matches.append(payer)
        
        if exact_start_matches:
            # Сортируем по длине названия (короткие сначала)
            exact_start_matches.sort(key=lambda p: len(p.name) if p.name else 0)
            _logger.info(f"[_advanced_payer_search] Найден по началу строки: '{exact_start_matches[0].name}' (ID: {exact_start_matches[0].id})")
            return exact_start_matches[0]
        
        # Стратегия 4: Поиск по содержанию (если поисковый запрос достаточно длинный)
        if len(search_normalized) >= 3:
            contains_matches = []
            for payer in all_payers:
                if payer.name:
                    payer_normalized = self._normalize_payer_name(payer.name)
                    if search_normalized in payer_normalized:
                        contains_matches.append(payer)
            
            if contains_matches:
                # Сортируем по длине названия (короткие сначала)
                contains_matches.sort(key=lambda p: len(p.name) if p.name else 0)
                _logger.info(f"[_advanced_payer_search] Найден по содержанию: '{contains_matches[0].name}' (ID: {contains_matches[0].id})")
                return contains_matches[0]
        
        # Стратегия 5: Нечеткий поиск (если ничего не найдено и текст достаточно длинный)
        if len(search_normalized) >= 4:
            fuzzy_matches = []
            for payer in all_payers:
                if payer.name:
                    payer_normalized = self._normalize_payer_name(payer.name)
                    # Простая эвристика: если больше половины символов совпадают
                    if self._calculate_similarity(search_normalized, payer_normalized) > 0.6:
                        fuzzy_matches.append(payer)
            
            if fuzzy_matches:
                # Сортируем по похожести и длине
                fuzzy_matches.sort(key=lambda p: (
                    -self._calculate_similarity(search_normalized, self._normalize_payer_name(p.name)),
                    len(p.name) if p.name else 0
                ))
                _logger.info(f"[_advanced_payer_search] Найден нечеткий матч: '{fuzzy_matches[0].name}' (ID: {fuzzy_matches[0].id})")
                return fuzzy_matches[0]
        
        _logger.warning(f"[_advanced_payer_search] Плательщик не найден для: '{search_text}'")
        return None
    
    def _calculate_similarity(self, str1, str2):
        """
        Вычисляет улучшенную меру похожести между двумя строками.
        Учитывает совпадение слов и символов.
        Возвращает значение от 0 до 1, где 1 - полное совпадение.
        """
        if not str1 or not str2:
            return 0.0
        
        # Алгоритм 1: Совпадение по словам (более важно)
        words1 = set(word.strip() for word in str1.lower().split() if len(word.strip()) >= 2)
        words2 = set(word.strip() for word in str2.lower().split() if len(word.strip()) >= 2)
        
        word_similarity = 0.0
        if words1 and words2:
            word_intersection = len(words1.intersection(words2))
            word_union = len(words1.union(words2))
            word_similarity = word_intersection / word_union if word_union > 0 else 0.0
        
        # Алгоритм 2: Совпадение по символам (менее важно)
        chars1 = set(str1.lower())
        chars2 = set(str2.lower())
        
        char_similarity = 0.0
        if chars1 and chars2:
            char_intersection = len(chars1.intersection(chars2))
            char_union = len(chars1.union(chars2))
            char_similarity = char_intersection / char_union if char_union > 0 else 0.0
        
        # Комбинированная оценка: 70% вес для слов, 30% для символов
        combined_similarity = word_similarity * 0.7 + char_similarity * 0.3
        
        return combined_similarity
    
    def _advanced_country_search(self, search_text):
        """
        Расширенный поиск страны с несколькими стратегиями:
        1. Поиск по коду страны (если текст похож на код - 2-3 символа)
        2. Точное совпадение по краткому названию (после нормализации)
        3. Точное совпадение по полному названию (после нормализации)
        4. Поиск по началу строки (краткое и полное название)
        5. Поиск по содержанию
        6. Нечеткий поиск
        """
        if not search_text:
            return None
            
        search_original = str(search_text).strip()
        search_normalized = self._normalize_payer_name(search_text)  # Используем ту же нормализацию
        
        if not search_normalized:
            return None
            
        _logger.info(f"[_advanced_country_search] Поиск страны: '{search_text}' -> нормализовано: '{search_normalized}'")
        
        # Получаем все страны для поиска
        all_countries = self.env['amanat.country'].search([])
        
        # Стратегия 1: Поиск по коду страны (если текст короткий и похож на код)
        if len(search_original) <= 3 and search_original.isdigit():
            try:
                country_code = int(search_original)
                country_by_code = all_countries.filtered(lambda c: c.code == country_code)
                if country_by_code:
                    _logger.info(f"[_advanced_country_search] Найдена по коду: '{country_by_code[0].name}' (код: {country_by_code[0].code})")
                    return country_by_code[0]
            except ValueError:
                pass
        
        # Стратегия 2: Точное совпадение по краткому названию (после нормализации)
        for country in all_countries:
            if country.name:
                country_name_normalized = self._normalize_payer_name(country.name)
                if country_name_normalized == search_normalized:
                    _logger.info(f"[_advanced_country_search] Найдена точное совпадение по названию: '{country.name}' (ID: {country.id})")
                    return country
        
        # Стратегия 3: Точное совпадение по полному названию (после нормализации)
        for country in all_countries:
            if country.full_name:
                country_full_normalized = self._normalize_payer_name(country.full_name)
                if country_full_normalized == search_normalized:
                    _logger.info(f"[_advanced_country_search] Найдена точное совпадение по полному названию: '{country.name}' (полное: '{country.full_name}')")
                    return country
        
        # Стратегия 4: Поиск по началу строки
        start_matches = []
        for country in all_countries:
            # Проверяем краткое название
            if country.name:
                country_name_normalized = self._normalize_payer_name(country.name)
                if country_name_normalized.startswith(search_normalized):
                    start_matches.append((country, 'name'))
            
            # Проверяем полное название
            if country.full_name:
                country_full_normalized = self._normalize_payer_name(country.full_name)
                if country_full_normalized.startswith(search_normalized):
                    start_matches.append((country, 'full_name'))
        
        if start_matches:
            # Приоритет: сначала краткие названия, потом полные
            start_matches.sort(key=lambda x: (
                0 if x[1] == 'name' else 1,  # Приоритет краткому названию
                len(x[0].name) if x[0].name else 999  # Потом по длине
            ))
            country, match_type = start_matches[0]
            match_field = 'краткое название' if match_type == 'name' else 'полное название'
            _logger.info(f"[_advanced_country_search] Найдена по началу строки ({match_field}): '{country.name}' (ID: {country.id})")
            return country
        
        # Стратегия 5: Поиск по содержанию (если поисковый запрос достаточно длинный)
        if len(search_normalized) >= 3:
            contains_matches = []
            for country in all_countries:
                # Проверяем краткое название
                if country.name:
                    country_name_normalized = self._normalize_payer_name(country.name)
                    if search_normalized in country_name_normalized:
                        contains_matches.append((country, 'name'))
                
                # Проверяем полное название
                if country.full_name:
                    country_full_normalized = self._normalize_payer_name(country.full_name)
                    if search_normalized in country_full_normalized:
                        contains_matches.append((country, 'full_name'))
            
            if contains_matches:
                # Приоритет: сначала краткие названия, потом полные, потом по длине
                contains_matches.sort(key=lambda x: (
                    0 if x[1] == 'name' else 1,
                    len(x[0].name) if x[0].name else 999
                ))
                country, match_type = contains_matches[0]
                match_field = 'краткое название' if match_type == 'name' else 'полное название'
                _logger.info(f"[_advanced_country_search] Найдена по содержанию ({match_field}): '{country.name}' (ID: {country.id})")
                return country
        
        # Стратегия 6: Нечеткий поиск (если ничего не найдено и текст достаточно длинный)
        if len(search_normalized) >= 4:
            fuzzy_matches = []
            for country in all_countries:
                max_similarity = 0.0
                match_type = 'name'
                
                # Проверяем краткое название
                if country.name:
                    country_name_normalized = self._normalize_payer_name(country.name)
                    similarity = self._calculate_similarity(search_normalized, country_name_normalized)
                    if similarity > max_similarity:
                        max_similarity = similarity
                        match_type = 'name'
                
                # Проверяем полное название
                if country.full_name:
                    country_full_normalized = self._normalize_payer_name(country.full_name)
                    similarity = self._calculate_similarity(search_normalized, country_full_normalized)
                    if similarity > max_similarity:
                        max_similarity = similarity
                        match_type = 'full_name'
                
                if max_similarity > 0.6:
                    fuzzy_matches.append((country, max_similarity, match_type))
            
            if fuzzy_matches:
                # Сортируем по похожести (убывание) и приоритету поля
                fuzzy_matches.sort(key=lambda x: (-x[1], 0 if x[2] == 'name' else 1))
                country, similarity, match_type = fuzzy_matches[0]
                match_field = 'краткое название' if match_type == 'name' else 'полное название'
                _logger.info(f"[_advanced_country_search] Найдена нечеткий матч ({match_field}, similarity: {similarity:.2f}): '{country.name}' (ID: {country.id})")
                return country
        
        _logger.warning(f"[_advanced_country_search] Страна не найдена для: '{search_text}'")
        return None
    
    def _advanced_contragent_search(self, search_text, context_type="контрагент"):
        """
        Расширенный поиск контрагента с несколькими стратегиями:
        1. Поиск по ИНН (если текст похож на ИНН - 10 или 12 цифр)
        2. Точное совпадение по названию (после нормализации)
        3. Поиск по началу строки
        4. Поиск по содержанию
        5. Нечеткий поиск
        6. Поиск по ИНН плательщиков (payer_inn)
        
        context_type: строка для логирования ("агент", "клиент", "контрагент")
        """
        if not search_text:
            return None
            
        search_original = str(search_text).strip()
        search_normalized = self._normalize_payer_name(search_text)  # Используем ту же нормализацию
        
        if not search_normalized:
            return None
            
        _logger.info(f"[_advanced_contragent_search] Поиск {context_type}: '{search_text}' -> нормализовано: '{search_normalized}'")
        
        # Получаем всех контрагентов для поиска
        all_contragents = self.env['amanat.contragent'].search([])
        _logger.info(f"[_advanced_contragent_search] Всего контрагентов в системе: {len(all_contragents)}")
        
        # Стратегия 1: Поиск по ИНН (если поисковый текст похож на ИНН - только цифры, длина 10 или 12)
        import re
        if re.match(r'^\d{10}$|^\d{12}$', search_original):
            _logger.info(f"[_advanced_contragent_search] Стратегия 1: Поиск по ИНН '{search_original}'")
            
            # Поиск по собственному ИНН контрагента
            contragent_by_inn = all_contragents.filtered(lambda c: c.inn and c.inn.strip() == search_original)
            if contragent_by_inn:
                _logger.info(f"[_advanced_contragent_search] Найден {context_type} по ИНН: '{contragent_by_inn[0].name}' (ИНН: {contragent_by_inn[0].inn})")
                return contragent_by_inn[0]
            
            # Поиск по ИНН плательщиков
            contragent_by_payer_inn = all_contragents.filtered(lambda c: c.payer_inn and search_original in c.payer_inn)
            if contragent_by_payer_inn:
                _logger.info(f"[_advanced_contragent_search] Найден {context_type} по ИНН плательщика: '{contragent_by_payer_inn[0].name}' (payer_inn: {contragent_by_payer_inn[0].payer_inn})")
                return contragent_by_payer_inn[0]
            
            _logger.info(f"[_advanced_contragent_search] Стратегия 1: ИНН '{search_original}' не найден")
        else:
            _logger.info(f"[_advanced_contragent_search] Стратегия 1: Пропускаем поиск по ИНН - '{search_original}' не похож на ИНН")
        
        # Стратегия 2: Точное совпадение по названию (после нормализации)
        _logger.info(f"[_advanced_contragent_search] Стратегия 2: Проверяем точное совпадение для '{search_normalized}'")
        exact_matches_checked = 0
        for contragent in all_contragents:
            if contragent.name:
                contragent_normalized = self._normalize_payer_name(contragent.name)
                exact_matches_checked += 1
                if contragent_normalized == search_normalized:
                    _logger.info(f"[_advanced_contragent_search] Найден {context_type} точное совпадение: '{contragent.name}' (ID: {contragent.id})")
                    return contragent
        _logger.info(f"[_advanced_contragent_search] Стратегия 2: Проверено {exact_matches_checked} контрагентов, точных совпадений не найдено")
        
        # Стратегия 3: Поиск по началу строки
        _logger.info(f"[_advanced_contragent_search] Стратегия 3: Проверяем поиск по началу строки для '{search_normalized}'")
        start_matches = []
        start_matches_checked = 0
        for contragent in all_contragents:
            if contragent.name:
                contragent_normalized = self._normalize_payer_name(contragent.name)
                start_matches_checked += 1
                if contragent_normalized.startswith(search_normalized):
                    start_matches.append(contragent)
                    _logger.info(f"[_advanced_contragent_search] DEBUG: Найден кандидат по началу строки: '{contragent.name}' -> '{contragent_normalized}'")
        
        _logger.info(f"[_advanced_contragent_search] Стратегия 3: Проверено {start_matches_checked} контрагентов, найдено кандидатов: {len(start_matches)}")
        
        if start_matches:
            # Сортируем по длине названия (короткие сначала), как в существующем name_search
            start_matches.sort(key=lambda c: len(c.name) if c.name else 999)
            _logger.info(f"[_advanced_contragent_search] Найден {context_type} по началу строки: '{start_matches[0].name}' (ID: {start_matches[0].id})")
            return start_matches[0]
        
        # Стратегия 3.5: Поиск по частям названия (разбиваем на слова)
        _logger.info("[_advanced_contragent_search] Стратегия 3.5: Проверяем поиск по частям названия")
        search_words = [word.strip() for word in search_normalized.split() if len(word.strip()) >= 2]
        _logger.info(f"[_advanced_contragent_search] Слова для поиска: {search_words}")
        
        if search_words:
            word_matches = []
            exact_word_matches = []  # Для точных совпадений с отдельными словами
            
            for contragent in all_contragents:
                if contragent.name:
                    contragent_normalized = self._normalize_payer_name(contragent.name)
                    contragent_words = set(word.strip() for word in contragent_normalized.split() if len(word.strip()) >= 2)
                    
                    # Специальная проверка: если название контрагента точно совпадает с одним из слов поиска
                    if contragent_normalized in search_words:
                        exact_word_matches.append(contragent)
                        _logger.info(f"[_advanced_contragent_search] DEBUG: Точное совпадение с словом '{contragent.name}' -> '{contragent_normalized}'")
                    
                    # Проверяем, сколько слов совпадает
                    matching_words = set(search_words).intersection(contragent_words)
                    if matching_words:
                        match_ratio = len(matching_words) / len(search_words)
                        word_matches.append((contragent, match_ratio, matching_words))
                        
                        # Специальное логирование для интересных кандидатов
                        if match_ratio >= 0.3 or any(word in contragent_normalized for word in ['тдк', 'джевэллэри', 'трейдинг']):
                            _logger.info(f"[_advanced_contragent_search] DEBUG: Кандидат по словам '{contragent.name}' -> '{contragent_normalized}' (совпадений: {len(matching_words)}/{len(search_words)} = {match_ratio:.2f}, слова: {matching_words})")
            
            # Приоритет: сначала точные совпадения с отдельными словами
            if exact_word_matches:
                # Сортируем по длине (короткие сначала)
                exact_word_matches.sort(key=lambda c: len(c.name) if c.name else 999)
                contragent = exact_word_matches[0]
                _logger.info(f"[_advanced_contragent_search] Найден {context_type} по точному совпадению со словом: '{contragent.name}' (ID: {contragent.id})")
                return contragent
            
            if word_matches:
                # Сортируем по проценту совпадающих слов (убывание), потом по длине названия
                word_matches.sort(key=lambda x: (-x[1], len(x[0].name) if x[0].name else 999))
                
                best_match = word_matches[0]
                if best_match[1] >= 0.5:  # Если совпадает минимум 50% слов
                    contragent, match_ratio, matching_words = best_match
                    _logger.info(f"[_advanced_contragent_search] Найден {context_type} по частям названия: '{contragent.name}' (совпадений: {len(matching_words)}/{len(search_words)} = {match_ratio:.2f}, слова: {matching_words})")
                    return contragent
                else:
                    _logger.info(f"[_advanced_contragent_search] Лучший кандидат по словам: '{best_match[0].name}' (совпадений: {best_match[1]:.2f}, но меньше порога 0.5)")
        
        # Стратегия 4: Поиск по содержанию (если поисковый запрос достаточно длинный)
        if len(search_normalized) >= 3:
            _logger.info(f"[_advanced_contragent_search] Стратегия 4: Проверяем поиск по содержанию для '{search_normalized}'")
            contains_matches = []
            contains_matches_checked = 0
            for contragent in all_contragents:
                if contragent.name:
                    contragent_normalized = self._normalize_payer_name(contragent.name)
                    contains_matches_checked += 1
                    if search_normalized in contragent_normalized:
                        contains_matches.append(contragent)
                        _logger.info(f"[_advanced_contragent_search] DEBUG: Найден кандидат по содержанию: '{contragent.name}' -> '{contragent_normalized}'")
            
            _logger.info(f"[_advanced_contragent_search] Стратегия 4: Проверено {contains_matches_checked} контрагентов, найдено кандидатов: {len(contains_matches)}")
            
            if contains_matches:
                # Сортируем по длине названия (короткие сначала)
                contains_matches.sort(key=lambda c: len(c.name) if c.name else 999)
                _logger.info(f"[_advanced_contragent_search] Найден {context_type} по содержанию: '{contains_matches[0].name}' (ID: {contains_matches[0].id})")
                return contains_matches[0]
        
        # Стратегия 5: Нечеткий поиск (если ничего не найдено и текст достаточно длинный)
        if len(search_normalized) >= 4:
            _logger.info(f"[_advanced_contragent_search] Стратегия 5: Проверяем нечеткий поиск для '{search_normalized}'")
            fuzzy_matches = []
            fuzzy_matches_checked = 0
            for contragent in all_contragents:
                if contragent.name:
                    contragent_normalized = self._normalize_payer_name(contragent.name)
                    similarity = self._calculate_similarity(search_normalized, contragent_normalized)
                    fuzzy_matches_checked += 1
                    
                    if similarity > 0.6:
                        fuzzy_matches.append((contragent, similarity))
                        _logger.info(f"[_advanced_contragent_search] DEBUG: Найден кандидат нечеткого поиска: '{contragent.name}' -> '{contragent_normalized}' (similarity: {similarity:.3f})")
            
            _logger.info(f"[_advanced_contragent_search] Стратегия 5: Проверено {fuzzy_matches_checked} контрагентов, найдено кандидатов: {len(fuzzy_matches)}")
            
            if fuzzy_matches:
                # Сортируем по похожести (убывание) и длине названия
                fuzzy_matches.sort(key=lambda x: (-x[1], len(x[0].name) if x[0].name else 999))
                
                # Логируем топ-5 кандидатов для анализа
                _logger.info(f"[_advanced_contragent_search] DEBUG: Топ-{min(5, len(fuzzy_matches))} кандидатов нечеткого поиска:")
                for i, (candidate, sim) in enumerate(fuzzy_matches[:5]):
                    _logger.info(f"[_advanced_contragent_search] DEBUG: {i+1}. '{candidate.name}' (similarity: {sim:.3f})")
                
                contragent, similarity = fuzzy_matches[0]
                _logger.info(f"[_advanced_contragent_search] Найден {context_type} нечеткий матч (similarity: {similarity:.2f}): '{contragent.name}' (ID: {contragent.id})")
                return contragent
        
        _logger.warning(f"[_advanced_contragent_search] {context_type.capitalize()} не найден для: '{search_text}'")
        return None

    def analyze_swift_documents_for_approved_date(self):
        """
        Анализирует SWIFT документы для извлечения даты из строки "approved at"
        и автоматически заполняет поле supplier_currency_paid_date
        """
        try:
            _logger.info(f"[analyze_swift_documents_for_approved_date] Начинаем анализ SWIFT документов для заявки {self.zayavka_id}")
            
            # Проверяем, есть ли SWIFT документы
            if not self.swift_attachments:
                _logger.warning(f"[analyze_swift_documents_for_approved_date] Нет SWIFT документов для анализа в заявке {self.zayavka_id}")
                return
            
            # Проверяем, не заполнено ли уже поле supplier_currency_paid_date
            if self.supplier_currency_paid_date:
                _logger.info(f"[analyze_swift_documents_for_approved_date] Поле 'оплачена валюта поставщику' уже заполнено ({self.supplier_currency_paid_date}), пропускаем анализ")
                return
            
            # Анализируем каждый SWIFT документ
            approved_date = None
            for attachment in self.swift_attachments:
                _logger.info(f"[analyze_swift_documents_for_approved_date] Анализируем документ: {attachment.name}")
                
                # Извлекаем дату из документа
                extracted_date = self._extract_approved_date_from_swift(attachment)
                if extracted_date:
                    approved_date = extracted_date
                    _logger.info(f"[analyze_swift_documents_for_approved_date] Найдена дата 'approved at': {approved_date}")
                    break
            
            # Если дата найдена, обновляем поле
            if approved_date:
                self.supplier_currency_paid_date = approved_date
                _logger.info(f"[analyze_swift_documents_for_approved_date] Автоматически установлена дата оплаты валюты поставщику: {approved_date}")
                
                # Уведомляем пользователя
                self._notify_user_simple(
                    title="SWIFT Анализ",
                    message=f"Извлечена дата 'approved at' из SWIFT документа: {approved_date.strftime('%d.%m.%Y')}",
                    warning=False,
                    sticky=True
                )
            else:
                _logger.warning(f"[analyze_swift_documents_for_approved_date] Не удалось найти дату 'approved at' в SWIFT документах заявки {self.zayavka_id}")
                
        except Exception as e:
            _logger.error(f"[analyze_swift_documents_for_approved_date] Ошибка при анализе SWIFT документов: {str(e)}")

    def _extract_approved_date_from_swift(self, attachment):
        """
        Извлекает дату из строки "approved at" в SWIFT документе
        """
        try:
            # Специальный промпт для анализа SWIFT документов
            swift_prompt = """
            Проанализируй SWIFT документ и найди дату в строке "approved at" или похожих строках, указывающих на дату одобрения/подтверждения платежа.
            
            Верни результат СТРОГО в формате JSON:
            {
                "approved_date": "YYYY-MM-DD"
            }
            
            Если дата не найдена, верни:
            {
                "approved_date": null
            }
            
            Ищи следующие паттерны:
            - "approved at" + дата
            - "approved on" + дата  
            - "confirmation date" + дата
            - "value date" + дата
            - любые другие строки, указывающие на дату подтверждения платежа
            
            Дату верни в формате YYYY-MM-DD (например: 2024-01-15).
            """
            
            # Анализируем документ с помощью YandexGPT
            _logger.info(f"[_extract_approved_date_from_swift] Тип файла: {attachment.mimetype}, имя: {attachment.name}")
            
            if attachment.mimetype == 'application/pdf' or (attachment.name and attachment.name.lower().endswith('.pdf')):
                _logger.info("[_extract_approved_date_from_swift] Обрабатываем как PDF документ")
                # Для PDF используем OCR + GPT
                gpt_response = self._analyze_pdf_with_custom_prompt(attachment, swift_prompt)
            else:
                _logger.info("[_extract_approved_date_from_swift] Обрабатываем как текстовый документ")
                # Для текстовых файлов используем прямой анализ
                gpt_response = self._analyze_text_with_custom_prompt(attachment, swift_prompt)
            
            if not gpt_response:
                _logger.warning(f"[_extract_approved_date_from_swift] Не получен ответ от YandexGPT для документа {attachment.name}")
                return None
            
            _logger.info(f"[_extract_approved_date_from_swift] Получен ответ от YandexGPT: {gpt_response}")
            
            # Парсим ответ GPT
            import json
            import re
            from datetime import datetime
            
            # Ищем JSON в ответе
            json_match = re.search(r'\{.*?\}', gpt_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    parsed_data = json.loads(json_str)
                    approved_date_str = parsed_data.get('approved_date')
                    
                    if approved_date_str and approved_date_str != 'null':
                        # Парсим дату
                        try:
                            approved_date = datetime.strptime(approved_date_str, '%Y-%m-%d').date()
                            return approved_date
                        except ValueError:
                            _logger.warning(f"[_extract_approved_date_from_swift] Неверный формат даты: {approved_date_str}")
                            return None
                    
                except json.JSONDecodeError as e:
                    _logger.error(f"[_extract_approved_date_from_swift] Ошибка парсинга JSON: {e}")
                    return None
            
            _logger.warning(f"[_extract_approved_date_from_swift] Не найден JSON с датой в ответе GPT: {gpt_response}")
            return None
            
        except Exception as e:
            _logger.error(f"[_extract_approved_date_from_swift] Ошибка при извлечении даты из SWIFT документа: {str(e)}")
            return None

    def _analyze_pdf_with_custom_prompt(self, attachment, custom_prompt):
        """
        Анализирует PDF документ с кастомным промптом
        """
        try:
            # Получаем PDF в base64
            pdfs_data = self._get_pdf_attachments_base64(attachment)
            if not pdfs_data:
                return None
            
            pdf_data = pdfs_data[0]  # Берем первый PDF
            
            # Отправляем в Yandex Vision OCR для распознавания текста
            recognized_text = self._send_image_to_yandex_gpt_vision(pdf_data)
            if not recognized_text:
                _logger.warning(f"[_analyze_pdf_with_custom_prompt] Не удалось распознать текст из PDF: {attachment.name}")
                return None
            
            _logger.info(f"[_analyze_pdf_with_custom_prompt] Распознанный текст из PDF ({len(recognized_text)} символов): {recognized_text[:200]}...")
            
            # Отправляем распознанный текст в YandexGPT с кастомным промптом
            return self._send_text_to_yandex_gpt_with_prompt(recognized_text, custom_prompt)
            
        except Exception as e:
            _logger.error(f"[_analyze_pdf_with_custom_prompt] Ошибка: {str(e)}")
            return None

    def _analyze_text_with_custom_prompt(self, attachment, custom_prompt):
        """
        Анализирует текстовый документ с кастомным промптом
        """
        try:
            # Читаем содержимое файла
            if not attachment.datas:
                return None
            
            # Декодируем содержимое
            import base64
            file_content = base64.b64decode(attachment.datas).decode('utf-8', errors='ignore')
            
            # Отправляем в YandexGPT с кастомным промптом
            return self._send_text_to_yandex_gpt_with_prompt(file_content, custom_prompt)
            
        except Exception as e:
            _logger.error(f"[_analyze_text_with_custom_prompt] Ошибка: {str(e)}")
            return None

    def _send_text_to_yandex_gpt_with_prompt(self, text, custom_prompt):
        """
        Отправляет текст в YandexGPT с кастомным промптом
        """
        try:
            cfg = _get_yandex_gpt_config(self.env, "zayavka")
            if not cfg['api_key'] or not cfg['folder_id']:
                _logger.error("[_send_text_to_yandex_gpt_with_prompt] Не настроены API ключ и/или Folder ID")
                return None

            user_message = f"{custom_prompt}\n\nДокумент для анализа:\n{text}"

            data = {
                "modelUri": f"gpt://{cfg['folder_id']}/yandexgpt/latest",
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.1,  # Низкая температура для точности
                    "maxTokens": 1000
                },
                "messages": [
                    {"role": "user", "text": user_message}
                ]
            }

            headers = {
                'Authorization': f'Api-Key {cfg["api_key"]}',
                'Content-Type': 'application/json'
            }

            response = requests.post(URL, headers=headers, json=data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if 'result' in result and 'alternatives' in result['result']:
                    alternatives = result['result']['alternatives']
                    if alternatives and len(alternatives) > 0:
                        gpt_response = alternatives[0]['message']['text']
                        _logger.info(f"[_send_text_to_yandex_gpt_with_prompt] YandexGPT ответ: {gpt_response}")
                        return gpt_response
            else:
                _logger.error(f"[_send_text_to_yandex_gpt_with_prompt] Ошибка API: {response.status_code} - {response.text}")
                
        except Exception as e:
            _logger.error(f"[_send_text_to_yandex_gpt_with_prompt] Ошибка: {str(e)}")
            
        return None

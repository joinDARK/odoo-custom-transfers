import requests
import logging
import base64
import json
import os
from odoo import models, api

_logger = logging.getLogger(__name__)

API_KEY = os.environ.get('YANDEX_API_KEY', '')
FOLDER_ID = 'b1gutoi9c7ngrfbtd6cl'
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

После этого сопоставь полученные данные и выдай мне информацию в формате json

сумма - amount
валюта - currency
кто платит - subagent_payer_ids
кому платят - exporter_importer_name
страна получателя - country_id
свифт код - bank_swift
назначение платежа - payment_purpose

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
]


class ZayavkaYandexGPTAnalyse(models.Model):
    _inherit = 'amanat.zayavka'

    def action_analyse_with_yandex_gpt(self):
        self._get_yandex_gpt_config()

    def action_test_screen_sber_ocr(self):
        """
        Тестовый метод для полного анализа изображений screen_sber: OCR + YandexGPT + обновление полей
        """
        try:
            _logger.info("🚀 Запуск ПОЛНОГО АНАЛИЗА для screen_sber_attachments")
            _logger.info("📋 Этапы: 1) OCR распознавание -> 2) YandexGPT анализ -> 3) Обновление полей заявки")
            
            # Анализируем изображения (теперь с полной обработкой)
            results = self.analyze_screen_sber_images_with_yandex_gpt()
            
            if results:
                _logger.info(f"ТЕСТ ЗАВЕРШЕН: Обработано {len(results)} изображений")
                _logger.info("📋 СВОДКА РЕЗУЛЬТАТОВ:")
                for i, result in enumerate(results, 1):
                    _logger.info(f"  {i}. {result['image_name']}")
                    _logger.info(f"     Длина распознанного текста: {len(result['recognized_text'])} символов")
                    _logger.info(f"     Первые 100 символов: {result['recognized_text'][:100]}...")
                _logger.info("✅ Все изображения прошли полный цикл обработки и анализа!")
            else:
                _logger.info("❌ ТЕСТ: Не удалось распознать текст ни из одного изображения")
                
        except Exception as e:
            _logger.error(f"Ошибка при тестировании полного анализа screen_sber: {str(e)}")

    @api.model
    def _get_yandex_gpt_config(self):
        headers = {
            "Authorization": f"Api-Key {API_KEY}",
            "Content-Type": "application/json",
            "X-Folder-Id": FOLDER_ID
        }

        data = {
            "modelUri": f"gpt://{FOLDER_ID}/yandexgpt/latest",  # или rc/pro/lite, если нужно
            "completionOptions": {
                "stream": False,
                "temperature": 0.3,
                "maxTokens": "1000"
            },
            "messages": [
                {"role": "system", "text": "Ты умный ассистент. Говори кратко и понятно."},
                {"role": "user", "text": "Объясни принцип работы нейронной сети простым языком."}
            ]
        }

        return headers, data

    def analyze_document_with_yandex_gpt(self, document_json):
        """
        Анализирует JSON документа с помощью YandexGPT
        """
        try:
            headers = {
                "Authorization": f"Api-Key {API_KEY}",
                "Content-Type": "application/json",
                "X-Folder-Id": FOLDER_ID
            }

            # Формируем сообщение с JSON документа
            user_message = f"Документ для анализа:\n{document_json}"

            data = {
                "modelUri": f"gpt://{FOLDER_ID}/yandexgpt/latest",
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.3,
                    "maxTokens": "2000"
                },
                "messages": [
                    {"role": "system", "text": PROMPT},
                    {"role": "user", "text": user_message}
                ]
            }

            response = requests.post(URL, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                # Извлекаем текст ответа
                if 'result' in result and 'alternatives' in result['result']:
                    alternatives = result['result']['alternatives']
                    if alternatives and len(alternatives) > 0:
                        gpt_response = alternatives[0]['message']['text']
                        
                        # Выводим ответ нейронки в логер
                        _logger.info(f"🤖 YandexGPT АНАЛИЗ ДОКУМЕНТА для заявки {self.zayavka_id}:\n{gpt_response}")
                        
                        # Парсим ответ и обновляем поля заявки
                        self._update_fields_from_gpt_response(gpt_response)
                        
                        return gpt_response
                else:
                    _logger.warning(f"Неожиданная структура ответа от YandexGPT: {result}")
            else:
                _logger.error(f"Ошибка API YandexGPT: {response.status_code} - {response.text}")
                
        except Exception as e:
            _logger.error(f"Ошибка при анализе документа с YandexGPT: {str(e)}")
            
        return None

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
                    _logger.warning(f"Не удалось найти JSON в ответе YandexGPT: {gpt_response}")
                    return

            # Парсим JSON
            try:
                parsed_data = json.loads(json_str)
            except json.JSONDecodeError as e:
                _logger.error(f"Ошибка парсинга JSON из ответа YandexGPT: {e}\nJSON: {json_str}")
                return

            # Подготавливаем данные для обновления
            update_values = {}
            
            # Маппинг полей из JSON в поля модели (используем реальные поля из zayavka.py)
            field_mapping = {
                'amount': 'amount',  # Сумма заявки (строка 916)
                'currency': 'currency',  # Валюта (строка 846)
                'subagent_payer_ids': None,  # Это Many2many поле к amanat.payer, обработаем отдельно
                'exporter_importer_name': 'exporter_importer_name',  # Наименование покупателя/продавца (строка 82)
                'country_id': None,  # Это Many2one поле, обработаем отдельно  
                'bank_swift': 'bank_swift',  # SWIFT код банка (строка 84)
                'payment_purpose': 'payment_purpose',  # Назначение платежа (строка 1165)
            }
            
            for json_key, model_field in field_mapping.items():
                if json_key in parsed_data and parsed_data[json_key] and model_field:
                    value = parsed_data[json_key]
                    
                    # Специальная обработка для разных типов полей
                    if model_field == 'amount' and value:
                        try:
                            # Конвертируем в float, убираем пробелы и запятые
                            value = float(str(value).replace(',', '.').replace(' ', ''))
                            update_values[model_field] = value
                        except (ValueError, TypeError):
                            _logger.warning(f"Не удалось конвертировать сумму: {value}")

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
                    
                    else:
                        # Для текстовых полей сохраняем как строку
                        update_values[model_field] = str(value)
            
            # Обработка специальных полей Many2one и Many2many
            self._handle_special_fields(parsed_data, update_values)

            # Обновляем поля, если есть что обновлять
            if update_values:
                # Фильтруем только существующие поля модели
                existing_fields = set(self._fields.keys())
                filtered_values = {k: v for k, v in update_values.items() if k in existing_fields}
                
                if filtered_values:
                    self.write(filtered_values)
                    
                    # Логируем обновления
                    updated_fields = ', '.join(f"{k}: {v}" for k, v in filtered_values.items())
                    _logger.info(f"✅ Обновлены поля заявки {self.zayavka_id}: {updated_fields}")
                else:
                    _logger.warning(f"Ни одно из полей не найдено в модели: {list(update_values.keys())}")
            else:
                _logger.info("Нет данных для обновления в ответе YandexGPT")
                
        except Exception as e:
            _logger.error(f"Ошибка при обновлении полей из ответа YandexGPT: {str(e)}")

    def _handle_special_fields(self, parsed_data, update_values):
        """
        Обработка специальных полей Many2one и Many2many
        """
        try:
            # Обработка country_id (Many2one к amanat.country)
            if 'country_id' in parsed_data and parsed_data['country_id']:
                country_name = str(parsed_data['country_id']).strip().upper()
                
                # Ищем страну по названию
                country = self.env['amanat.country'].search([
                    ('name', 'ilike', country_name)
                ], limit=1)
                
                if country:
                    update_values['country_id'] = country.id
                    _logger.info(f"Найдена страна: {country.name} (ID: {country.id})")
                else:
                    _logger.warning(f"Страна '{country_name}' не найдена в базе данных, пропускаем обновление поля country_id")
            
            # Обработка subagent_payer_ids (Many2many к amanat.payer)
            if 'subagent_payer_ids' in parsed_data and parsed_data['subagent_payer_ids']:
                payer_name = str(parsed_data['subagent_payer_ids']).strip()
                
                # Ищем плательщика по названию
                payer = self.env['amanat.payer'].search([
                    ('name', 'ilike', payer_name)
                ], limit=1)
                
                if payer:
                    # Очищаем поле subagent_payer_ids и добавляем нового плательщика
                    update_values['subagent_payer_ids'] = [(6, 0, [payer.id])]  # (6, 0, ids) - заменить все записи
                    _logger.info(f"Очищено поле subagent_payer_ids и добавлен плательщик субагента: {payer.name} (ID: {payer.id})")
                    
                    # Теперь ищем связанного контрагента для subagent_ids
                    if payer.contragents_ids:
                        # Берем первого связанного контрагента
                        contragent = payer.contragents_ids[0]
                        # Очищаем поле subagent_ids и добавляем нового контрагента
                        update_values['subagent_ids'] = [(6, 0, [contragent.id])]  # (6, 0, ids) - заменить все записи
                        _logger.info(f"Очищено поле subagent_ids и добавлен связанный субагент: {contragent.name} (ID: {contragent.id})")
                    else:
                        _logger.warning(f"У плательщика {payer.name} нет связанных контрагентов, пропускаем обновление поля subagent_ids")
                        
                else:
                    _logger.warning(f"Плательщик '{payer_name}' не найден в базе данных, пропускаем обновление полей subagent_payer_ids и subagent_ids")
                        
        except Exception as e:
            _logger.error(f"Ошибка при обработке специальных полей: {str(e)}")                                   

    def get_screen_sber_images_base64(self):
        """
        Получает изображения из поля screen_sber_attachments и кодирует их в base64
        """
        try:
            images_data = []
            
            if not self.screen_sber_attachments:
                _logger.info("Нет изображений в поле screen_sber_attachments")
                return images_data
            
            # Поддерживаемые форматы изображений
            supported_formats = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']
            
            for attachment in self.screen_sber_attachments:
                try:
                    # Проверяем что это изображение
                    if not attachment.mimetype or not attachment.mimetype.startswith('image/'):
                        _logger.warning(f"Файл {attachment.name} не является изображением (mimetype: {attachment.mimetype})")
                        continue
                    
                    # Получаем расширение файла
                    file_extension = attachment.name.lower().split('.')[-1] if '.' in attachment.name else ''
                    if file_extension not in supported_formats:
                        _logger.warning(f"Неподдерживаемый формат изображения: {file_extension} для файла {attachment.name}")
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
                    
                    _logger.info(f"✅ Подготовлено изображение: {attachment.name} ({attachment.mimetype}, {len(image_data)} байт)")
                    
                except Exception as e:
                    _logger.error(f"Ошибка при обработке изображения {attachment.name}: {str(e)}")
                    continue
            
            _logger.info(f"📸 Всего подготовлено изображений: {len(images_data)}")
            return images_data
            
        except Exception as e:
            _logger.error(f"Ошибка при получении изображений screen_sber: {str(e)}")
            return []

    def analyze_screen_sber_images_with_yandex_gpt(self):
        """
        Анализирует изображения из screen_sber_attachments с помощью Yandex Vision OCR API
        """
        try:
            # Получаем изображения в base64
            images_data = self.get_screen_sber_images_base64()
            
            if not images_data:
                _logger.info("📸 Нет изображений для анализа в screen_sber_attachments")
                return None
            
            # Анализируем каждое изображение
            all_recognized_text = []
            
            for i, image_info in enumerate(images_data, 1):
                _logger.info(f"🔍 Анализируем изображение {i}/{len(images_data)}: {image_info['name']}")
                
                recognized_text = self._send_image_to_yandex_gpt_vision(image_info)
                if recognized_text:
                    all_recognized_text.append({
                        'image_name': image_info['name'],
                        'recognized_text': recognized_text
                    })
                    _logger.info(f"✅ Распознан текст из {image_info['name']}:\n{recognized_text}")
                    
                    # Отправляем распознанный текст в YandexGPT для анализа
                    _logger.info(f"🤖 Отправляем текст из {image_info['name']} в YandexGPT для анализа...")
                    self._analyze_ocr_text_with_yandex_gpt(recognized_text, image_info['name'])
                    
                else:
                    _logger.warning(f"❌ Не удалось распознать текст из {image_info['name']}")
            
            # Выводим общий результат
            if all_recognized_text:
                _logger.info(f"ИТОГО: Успешно обработано {len(all_recognized_text)} изображений")
                _logger.info("📋 Все изображения прошли полный цикл: OCR -> YandexGPT -> Обновление полей заявки")
                for result in all_recognized_text:
                    _logger.info(f"📄 {result['image_name']}:\n{result['recognized_text']}\n" + "="*50)
            else:
                _logger.warning("❌ Не удалось распознать текст ни из одного изображения")
                
            return all_recognized_text
            
        except Exception as e:
            _logger.error(f"Ошибка при анализе изображений screen_sber с Yandex Vision OCR: {str(e)}")
            
        return None

    def _send_image_to_yandex_gpt_vision(self, image_info):
        """
        Отправляет одно изображение в Yandex Vision OCR API для распознавания текста
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Api-Key {API_KEY}",
                "x-folder-id": FOLDER_ID,
                "x-data-logging-enabled": "true"
            }

            # Формируем данные для OCR API
            data = {
                "mimeType": image_info['mimetype'],
                "languageCodes": ["ru", "en"],
                "content": image_info['base64']
            }

            response = requests.post(
                url=OCR_URL, 
                headers=headers, 
                data=json.dumps(data), 
                timeout=60
            )
            
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
                _logger.error(f"Ошибка API Yandex Vision OCR: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            _logger.error(f"Ошибка при отправке изображения в Yandex Vision OCR: {str(e)}")
            return None

    def _analyze_ocr_text_with_yandex_gpt(self, recognized_text, image_name):
        """
        Анализирует распознанный текст с изображения с помощью YandexGPT
        """
        try:
            headers = {
                "Authorization": f"Api-Key {API_KEY}",
                "Content-Type": "application/json",
                "X-Folder-Id": FOLDER_ID
            }

            # Формируем сообщение с распознанным текстом
            user_message = f"Текст, распознанный с изображения '{image_name}':\n{recognized_text}"

            data = {
                "modelUri": f"gpt://{FOLDER_ID}/yandexgpt/latest",
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.3,
                    "maxTokens": "2000"
                },
                "messages": [
                    {"role": "system", "text": PROMPT},
                    {"role": "user", "text": user_message}
                ]
            }

            response = requests.post(URL, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                # Извлекаем текст ответа
                if 'result' in result and 'alternatives' in result['result']:
                    alternatives = result['result']['alternatives']
                    if alternatives and len(alternatives) > 0:
                        gpt_response = alternatives[0]['message']['text']
                        
                        # Выводим ответ нейронки в логер
                        _logger.info(f"🤖 YandexGPT АНАЛИЗ ИЗОБРАЖЕНИЯ '{image_name}' для заявки {self.zayavka_id}:\n{gpt_response}")
                        
                        # Парсим ответ и обновляем поля заявки (используем тот же метод что и для документов)
                        self._update_fields_from_gpt_response(gpt_response)
                        
                        return gpt_response
                else:
                    _logger.warning(f"Неожиданная структура ответа от YandexGPT при анализе изображения '{image_name}': {result}")
            else:
                _logger.error(f"Ошибка API YandexGPT при анализе изображения '{image_name}': {response.status_code} - {response.text}")
                
        except Exception as e:
            _logger.error(f"Ошибка при анализе текста изображения '{image_name}' с YandexGPT: {str(e)}")
            
        return None                                   

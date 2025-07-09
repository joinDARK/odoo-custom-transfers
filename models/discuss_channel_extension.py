# -*- coding: utf-8 -*-
from odoo import models, api, _
from markupsafe import Markup
import re
import logging

_logger = logging.getLogger(__name__)


class DiscussChannelExtension(models.Model):
    _inherit = 'discuss.channel'

    def execute_command_swift(self, **kwargs):
        """Execute swift command to get SWIFT/BIC code information"""
        self.ensure_one()
        
        # Получаем полный текст команды из kwargs
        body = kwargs.get('body', '').strip()
        
        # Извлекаем команду и параметры
        # Поддерживаемые форматы:
        # /swift DEUTDEFFXXX [номер_заявки] - информация о банке
        # /swift track UETR [номер_заявки] - отслеживание по UETR
        # /swift status REF123 [номер_заявки] - статус по номеру перевода
        
        # Попробуем найти команду track с UETR
        track_pattern = r'/swift\s+track\s+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\s*(\d+)?'
        track_match = re.search(track_pattern, body, re.IGNORECASE)
        
        # Попробуем найти команду status с номером перевода
        status_pattern = r'/swift\s+status\s+([A-Z0-9]+)\s*(\d+)?'
        status_match = re.search(status_pattern, body, re.IGNORECASE)
        
        # Попробуем найти прямой UETR (без track)
        uetr_pattern = r'/swift\s+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\s*(\d+)?'
        uetr_match = re.search(uetr_pattern, body, re.IGNORECASE)
        
        # Если ничего не найдено, попробуем найти обычный BIC код
        general_pattern = r'/swift\s+([A-Z0-9]+)\s*(\d+)?'
        general_match = re.search(general_pattern, body, re.IGNORECASE)
        
        if track_match:
            identifier = track_match.group(1).lower()
            application_number = track_match.group(2)
            command_type = 'track_uetr'
        elif status_match:
            identifier = status_match.group(1).upper()
            application_number = status_match.group(2)
            command_type = 'track_reference'
        elif uetr_match:
            identifier = uetr_match.group(1).lower()
            application_number = uetr_match.group(2)
            command_type = 'track_uetr'
        elif general_match:
            identifier = general_match.group(1).upper()
            application_number = general_match.group(2)
            command_type = 'bank_info'
        else:
            msg = _(
                "%(bold_start)sНеверный формат команды.%(bold_end)s%(new_line)s"
                "Применение: %(new_line)s"
                "%(command_start)s/swift <БИК_КОД> [<НОМЕР_ЗАЯВКИ>]%(command_end)s - информация о банке%(new_line)s"
                "%(command_start)s/swift track <UETR> [<НОМЕР_ЗАЯВКИ>]%(command_end)s - отслеживание перевода%(new_line)s"
                "%(command_start)s/swift status <REF> [<НОМЕР_ЗАЯВКИ>]%(command_end)s - статус по номеру%(new_line)s"
                "%(new_line)sПримеры: %(new_line)s"
                "%(command_start)s/swift DEUTDEFF 123%(command_end)s%(new_line)s"
                "%(command_start)s/swift track 56f72953-d513-47d4-8b0b-ceab9b28b1c5%(command_end)s%(new_line)s"
                "%(command_start)s/swift status MT103REF123 456%(command_end)s",
                bold_start=Markup("<b>"),
                bold_end=Markup("</b>"),
                new_line=Markup("<br>"),
                command_start=Markup("<code>"),
                command_end=Markup("</code>"),
            )
            getattr(self.env.user, '_bus_send_transient_message', lambda x, y: None)(self, msg)
            return
        
        # Проверяем валидность только если это BIC код, а не UETR
        if command_type == 'bank_info':
            valid_bic_pattern = r'^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?$'
            if not re.match(valid_bic_pattern, identifier):
                msg = _(
                    "%(warning_icon)s %(bold_start)sВнимание: '%(bic_code)s' не является стандартным BIC кодом.%(bold_end)s%(new_line)s"
                    "%(new_line)s%(bold_start)sСтандартный формат BIC кода:%(bold_end)s%(new_line)s"
                    "%(bullet)s 4 буквы (код банка) + 2 буквы (код страны) + 2 символа (код города) + опционально 3 символа (код филиала)%(new_line)s"
                    "%(bullet)s Минимум 8 символов, максимум 11%(new_line)s"
                    "%(new_line)s%(bold_start)sПримеры валидных BIC кодов:%(bold_end)s%(new_line)s"
                    "%(bullet)s DEUTDEFF (Deutsche Bank, Германия)%(new_line)s"
                    "%(bullet)s SBICJPJT (Sumitomo Mitsui Banking Corporation, Япония)%(new_line)s"
                    "%(bullet)s CHASUS33 (JPMorgan Chase Bank, США)%(new_line)s"
                    "%(new_line)s%(bold_start)sПопробуйте выполнить поиск с правильным BIC кодом или продолжите с текущим кодом.%(bold_end)s",
                    warning_icon=Markup("⚠️"),
                    bold_start=Markup("<b>"),
                    bold_end=Markup("</b>"),
                    new_line=Markup("<br>"),
                    bullet=Markup("•"),
                    bic_code=identifier,
                )
                getattr(self.env.user, '_bus_send_transient_message', lambda x, y: None)(self, msg)
                # Продолжаем выполнение с предупреждением
        
        # Получаем SWIFT информацию
        swift_model = self.env['amanat.swift']
        try:
            swift_info = None
            
            # Обработка разных типов команд
            if command_type == 'track_uetr':
                # Отслеживание по UETR - вызываем API для получения статуса перевода
                swift_info = self._get_swift_tracking_status(identifier, 'uetr')
            elif command_type == 'track_reference':
                # Отслеживание по номеру перевода - вызываем API
                swift_info = self._get_swift_tracking_status(identifier, 'reference')
            elif command_type == 'bank_info' and len(identifier) == 36:
                # Если это UETR в формате обычной команды
                swift_info = self._get_swift_tracking_status(identifier, 'uetr')
            elif command_type == 'bank_info':
                # Обычный поиск информации о банке
                swift_record = swift_model.search([('uetr_no', '=', identifier)], limit=1)
                if swift_record:
                    swift_info = {
                        'bank_name': swift_record.bank_name if hasattr(swift_record, 'bank_name') else 'N/A',
                        'bank_name_short': swift_record.bank_name_short if hasattr(swift_record, 'bank_name_short') else 'N/A',
                        'country_code': swift_record.country_code if hasattr(swift_record, 'country_code') else 'N/A',
                        'country_name': swift_record.country_name if hasattr(swift_record, 'country_name') else 'N/A',
                        'city': swift_record.city if hasattr(swift_record, 'city') else 'N/A',
                        'address': swift_record.address if hasattr(swift_record, 'address') else 'N/A',
                        'branch_code': swift_record.branch_code if hasattr(swift_record, 'branch_code') else 'N/A',
                        'swift_network': swift_record.swift_network if hasattr(swift_record, 'swift_network') else False,
                        'swift_status': swift_record.swift_status if hasattr(swift_record, 'swift_status') else 'unknown',
                        'uetr_no': swift_record.uetr_no if hasattr(swift_record, 'uetr_no') else 'N/A'
                    }
                else:
                    # Если не найдено, возвращаем ошибку
                    swift_info = None
            
            # Если получили tracking информацию, форматируем и отправляем
            if swift_info and swift_info.get('transaction_type') == 'swift_transfer':
                formatted_response = self._format_swift_tracking_response(swift_info)
                if formatted_response:
                    # Конвертируем markdown в HTML для Odoo
                    html_response = formatted_response.replace('**', '<b>').replace('**', '</b>')
                    html_response = html_response.replace('`', '<code>').replace('`', '</code>')
                    
                    # Если указан номер заявки, обновляем ее
                    if application_number:
                        try:
                            application_number = int(application_number)
                            application = self.env['amanat.zayavka'].search([
                                ('id', '=', application_number)
                            ], limit=1)
                            
                            if application:
                                # Сохраняем информацию о отслеживании в заявке
                                update_data = {}
                                if swift_info.get('identifier_type') == 'uetr':
                                    update_data['swift_uetr'] = swift_info.get('identifier')
                                else:
                                    update_data['swift_transaction_ref'] = swift_info.get('identifier')
                                
                                if swift_info.get('status'):
                                    update_data['swift_transfer_status'] = swift_info.get('status')
                                
                                application.write(update_data)
                                application.message_post(
                                    body=f"SWIFT отслеживание добавлено: {swift_info.get('identifier')}"
                                )
                                
                                html_response += f"<br><br>✅ <b>Заявка #{application_number} обновлена информацией об отслеживании.</b>"
                            else:
                                html_response += f"<br><br>⚠️ <b>Заявка #{application_number} не найдена.</b>"
                        except ValueError:
                            html_response += f"<br><br>❌ <b>Неверный формат номера заявки.</b>"
                    
                    getattr(self.env.user, '_bus_send_transient_message', lambda x, y: None)(self, Markup(html_response))
                    return
            else:
                # Ищем существующую запись по BIC коду
                swift_record = swift_model.search([('bic_code', '=', identifier)], limit=1)
                if swift_record:
                    # Обновляем существующую запись
                    try:
                        swift_info_data = swift_record.fetch_swift_data()
                        if swift_info_data:
                            swift_info = swift_info_data
                    except AttributeError:
                        # Если метод не найден, используем данные из записи
                        swift_info = {
                            'bank_name': swift_record.bank_name,
                            'bank_name_short': swift_record.bank_name_short,
                            'country_code': swift_record.country_code,
                            'country_name': swift_record.country_name,
                            'city': swift_record.city,
                            'address': swift_record.address,
                            'branch_code': swift_record.branch_code,
                            'swift_network': swift_record.swift_network,
                            'swift_status': swift_record.swift_status,
                            'bic_code': swift_record.bic_code
                        }
                else:
                    # Создаем новую запись и получаем данные только через API
                    try:
                        swift_record = swift_model.create([{'bic_code': identifier}])
                        swift_info_data = swift_record.fetch_swift_data()
                        if swift_info_data:
                            swift_info = swift_info_data
                    except (AttributeError, Exception) as e:
                        # Если создание не удалось или API недоступен, оставляем swift_info = None
                        _logger.error(f"Не удалось создать запись SWIFT для {identifier}: {str(e)}")
                        swift_info = None
            
            if not swift_info:
                identifier_type = "UETR" if is_uetr else "BIC кода"
                msg = _(
                    "%(warning_icon)s %(bold_start)sИнформация для %(id_type)s %(identifier)s не найдена в API.%(bold_end)s%(new_line)s"
                    "%(bold_start)sПричина:%(bold_end)s Внешние API недоступны или код не найден.%(new_line)s"
                    "%(new_line)s%(bold_start)sПопробуйте:%(bold_end)s%(new_line)s"
                    "%(bullet)s Проверьте правильность кода%(new_line)s"
                    "%(bullet)s Попробуйте снова через некоторое время%(new_line)s"
                    "%(bullet)s Создайте запись вручную через меню SWIFT%(new_line)s",
                    warning_icon=Markup("⚠️"),
                    bold_start=Markup("<b>"),
                    bold_end=Markup("</b>"),
                    new_line=Markup("<br>"),
                    bullet=Markup("•"),
                    id_type=identifier_type,
                    identifier=identifier,
                )
                getattr(self.env.user, '_bus_send_transient_message', lambda x, y: None)(self, msg)
                return
            
            # Формируем расширенное сообщение с профессиональной SWIFT информацией
            identifier_display = identifier
            if is_uetr:
                bic_code_display = swift_info.get('bic_code', 'N/A')
                title_text = f"SWIFT информация для UETR {identifier}:"
                if bic_code_display != 'N/A':
                    title_text += f" (BIC: {bic_code_display})"
            else:
                title_text = f"SWIFT информация для BIC кода {identifier}:"
                
            # Проверка валидности и активности
            bic_valid = swift_info.get('bic_valid', False)
            bic_active = swift_info.get('bic_active', False)
            swift_network = swift_info.get('swift_network', False)
            
            # Определяем статус валидности
            if bic_valid:
                valid_display = "✅ Валидный"
            else:
                valid_display = "❌ Невалидный"
            
            # Определяем активность в SWIFT сети
            if bic_active:
                active_display = "🌐 Активен в SWIFT"
            else:
                active_display = "🔴 Неактивен в SWIFT"
            
            # Определяем подключение к сети
            if swift_network:
                network_display = "✅ Подключен"
            else:
                network_display = "❌ Не подключен"
            
            # Статус из старой системы
            status = swift_info.get('swift_status', 'unknown')
            status_display = {
                'active': '🟢 Активный',
                'inactive': '🔴 Неактивный',
                'suspended': '🟡 Приостановлен',
                'pending': '🔵 В ожидании',
                'unknown': '⚪ Неизвестно'
            }.get(status, '⚪ Неизвестно')
            
            # Источник валидации
            validation_source = swift_info.get('validation_source', 'unknown')
            source_display = {
                'iban_com': '🏛️ IBAN.com (Официальный)',
                'swiftcodes_api': '🔍 SwiftCodesAPI.com',
                'bank_suite': '🌍 Bank Suite Global',
                'fallback': '⚠️ Fallback данные',
                'manual': '👤 Ручной ввод'
            }.get(validation_source, '❓ Неизвестно')
            
            # Обработка SWIFT сервисов
            services_info = ""
            if swift_info.get('swift_services'):
                try:
                    import json
                    services = json.loads(swift_info['swift_services'])
                    if services:
                        service_codes = [s.get('code', '') for s in services if s.get('code')]
                        if service_codes:
                            services_info = f"%(new_line)s🔧 %(bold_start)sСервисы:%(bold_end)s {', '.join(service_codes)}"
                except:
                    pass
            
            msg = _(
                "%(bold_start)s%(title)s%(bold_end)s%(new_line)s"
                "%(new_line)s📋 %(bold_start)sВалидация:%(bold_end)s%(new_line)s"
                "%(tab)s%(valid_display)s%(new_line)s"
                "%(tab)s%(active_display)s%(new_line)s"
                "%(tab)s🌐 %(bold_start)sСеть SWIFT:%(bold_end)s %(network_display)s%(new_line)s"
                "%(tab)s📊 %(bold_start)sИсточник:%(bold_end)s %(source_display)s%(new_line)s"
                "%(new_line)s🏦 %(bold_start)sИнформация о банке:%(bold_end)s%(new_line)s"
                "%(tab)s🏪 %(bold_start)sБанк:%(bold_end)s %(bank_name)s%(new_line)s"
                "%(tab)s🌍 %(bold_start)sСтрана:%(bold_end)s %(country_name)s (%(country_code)s)%(new_line)s"
                "%(tab)s🏙️ %(bold_start)sГород:%(bold_end)s %(city)s%(new_line)s"
                "%(tab)s📍 %(bold_start)sАдрес:%(bold_end)s %(address)s%(new_line)s"
                "%(tab)s📊 %(bold_start)sСтатус:%(bold_end)s %(status)s%(services_info)s",
                bold_start=Markup("<b>"),
                bold_end=Markup("</b>"),
                new_line=Markup("<br>"),
                tab=Markup("&nbsp;&nbsp;&nbsp;&nbsp;"),
                title=title_text,
                valid_display=valid_display,
                active_display=active_display,
                network_display=network_display,
                source_display=source_display,
                bank_name=swift_info.get('bank_name', 'N/A'),
                country_name=swift_info.get('country_name', 'N/A'),
                country_code=swift_info.get('country_code', 'N/A'),
                city=swift_info.get('city', 'N/A'),
                address=swift_info.get('address', 'N/A'),
                status=status_display,
                services_info=Markup(services_info)
            )
            
            # Если указан номер заявки, обновляем ее
            if application_number:
                try:
                    application_number = int(application_number)
                    application = self.env['amanat.zayavka'].search([
                        ('id', '=', application_number)
                    ], limit=1)
                    
                    if application:
                        # Обновляем SWIFT информацию в заявке
                        actual_bic = swift_info.get('bic_code', identifier) if is_uetr else identifier
                        getattr(application, 'update_swift_from_bot', lambda x, y: None)(actual_bic, swift_info)
                        
                        msg += _(
                            "%(new_line)s%(new_line)s%(check_icon)s %(bold_start)sЗаявка #%(app_number)s обновлена SWIFT информацией.%(bold_end)s",
                            new_line=Markup("<br>"),
                            check_icon=Markup("✅"),
                            bold_start=Markup("<b>"),
                            bold_end=Markup("</b>"),
                            app_number=application_number,
                        )
                    else:
                        msg += _(
                            "%(new_line)s%(new_line)s%(warning_icon)s %(bold_start)sЗаявка #%(app_number)s не найдена.%(bold_end)s",
                            new_line=Markup("<br>"),
                            warning_icon=Markup("⚠️"),
                            bold_start=Markup("<b>"),
                            bold_end=Markup("</b>"),
                            app_number=application_number,
                        )
                except ValueError:
                    msg += _(
                        "%(new_line)s%(new_line)s%(error_icon)s %(bold_start)sНеверный формат номера заявки.%(bold_end)s",
                        new_line=Markup("<br>"),
                        error_icon=Markup("❌"),
                        bold_start=Markup("<b>"),
                        bold_end=Markup("</b>"),
                    )
            
            getattr(self.env.user, '_bus_send_transient_message', lambda x, y: None)(self, msg)
            
        except Exception as e:
            msg = _(
                "%(error_icon)s %(bold_start)sОшибка получения SWIFT информации:%(bold_end)s %(error_msg)s",
                error_icon=Markup("❌"),
                bold_start=Markup("<b>"),
                bold_end=Markup("</b>"),
                error_msg=str(e),
            )
            getattr(self.env.user, '_bus_send_transient_message', lambda x, y: None)(self, msg) 

    def _get_swift_tracking_status(self, identifier, identifier_type):
        """Получение статуса SWIFT перевода через реальный Swift GPI API"""
        try:
            # Получаем конфигурацию API
            config_model = self.env['amanat.swift.api.config']
            api_config = config_model.get_active_config()
            
            # Создаем клиент API
            from .swift_gpi_client import SwiftGpiClient
            client = SwiftGpiClient(api_config)
            
            # Для reference номеров пытаемся найти соответствующий UETR
            if identifier_type == 'reference':
                # Поиск UETR по reference в базе данных
                zayavka = self.env['amanat.zayavka'].search([
                    '|',
                    ('swift_transaction_ref', '=', identifier),
                    ('name', '=', identifier)
                ], limit=1)
                
                if zayavka and zayavka.swift_uetr:
                    identifier = zayavka.swift_uetr
                    identifier_type = 'uetr'
                else:
                    return {
                        'error': True,
                        'status': 'not_found',
                        'status_description': f'Не найден UETR для reference {identifier}',
                        'identifier': identifier,
                        'identifier_type': identifier_type
                    }
            
            # Валидация UETR формата
            if identifier_type == 'uetr':
                if len(identifier.replace('-', '')) != 32:
                    return {
                        'error': True,
                        'status': 'invalid_format', 
                        'status_description': f'Неверный формат UETR: {identifier}',
                        'identifier': identifier,
                        'identifier_type': identifier_type
                    }
            
            # Получаем статус через API
            status_result = client.get_payment_status(identifier)
            
            if 'error' in status_result:
                return {
                    'error': True,
                    'status': status_result.get('status', 'api_error'),
                    'status_description': status_result.get('message', 'Ошибка API'),
                    'identifier': identifier,
                    'identifier_type': identifier_type,
                    'error_type': status_result.get('error', 'unknown')
                }
            
            # Получаем детальную информацию отслеживания
            tracking_result = client.get_payment_tracking(identifier)
            
            # Формируем единый ответ
            result = {
                'transaction_type': 'swift_transfer',
                'identifier': identifier,
                'identifier_type': identifier_type,
                'status': status_result.get('status', 'unknown').lower(),
                'status_description': status_result.get('status_description', 'Неизвестный статус'),
                'gpi_reason_code': status_result.get('reason_code', ''),
                'gpi_reason_description': status_result.get('reason_description', ''),
                'progress_percentage': 0,
                'last_update': status_result.get('timestamp', ''),
                'forward_bank_name': status_result.get('forward_bank_name', ''),
                'forward_bank_code': status_result.get('forward_bank_code', ''),
                'details': status_result.get('details', ''),
                'route_info': '',
                'route_steps': []
            }
            
            # Добавляем информацию о маршруте если доступна
            if 'error' not in tracking_result:
                route_steps = tracking_result.get('route', [])
                result['route_steps'] = route_steps
                
                # Строим строку маршрута
                if route_steps:
                    route_parts = []
                    for step in route_steps:
                        bank_code = step.get('bank_code', '')
                        if bank_code:
                            route_parts.append(bank_code)
                    result['route_info'] = ' → '.join(route_parts)
                
                # Вычисляем прогресс
                total_steps = tracking_result.get('total_steps', 0)
                completed_steps = tracking_result.get('completed_steps', 0)
                
                if total_steps > 0:
                    result['progress_percentage'] = int((completed_steps / total_steps) * 100)
                else:
                    # Устанавливаем прогресс на основе статуса
                    status_progress = {
                        'completed': 100,
                        'processing': 75,
                        'forwarded': 60,
                        'pending_credit': 80,
                        'rejected': 0,
                        'failed': 0
                    }
                    result['progress_percentage'] = status_progress.get(result['status'], 50)
            
            return result
            
        except Exception as e:
            _logger.error(f"Ошибка при получении статуса SWIFT через API: {str(e)}")
            return {
                'error': True,
                'status': 'api_error',
                'status_description': f'Ошибка подключения к Swift GPI API: {str(e)}',
                'identifier': identifier,
                'identifier_type': identifier_type
            }

    def _format_swift_tracking_response(self, tracking_info):
        """Форматирование ответа для отслеживания SWIFT перевода"""
        if not tracking_info:
            return None
            
        # Проверяем ошибки
        if tracking_info.get('error'):
            error_emojis = {
                'not_found': '🔍',
                'invalid_format': '⚠️',
                'api_error': '🔌',
                'network_error': '🌐',
                'unknown': '❓'
            }
            
            error_type = tracking_info.get('error_type', 'unknown')
            emoji = error_emojis.get(error_type, '❌')
            
            msg_parts = []
            msg_parts.append(f"{emoji} **Ошибка отслеживания SWIFT перевода**")
            
            if tracking_info.get('identifier_type') == 'uetr':
                msg_parts.append(f"🔍 UETR: `{tracking_info.get('identifier', 'N/A')}`")
            else:
                msg_parts.append(f"🔍 Reference: `{tracking_info.get('identifier', 'N/A')}`")
            
            msg_parts.append(f"📝 **Описание:** {tracking_info.get('status_description', 'Неизвестная ошибка')}")
            
            # Инструкции по устранению
            if error_type == 'not_found':
                msg_parts.append("💡 **Совет:** Убедитесь что UETR или номер перевода правильный")
            elif error_type == 'invalid_format':
                msg_parts.append("💡 **Совет:** UETR должен быть в формате UUID (36 символов с дефисами)")
            elif error_type == 'api_error':
                msg_parts.append("💡 **Совет:** Проверьте настройки API в меню SWIFT → Настройки API")
            
            return "<br>".join(msg_parts)
            
        # Эмодзи для статусов
        status_emoji = {
            'initiated': '🟦',
            'sent_to_bank': '🟨', 
            'processing': '🟧',
            'forwarded': '🟪',
            'pending_credit': '🟩',
            'completed': '✅',
            'rejected': '❌',
            'failed': '❌',
            'returned': '🔄',
            'cancelled': '⛔',
            'unknown': '❓'
        }
        
        status = tracking_info.get('status', 'unknown')
        emoji = status_emoji.get(status, '⚪')
        
        # Формируем сообщение
        msg_parts = []
        
        # Заголовок
        if tracking_info.get('identifier_type') == 'uetr':
            msg_parts.append(f"📍 **Отслеживание SWIFT перевода**")
            msg_parts.append(f"🔍 UETR: `{tracking_info.get('identifier', 'N/A')[:8]}...`")
        else:
            msg_parts.append(f"📍 **Статус SWIFT перевода**")
            msg_parts.append(f"🔍 Reference: `{tracking_info.get('identifier', 'N/A')}`")
        
        # Статус
        msg_parts.append(f"{emoji} **Статус:** {tracking_info.get('status_description', 'Неизвестно')}")
        
        # GPI код причины
        if tracking_info.get('gpi_reason_code'):
            gpi_description = tracking_info.get('gpi_reason_description', '')
            if gpi_description:
                msg_parts.append(f"🔧 **GPI:** {tracking_info.get('gpi_reason_code')} - {gpi_description}")
            else:
                msg_parts.append(f"🔧 **GPI код:** {tracking_info.get('gpi_reason_code')}")
        
        # Прогресс
        progress = tracking_info.get('progress_percentage', 0)
        progress_bar = "▓" * (progress // 10) + "░" * ((100 - progress) // 10)
        msg_parts.append(f"📊 **Прогресс:** {progress}% [{progress_bar}]")
        
        # Дополнительные детали
        if tracking_info.get('details'):
            msg_parts.append(f"📝 **Детали:** {tracking_info.get('details')}")
        
        # Текущий банк
        if tracking_info.get('forward_bank_name') and tracking_info.get('forward_bank_code'):
            msg_parts.append(f"🏦 **Текущий банк:** {tracking_info.get('forward_bank_name')} ({tracking_info.get('forward_bank_code')})")
        elif tracking_info.get('forward_bank_code'):
            msg_parts.append(f"🏦 **Текущий банк:** {tracking_info.get('forward_bank_code')}")
        
        # Маршрут
        if tracking_info.get('route_info'):
            msg_parts.append(f"🗺️ **Маршрут:** {tracking_info.get('route_info')}")
        
        # Детальный маршрут если есть
        route_steps = tracking_info.get('route_steps', [])
        if route_steps and len(route_steps) > 1:
            msg_parts.append(f"📍 **Детальный маршрут:**")
            for step in route_steps:
                step_emoji = '✅' if step.get('status') == 'ACCC' else '🟧' if step.get('status') == 'ACSP' else '⚪'
                bank_name = step.get('bank_name', step.get('bank_code', f"Шаг {step.get('step', '?')}"))
                timestamp = step.get('timestamp', '')
                if timestamp:
                    msg_parts.append(f"  {step_emoji} {bank_name} ({timestamp})")
                else:
                    msg_parts.append(f"  {step_emoji} {bank_name}")
        
        # Временные метки
        if tracking_info.get('last_update'):
            update_time = tracking_info.get('last_update')
            # Если это строка, выводим как есть, если datetime - форматируем
            if hasattr(update_time, 'strftime'):
                msg_parts.append(f"🕐 **Последнее обновление:** {update_time.strftime('%d.%m.%Y %H:%M')}")
            else:
                msg_parts.append(f"🕐 **Последнее обновление:** {update_time}")
        
        return "<br>".join(msg_parts) 
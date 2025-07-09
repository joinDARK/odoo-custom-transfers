from odoo import models, _
from markupsafe import Markup
import re
import logging

_logger = logging.getLogger(__name__)


class MailBotExtension(models.AbstractModel):
    _inherit = 'mail.bot'

    def _get_answer(self, record, body, values, command=False):
        """Переопределение метода для добавления команды swift"""
        
        # Проверяем команду swift
        if command == 'swift' or 'swift' in body.lower():
            return self._handle_swift_command(record, body, values)
        
        # Если не наша команда, используем родительскую логику
        try:
            parent_method = getattr(super(MailBotExtension, self), '_get_answer', None)
            if parent_method:
                return parent_method(record, body, values, command)
        except Exception:
            pass
        
        return False

    def _handle_swift_command(self, record, body, values):
        """Обработка команды swift"""
        _logger.info(f"Handling SWIFT command: {body}")
        
        # Извлекаем SWIFT код из сообщения
        swift_code = self._extract_swift_code(body)
        
        if not swift_code:
            return self._get_swift_help_message()
        
        # Получаем информацию по SWIFT коду
        swift_info = self._get_swift_info(swift_code)
        
        if swift_info:
            # Создаем или обновляем запись в заявках если пользователь указал
            self._maybe_create_zayavka_swift(record, swift_info, values)
            return self._format_swift_response(swift_info)
        else:
            return self._get_swift_error_message(swift_code)

    def _extract_swift_code(self, body):
        """Извлечение SWIFT кода из текста сообщения"""
        # Убираем HTML теги и лишние символы
        clean_body = re.sub(r'<[^>]+>', '', body)
        
        # Паттерн для SWIFT кода (8 или 11 символов)
        swift_pattern = r'\b[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?\b'
        
        matches = re.findall(swift_pattern, clean_body.upper())
        
        if matches:
            # Возвращаем первый найденный код
            return matches[0] if isinstance(matches[0], str) else ''.join(matches[0])
        
        # Попробуем найти любую последовательность из 8-11 символов
        general_pattern = r'\b[A-Z0-9]{8,11}\b'
        matches = re.findall(general_pattern, clean_body.upper())
        
        if matches:
            # Проверяем что это похоже на SWIFT код
            for match in matches:
                if len(match) in [8, 11] and match[:4].isalpha() and match[4:6].isalpha():
                    return match
        
        return None

    def _get_swift_info(self, swift_code):
        """Получение информации по SWIFT коду"""
        try:
            SwiftModel = self.env['amanat.swift']
            
            # Ищем существующую запись
            swift_record = SwiftModel.search([('bic_code', '=', swift_code)], limit=1)
            
            if not swift_record:
                # Создаем новую запись (автоматически получит данные через API)
                swift_record = SwiftModel.create([{'bic_code': swift_code}])
            
            return {
                'bic_code': getattr(swift_record, 'bic_code', ''),
                'bank_name': getattr(swift_record, 'bank_name', ''),
                'bank_name_short': getattr(swift_record, 'bank_name_short', ''),
                'country_code': getattr(swift_record, 'country_code', ''),
                'country_name': getattr(swift_record, 'country_name', ''),
                'city': getattr(swift_record, 'city', ''),
                'address': getattr(swift_record, 'address', ''),
                'branch_code': getattr(swift_record, 'branch_code', ''),
                'swift_network': getattr(swift_record, 'swift_network', False),
                'record_id': swift_record.id,
                'last_updated': getattr(swift_record, 'last_updated', None)
            }
            
        except Exception as e:
            _logger.error(f"Error getting SWIFT info for {swift_code}: {str(e)}")
            return None

    def _format_swift_response(self, swift_info):
        """Форматирование ответа с информацией по SWIFT"""
        style_dict = self._get_style_dict()
        
        response_parts = []
        
        # Заголовок
        response_parts.append(
            f"{style_dict['bold_start']}SWIFT Информация{style_dict['bold_end']}"
        )
        
        # BIC код
        response_parts.append(
            f"{style_dict['command_start']}BIC/SWIFT:{style_dict['command_end']} {swift_info['bic_code']}"
        )
        
        # Название банка
        if swift_info.get('bank_name'):
            response_parts.append(
                f"{style_dict['command_start']}Банк:{style_dict['command_end']} {swift_info['bank_name']}"
            )
        elif swift_info.get('bank_name_short'):
            response_parts.append(
                f"{style_dict['command_start']}Банк:{style_dict['command_end']} {swift_info['bank_name_short']}"
            )
        
        # Страна
        if swift_info.get('country_name'):
            country_info = swift_info['country_name']
            if swift_info.get('country_code'):
                country_info += f" ({swift_info['country_code']})"
            response_parts.append(
                f"{style_dict['command_start']}Страна:{style_dict['command_end']} {country_info}"
            )
        
        # Город
        if swift_info.get('city'):
            response_parts.append(
                f"{style_dict['command_start']}Город:{style_dict['command_end']} {swift_info['city']}"
            )
        
        # Адрес
        if swift_info.get('address') and swift_info['address'] != 'Address not available':
            response_parts.append(
                f"{style_dict['command_start']}Адрес:{style_dict['command_end']} {swift_info['address']}"
            )
        
        # Код филиала
        if swift_info.get('branch_code') and swift_info['branch_code'] != 'XXX':
            response_parts.append(
                f"{style_dict['command_start']}Филиал:{style_dict['command_end']} {swift_info['branch_code']}"
            )
        
        # SWIFT сеть
        if swift_info.get('swift_network'):
            response_parts.append(
                f"{style_dict['command_start']}SWIFT сеть:{style_dict['command_end']} ✅ Подключен"
            )
        else:
            response_parts.append(
                f"{style_dict['command_start']}SWIFT сеть:{style_dict['command_end']} ❌ Не подключен"
            )
        
        # Последнее обновление
        if swift_info.get('last_updated'):
            response_parts.append(
                f"{style_dict['command_start']}Обновлено:{style_dict['command_end']} {swift_info['last_updated']}"
            )
        
        # Инструкция по добавлению в заявку
        response_parts.append(
            f"{style_dict['new_line']}{style_dict['command_start']}Совет:{style_dict['command_end']} "
            f"Чтобы добавить этот SWIFT в заявку, напишите: {style_dict['command_start']}swift {swift_info['bic_code']} заявка НОМЕР{style_dict['command_end']}"
        )
        
        return Markup(style_dict['new_line'].join(response_parts))

    def _get_swift_help_message(self):
        """Сообщение с помощью по команде swift"""
        style_dict = self._get_style_dict()
        
        help_parts = [
            f"{style_dict['bold_start']}SWIFT Команда{style_dict['bold_end']}",
            f"Для получения информации по SWIFT коду используйте:",
            f"{style_dict['command_start']}/swift DEUTDEFFXXX{style_dict['command_end']} - поиск по коду",
            f"{style_dict['command_start']}swift SBZAINBBXXX{style_dict['command_end']} - можно без слэша",
            f"{style_dict['command_start']}swift DEUTDEFFXXX заявка 123{style_dict['command_end']} - добавить в заявку",
            f"{style_dict['new_line']}SWIFT код должен содержать 8 или 11 символов.",
            f"Пример: {style_dict['command_start']}DEUTDEFFXXX{style_dict['command_end']} (Deutsche Bank)"
        ]
        
        return Markup(style_dict['new_line'].join(help_parts))

    def _get_swift_error_message(self, swift_code):
        """Сообщение об ошибке при получении SWIFT информации"""
        style_dict = self._get_style_dict()
        
        error_parts = [
            f"{style_dict['bold_start']}Ошибка SWIFT{style_dict['bold_end']}",
            f"Не удалось получить информацию по коду: {style_dict['command_start']}{swift_code}{style_dict['command_end']}",
            f"{style_dict['new_line']}Возможные причины:",
            f"• Неверный формат кода",
            f"• Код не существует",
            f"• Проблема с API сервисом",
            f"{style_dict['new_line']}Попробуйте еще раз или обратитесь к администратору."
        ]
        
        return Markup(style_dict['new_line'].join(error_parts))

    def _maybe_create_zayavka_swift(self, record, swift_info, values):
        """Создание или обновление заявки с SWIFT информацией"""
        try:
            # Проверяем есть ли в сообщении упоминание заявки
            body = values.get('body', '').lower()
            
            # Паттерн для поиска номера заявки
            zayavka_patterns = [
                r'заявка\s+(\d+)',
                r'заявку\s+(\d+)',
                r'заявке\s+(\d+)',
                r'зaявка\s+(\d+)',  # с латинской 'a'
                r'№\s*(\d+)',
                r'номер\s+(\d+)'
            ]
            
            zayavka_number = None
            for pattern in zayavka_patterns:
                match = re.search(pattern, body)
                if match:
                    zayavka_number = match.group(1)
                    break
            
            if not zayavka_number:
                return
            
            # Ищем заявку по номеру
            zayavka = self.env['amanat.zayavka'].search([
                ('zayavka_num', '=', zayavka_number)
            ], limit=1)
            
            if not zayavka:
                # Пробуем найти по ID
                try:
                    zayavka_id = int(zayavka_number)
                    zayavka = self.env['amanat.zayavka'].browse(zayavka_id)
                    if not zayavka.exists():
                        return
                except (ValueError, TypeError):
                    return
            
            # Обновляем заявку
            swift_record = self.env['amanat.swift'].browse(swift_info['record_id'])
            zayavka.write({
                'swift_id': swift_record.id,
                'swift_code': swift_info['bic_code'],
                'swift_bank_name': swift_info.get('bank_name') or swift_info.get('bank_name_short'),
                'swift_country': swift_info.get('country_name'),
                'swift_city': swift_info.get('city'),
                'swift_received_date': self.env.context.get('swift_received_date') or False
            })
            
            # Добавляем сообщение в заявку
            zayavka.message_post(
                body=f"SWIFT информация обновлена через бот: {swift_info['bic_code']} - {swift_info.get('bank_name', 'Unknown Bank')}"
            )
            
            _logger.info(f"Updated zayavka {zayavka.id} with SWIFT info {swift_info['bic_code']}")
            
        except Exception as e:
            _logger.error(f"Error updating zayavka with SWIFT info: {str(e)}")

    def _is_swift_command(self, body):
        """Проверка является ли сообщение командой swift"""
        body_lower = body.lower().strip()
        
        # Проверяем начинается ли с команды swift
        if body_lower.startswith('/swift') or body_lower.startswith('swift'):
            return True
        
        # Проверяем содержит ли слово swift
        if 'swift' in body_lower:
            return True
        
        # Проверяем есть ли в тексте SWIFT код
        swift_pattern = r'\b[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?\b'
        if re.search(swift_pattern, body.upper()):
            return True
        
        return False 
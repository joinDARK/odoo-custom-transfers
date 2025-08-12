# models/base_model.py
from odoo import models, api, fields
from odoo.tools import html_escape
import logging
import json

_logger = logging.getLogger(__name__)

class AmanatBaseModel(models.AbstractModel):
    _name = 'amanat.base.model'
    _description = 'Base Model for Logging and Real-time Updates'

    def open_form(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    def open_form_new_tab(self):
        """Открыть форму в новой вкладке браузера"""
        # Формируем URL для открытия формы
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = f"{base_url}/web#id={self.id}&view_type=form&model={self._name}"
        
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',  # Открывает в новом окне/вкладке браузера
        }

    def open_form_modal(self):
        """Открыть форму в модальном окне"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',  # Открывает в модальном окне
            'name': f'{self.display_name}',
        }

    def open_form_new_tab_js(self):
        """Альтернативный метод открытия формы в новой вкладке через JavaScript"""
        return {
            'type': 'ir.actions.client',
            'tag': 'open_form_new_tab',
            'params': {
                'model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
            }
        }

    def _should_log(self):
        """Проверяем, нужно ли логировать операцию"""
        return (
            not self.env.context.get('no_log') and 
            self._name != 'amanat.activity' and
            'amanat.activity' in self.env.registry
        )

    def _get_realtime_fields(self):
        """Переопределите этот метод в наследуемых моделях для указания полей для real-time обновлений"""
        # Базовые поля для всех моделей
        basic_fields = ['id', 'display_name', 'create_date', 'write_date']
        
        # Добавляем общие поля если они есть
        common_fields = ['name', 'state', 'active', 'date', 'amount', 'currency']
        for field in common_fields:
            if field in self._fields:
                basic_fields.append(field)
        
        # Добавляем поля отслеживания (tracking=True)
        for field_name, field in self._fields.items():
            if hasattr(field, 'tracking') and field.tracking and field_name not in basic_fields:
                basic_fields.append(field_name)
        
        return basic_fields

    def _get_record_data_for_realtime(self, record):
        """Получаем данные записи для real-time обновлений"""
        try:
            # Получаем поля для чтения
            fields_to_read = record._get_realtime_fields()
            
            # Убираем дубликаты
            fields_to_read = list(set(fields_to_read))
            
            # Читаем данные
            data = record.read(fields_to_read)[0] if record.exists() else {}
            
            # Преобразуем Many2one поля в читаемый формат
            for field_name, field in record._fields.items():
                if field_name in data and field.type == 'many2one' and data[field_name]:
                    if isinstance(data[field_name], (list, tuple)) and len(data[field_name]) == 2:
                        data[field_name] = {
                            'id': data[field_name][0],
                            'display_name': data[field_name][1]
                        }
            
            return data
        except Exception as e:
            _logger.error(f"Ошибка при получении данных записи для real-time: {e}")
            return {'id': record.id, 'display_name': record.display_name}

    def _send_realtime_notification(self, action, changed_fields=None):
        """Отправляем real-time уведомление с детальной информацией"""
        # try:
            # _logger.info(f"🔥 _send_realtime_notification called: action={action}, model={self._name}, records={len(self)}")
            # _logger.info(f"🔥 Changed fields: {changed_fields}")
            
            # Используем новый метод из res.users
            # self.env.user.notify_record_change(action, self, changed_fields)
            
            # _logger.info("🔥 notify_record_change completed successfully")
            
        # except Exception as e:
        #     _logger.error(f"❌ Ошибка при отправке real-time уведомления: {e}")
        #     import traceback
        #     _logger.error(f"❌ Traceback: {traceback.format_exc()}")

    def _log_activity(self, action, changes=None):
        if not self._should_log():
            return
        
        try:
            for record in self:
                data = {
                    'name': record.display_name,
                    'model': record._name,
                    'id': record.id,
                }

                # Создаем запись лога с контекстом no_log
                self.env['amanat.activity'].with_context(no_log=True).sudo().create({
                    'action': action,
                    'model_name': record._name,
                    'record_id': record.id,
                    'record_name': record.display_name,
                    'user_id': self.env.uid,
                    'changes': changes,
                    'data': html_escape(str(data)),
                })
        except Exception as e:
            _logger.error(f"Ошибка при логировании: {e}")

    @api.model_create_multi
    def create(self, vals_list):
        user = self.env.user
        
        for vals in vals_list:
            if user.has_group('amanat.group_amanat_manager'):
                # Для модели заявки используем manager_ids (Many2many)
                if self._name == 'amanat.zayavka' and 'manager_ids' in self._fields:
                    # Находим или создаем менеджера для текущего пользователя
                    manager = self.env['amanat.manager'].find_or_create_manager(user.id)
                    
                    if manager:
                        vals['manager_ids'] = [(4, manager.id)]  # Добавляем в Many2many
                        _logger.info(f"Назначен менеджер {manager.name} (ID: {manager.id}) для заявки")
                    else:
                        _logger.warning(f"Не удалось назначить менеджера для пользователя {user.name}")
                
                # Для других моделей используем manager_id (Many2one)
                elif 'manager_id' in self._fields:
                    vals['manager_id'] = user.id
        
        records = super().create(vals_list)
        
        # Логируем создание только если это не логи
        if self._should_log():
            for record in records:
                record._log_activity('create')
        
        # Отправляем real-time уведомление для всех записей
        if records:
            records._send_realtime_notification('create')
        
        return records

    def write(self, vals):
        # _logger.info(f"🔥 BASE_MODEL WRITE CALLED: model={self._name}, vals={vals}")
        # _logger.info(f"🔥 Records count: {len(self)}")
        
        changed_fields = list(vals.keys())
        
        # Сохраняем старые значения для логирования
        old_values = {}
        if self._should_log():
            for record in self:
                old_values[record.id] = {}
                for field in changed_fields:
                    old_values[record.id][field] = getattr(record, field, None)
        
        # Применяем изменения
        result = super().write(vals)
        
        # Логируем изменения
        if self._should_log():
            for record in self:
                if record.id in old_values:
                    changes = []
                    for field, new_value in vals.items():
                        old_value = old_values[record.id].get(field)
                        if field in record._fields:
                            # Для Many2one полей показываем имена
                            if record._fields[field].type == 'many2one':
                                old_display = old_value.display_name if old_value else 'Не задано'
                                new_display = getattr(record, field).display_name if getattr(record, field) else 'Не задано'
                                changes.append(f"{field}: {old_display} → {new_display}")
                            else:
                                changes.append(f"{field}: {old_value} → {new_value}")
                    
                    if changes:
                        record._log_activity('update', "\n".join(changes))
        
        # Отправляем real-time уведомление
        if self.exists():
            self._send_realtime_notification('update', changed_fields=changed_fields)
        
        return result

    def unlink(self):
        # Сохраняем данные для логирования и уведомления перед удалением
        log_data = []
        records_for_notification = self
        
        if self._should_log():
            for record in self:
                data = {
                    'name': record.display_name,
                    'model': record._name,
                    'id': record.id,
                }
                log_data.append(data)
        
        # Удаляем записи
        result = super().unlink()
        
        # Логируем удаление
        if self._should_log() and log_data:
            try:
                for data in log_data:
                    self.env['amanat.activity'].with_context(no_log=True).sudo().create({
                        'action': 'delete',
                        'model_name': data['model'],
                        'record_id': data['id'],
                        'record_name': data['name'],
                        'data': html_escape(str(data)),
                        'user_id': self.env.uid,
                    })
            except Exception as e:
                _logger.error(f"Ошибка при логировании удаления: {e}")
        
        # Отправляем real-time уведомление об удалении
        # try:
        #     self.env.user.notify_record_change('delete', records_for_notification, None)
        # except Exception as e:
        #     _logger.error(f"Ошибка при отправке уведомления об удалении: {e}")
        
        return result
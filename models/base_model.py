# models/base_model.py
from odoo import models, api
from odoo.tools import html_escape
import logging

_logger = logging.getLogger(__name__)

class AmanatBaseModel(models.AbstractModel):
    _name = 'amanat.base.model'
    _description = 'Base Model for Logging'

    def open_form(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    def _should_log(self):
        """Проверяем, нужно ли логировать операцию"""
        return (
            not self.env.context.get('no_log') and 
            self._name != 'amanat.activity' and
            'amanat.activity' in self.env.registry
        )

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
                vals['manager_id'] = user.id
        
        records = super().create(vals_list)
        
        # Логируем создание только если это не логи
        if self._should_log():
            for record in records:
                record._log_activity('create')
        
        try:
            self.env.user._bus_send("realtime_updates", {
                'type': 'create', 
                'model': records._name, 
                'ids': records.ids, 
                'user_id': user.id
            })
        except:
            pass  # Игнорируем ошибки отправки уведомлений
        
        return records

    def write(self, vals):
        if not self._should_log():
            return super().write(vals)
            
        user = self.env.user
        
        for record in self:
            # Подготавливаем изменения для лога
            changes = []
            for field, value in vals.items():
                old_value = getattr(record, field, None)
                changes.append(f"{field}: {old_value} → {value}")
            
            # Применяем изменения
            super(AmanatBaseModel, record).write(vals)
            
            # Логируем изменения
            record._log_activity('update', "\n".join(changes))
        
        try:
            self.env.user._bus_send("realtime_updates", {
                'type': 'update', 
                'model': self._name, 
                'ids': self.ids, 
                'user_id': user.id
            })
        except:
            pass
        
        return True

    def unlink(self):
        # Если это логи - просто удаляем без логирования
        if not self._should_log():
            return super().unlink()
            
        user = self.env.user
        
        # Собираем данные для лога перед удалением
        log_data = []
        for record in self:
            data = {
                'name': record.display_name,
                'model': record._name,
                'id': record.id,
            }
            log_data.append(data)
        
        # Сохраняем IDs для уведомления
        record_ids = self.ids
        model_name = self._name
        
        # Удаляем записи
        result = super().unlink()
        
        # Логируем удаление
        if log_data:
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
        
        # Отправляем уведомление
        try:
            if record_ids:
                self.env.user._bus_send("realtime_updates", {
                    'type': 'delete',
                    'model': model_name,
                    'ids': record_ids,
                    'user_id': user.id
                })
        except:
            pass
        
        return result
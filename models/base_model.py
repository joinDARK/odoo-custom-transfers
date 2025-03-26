# models/base_model.py
from odoo import models, api, fields
from odoo.tools import html_escape

class AmanatBaseModel(models.AbstractModel):
    _name = 'amanat.base.model'
    _description = 'Base Model for Logging'

    def _log_activity(self, action, changes=None):
        if self.env.context.get('no_log'):
            return
        
        for record in self:
            # Собираем данные записи в зависимости от действия
            data = {}
            if action == 'delete':
                data = {
                    'name': record.display_name,
                    'model': record._name,
                    'id': record.id,
                    # Добавьте другие поля, которые нужно сохранить
                }
            else:
                data = {
                    'name': record.display_name,
                    'model': record._name,
                    'id': record.id,
                }

            self.env['amanat.activity'].sudo().create({
                'action': action,
                'model_name': record._name,
                'record_id': record.id,
                'record_name': record.display_name,  # Сохраняем название до удаления
                'user_id': self.env.uid,
                'changes': changes,
                'data': html_escape(str(data)),  # Экранируем данные для безопасности
            })

    @api.model_create_multi
    def create(self, vals_list):
        print("executed model_create_multi")
        user = self.env.user
        print(f"Current user: {user.name}, Groups: {user.groups_id.mapped('name')}")
        
        for vals in vals_list:
            if user.has_group('amanat.group_amanat_manager'):
                print("user.id manager exist")
                vals['manager_id'] = user.id  # Менеджер автоматически назначается
            else:
                print("user.id manager doesnt exist")
        
        return super().create(vals_list)

    def write(self, vals):
        # Исправление: перебор записей для корректного логгирования
        for record in self:
            changes = []
            for field, value in vals.items():
                old_value = getattr(record, field, None)
                changes.append(f"{field}: {old_value} → {value}")
            super(AmanatBaseModel, record).write(vals)
            record._log_activity('update', "\n".join(changes))
        return True

    def unlink(self):
        # Собираем данные для лога перед удалением
        log_data = []
        for record in self:
            data = {
                'name': record.display_name,
                'model': record._name,
                'id': record.id,
                # Добавьте другие поля, например:
                # 'field1': record.field1,
                # 'field2': record.field2,
            }
            log_data.append(data)
        
        # Вызываем unlink() и сохраняем результат
        result = super().unlink()
        
        # Логируем удаление с сохраненными данными
        for data in log_data:
            self.env['amanat.activity'].sudo().create({
                'action': 'delete',
                'model_name': data['model'],
                'record_id': data['id'],
                'record_name': data['name'],
                'data': html_escape(str(data)),
                'user_id': self.env.uid,
            })
        return result
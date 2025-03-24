# # models/base_model.py
# from odoo import models, api, fields
# from odoo.tools import html_escape

# class AmanatBaseModel(models.AbstractModel):
#     _name = 'amanat.base.model'
#     _description = 'Base Model for Logging'

#     def _log_activity(self, action, changes=None):
#         if self.env.context.get('no_log'):
#             return
        
#         for record in self:
#             # Собираем данные записи в зависимости от действия
#             data = {}
#             if action == 'delete':
#                 data = {
#                     'name': record.display_name,
#                     'model': record._name,
#                     'id': record.id,
#                     # Добавьте другие поля, которые нужно сохранить
#                 }
#             else:
#                 data = {
#                     'name': record.display_name,
#                     'model': record._name,
#                     'id': record.id,
#                 }

#             self.env['amanat.activity'].sudo().create({
#                 'action': action,
#                 'model_name': record._name,
#                 'record_id': record.id,
#                 'record_name': record.display_name,  # Сохраняем название до удаления
#                 'user_id': self.env.uid,
#                 'changes': changes,
#                 'data': html_escape(str(data)),  # Экранируем данные для безопасности
#             })

#     @api.model_create_multi
#     def create(self, vals_list):
#         print("executed model_create_multi")
#         user = self.env.user
#         print(f"Current user: {user.name}, Groups: {user.groups_id.mapped('name')}")
        
#         for vals in vals_list:
#             if user.has_group('amanat.group_amanat_manager'):
#                 print("user.id manager exist")
#                 vals['manager_id'] = user.id  # Менеджер автоматически назначается
#             else:
#                 print("user.id manager doesnt exist")
        
#         return super().create(vals_list)

#     def write(self, vals):
#         # Исправление: перебор записей для корректного логгирования
#         for record in self:
#             changes = []
#             for field, value in vals.items():
#                 old_value = getattr(record, field, None)
#                 changes.append(f"{field}: {old_value} → {value}")
#             super(AmanatBaseModel, record).write(vals)
#             record._log_activity('update', "\n".join(changes))
#         return True

#     def unlink(self):
#         # Собираем данные для лога перед удалением
#         log_data = []
#         for record in self:
#             data = {
#                 'name': record.display_name,
#                 'model': record._name,
#                 'id': record.id,
#                 # Добавьте другие поля, например:
#                 # 'field1': record.field1,
#                 # 'field2': record.field2,
#             }
#             log_data.append(data)
        
#         # Вызываем unlink() и сохраняем результат
#         result = super().unlink()
        
#         # Логируем удаление с сохраненными данными
#         for data in log_data:
#             self.env['amanat.activity'].sudo().create({
#                 'action': 'delete',
#                 'model_name': data['model'],
#                 'record_id': data['id'],
#                 'record_name': data['name'],
#                 'data': html_escape(str(data)),
#                 'user_id': self.env.uid,
#             })
#         return result
    
#     @api.model_create_multi
#     def create(self, vals_list):
#         records = super().create(vals_list)
#         for record in records:
#             self.env['amanat.automation'].execute_automation(record._name, record.id, 'on_create')
#         return records

#     def write(self, vals):
#         result = super().write(vals)
#         for record in self:
#             self.env['amanat.automation'].execute_automation(record._name, record.id, 'on_write')
#         return result

#     def unlink(self):
#         for record in self:
#             self.env['amanat.automation'].execute_automation(record._name, record.id, 'on_delete')
#         return super().unlink()






from odoo import models, api, fields
from odoo.tools import html_escape
import logging

_logger = logging.getLogger(__name__)

class AmanatBaseModel(models.AbstractModel):
    _name = 'amanat.base.model'
    _description = 'Base Model for Logging'

    def _log_activity(self, action, changes=None):
        if self.env.context.get('no_log'):
            return
        
        for record in self:
            data = {}
            if action == 'delete':
                data = {
                    'name': record.display_name,
                    'model': record._name,
                    'id': record.id,
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
                'record_name': record.display_name,  
                'user_id': self.env.uid,
                'changes': changes,
                'data': html_escape(str(data)), 
            })

    @api.model_create_multi
    def create(self, vals_list):
        print("executed model_create_multi")
        user = self.env.user
        print(f"Current user: {user.name}, Groups: {user.groups_id.mapped('name')}")
        
        for vals in vals_list:
            if user.has_group('amanat.group_amanat_manager'):
                print("user.id manager exist")
                vals['manager_id'] = user.id  
            else:
                print("user.id manager doesnt exist")

        records = super().create(vals_list)

        for record in records:
            record._log_activity('create')

        for record in records:
            self.env['amanat.automation'].execute_automation(record._name, record.id, 'on_create')

        return records

    def write(self, vals):
        for record in self:
            changes = []
            for field, value in vals.items():
                old_value = getattr(record, field, None)
                changes.append(f"{field}: {old_value} → {value}")
            record._log_activity('update', "\n".join(changes))

        result = super().write(vals)

        for record in self:
            self.env['amanat.automation'].execute_automation(record._name, record.id, 'on_write')

        return result

    def unlink(self):
        log_data = []
        for record in self:
            data = {
                'name': record.display_name,
                'model': record._name,
                'id': record.id,
            }
            log_data.append(data)

        for record in self:
            self.env['amanat.automation'].execute_automation(record._name, record.id, 'on_delete')

        result = super().unlink()

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
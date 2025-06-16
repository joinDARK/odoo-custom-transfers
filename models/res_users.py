from odoo import models, fields, api


class ResUsers(models.Model):
    
    _inherit = 'res.users'
    
    #----------------------------------------------------------
    # Properties
    #----------------------------------------------------------
    
    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'sidebar_type',
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            'sidebar_type',
        ]

    #----------------------------------------------------------
    # Fields
    #----------------------------------------------------------
    
    sidebar_type = fields.Selection(
        selection=[
            ('invisible', 'Invisible'),
            ('small', 'Small'),
            ('large', 'Large')
        ], 
        string="Sidebar Type",
        default='large',
        required=True,
    )

    # #----------------------------------------------------------
    # # Real-time notification methods
    # #----------------------------------------------------------
    
    # def _get_interested_users(self, model=None):
    #     """Получить список пользователей, заинтересованных в real-time обновлениях"""
    #     try:
    #         # Получаем всех активных пользователей групп amanat
    #         amanat_group_ids = []
            
    #         # Пробуем найти различные группы amanat
    #         for group_xml_id in [
    #             'amanat.group_amanat_admin',
    #             'amanat.group_amanat_manager', 
    #             'amanat.group_amanat_senior_manager',
    #             'amanat.group_amanat_inspector'
    #         ]:
    #             try:
    #                 group = self.env.ref(group_xml_id)
    #                 if group:
    #                     amanat_group_ids.append(group.id)
    #             except:
    #                 continue
            
    #         if amanat_group_ids:
    #             amanat_users = self.env['res.users'].search([
    #                 ('active', '=', True),
    #                 ('groups_id', 'in', amanat_group_ids),
    #                 # Включаем всех пользователей для межбраузерной работы
    #             ])
    #         else:
    #             # Если групп amanat нет, берем всех активных пользователей
    #             amanat_users = self.env['res.users'].search([
    #                 ('active', '=', True),
    #                 # Включаем всех пользователей для межбраузерной работы
    #             ])
            
    #         return amanat_users
    #     except Exception as e:
    #         import logging
    #         _logger = logging.getLogger(__name__)
    #         _logger.error(f"Error getting interested users: {e}")
    #         # Fallback - возвращаем всех активных пользователей
    #         return self.env['res.users'].search([
    #             ('active', '=', True),
    #             # Включаем всех пользователей для межбраузерной работы
    #         ])

    # def _bus_send_to_user(self, user, message):
    #     """Отправка bus уведомления конкретному пользователю"""
    #     try:
    #         import logging
    #         _logger = logging.getLogger(__name__)
            
    #         # Формируем личный канал пользователя
    #         user_channel = f"res.users,{user.id}"
    #         _logger.info(f"Sending bus message to user channel {user_channel}: {message}")
            
    #         # Для Odoo 18 правильный API с тремя параметрами
    #         self.env['bus.bus']._sendone(user_channel, 'amanat_realtime_update', message)
            
    #         _logger.info(f"Bus message sent successfully to user {user.name}")
    #     except Exception as e:
    #         import logging
    #         _logger = logging.getLogger(__name__)
    #         _logger.error(f"Error sending bus message to user {user.name}: {e}")

    # def _send_realtime_notification(self, message_type, model, records_data, changed_fields=None):
    #     """Отправка структурированного real-time уведомления всем заинтересованным пользователям"""
    #     import logging
    #     _logger = logging.getLogger(__name__)
        
    #     try:
    #         _logger.info(f"🔔 _send_realtime_notification: type={message_type}, model={model}")
            
    #         notification_data = {
    #             'type': message_type,
    #             'model': model,
    #             'model_display_name': self.env[model]._description if model in self.env else model,
    #             'user_id': self.id,
    #             'user_name': self.name,
    #             'timestamp': fields.Datetime.now().isoformat(),
    #             'records': records_data,
    #             'changed_fields': changed_fields or []
    #         }
            
    #         _logger.info(f"📋 Notification data prepared: {notification_data}")
            
    #         # Получаем всех заинтересованных пользователей
    #         interested_users = self._get_interested_users(model)
            
    #         _logger.info(f"👥 Found {len(interested_users)} interested users for model {model}")
    #         _logger.info(f"👥 Interested users: {[u.name for u in interested_users]}")
            
    #         if not interested_users:
    #             _logger.warning("⚠️ No interested users found - notification will not be sent")
    #             return
            
    #         # Отправляем уведомление каждому заинтересованному пользователю
    #         for user in interested_users:
    #             _logger.info(f"📤 Sending notification to user: {user.name} (ID: {user.id})")
    #             self._bus_send_to_user(user, notification_data)
            
    #         _logger.info("✅ All notifications sent successfully")
            
    #     except Exception as e:
    #         _logger.error(f"❌ Error sending realtime notification: {e}")
    #         import traceback
    #         _logger.error(f"❌ Traceback: {traceback.format_exc()}")

    # def notify_record_change(self, action, records, changed_fields=None):
    #     """Уведомление об изменении записей"""
    #     import logging
    #     _logger = logging.getLogger(__name__)
        
    #     _logger.info(f"🚀 notify_record_change called: action={action}, records={len(records) if records else 0}")
        
    #     if not records:
    #         _logger.warning("⚠️ No records provided to notify_record_change")
    #         return
            
    #     # Подготавливаем данные записей
    #     records_data = []
    #     for record in records:
    #         try:
    #             record_data = {
    #                 'id': record.id,
    #                 'display_name': record.display_name
    #             }
                
    #             # Добавляем дополнительные поля для отображения
    #             if hasattr(record, '_get_realtime_fields'):
    #                 fields_to_read = record._get_realtime_fields()
    #             else:
    #                 # Стандартные поля
    #                 fields_to_read = ['name', 'state', 'create_date', 'write_date']
                
    #             _logger.info(f"🔍 Reading fields for record {record.id}: {fields_to_read}")
                
    #             for field_name in fields_to_read:
    #                 if field_name in record._fields and hasattr(record, field_name):
    #                     try:
    #                         value = getattr(record, field_name)
    #                         if field_name.endswith('_id') and hasattr(value, 'display_name'):
    #                             record_data[field_name] = {
    #                                 'id': value.id,
    #                                 'display_name': value.display_name
    #                             }
    #                         else:
    #                             record_data[field_name] = value
    #                     except:
    #                         continue
                
    #             records_data.append(record_data)
    #             _logger.info(f"✅ Prepared record data: {record_data}")
                
    #         except Exception as e:
    #             _logger.error(f"❌ Error preparing record data for {record}: {e}")
    #             continue
        
    #     if records_data:
    #         _logger.info(f"📤 Sending notification with {len(records_data)} records")
    #         self._send_realtime_notification(action, records._name, records_data, changed_fields)
    #     else:
    #         _logger.warning("⚠️ No records data prepared for notification")

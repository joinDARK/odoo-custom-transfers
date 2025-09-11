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

    #----------------------------------------------------------
    # Methods
    #----------------------------------------------------------
    
    @api.model
    def check_user_groups(self):
        """Проверка групп текущего пользователя для фильтрации меню"""
        user = self.env.user
        return {
            'is_manager': user.has_group('amanat.group_amanat_manager'),
            'is_senior_manager': user.has_group('amanat.group_amanat_senior_manager'),
            'is_fin_manager': user.has_group('amanat.group_amanat_fin_manager'),
            'is_fin_manager_jess': user.has_group('amanat.group_amanat_fin_manager_jess'),
            'is_director': user.has_group('amanat.group_amanat_director'),
            'is_admin': user.has_group('amanat.group_amanat_admin'),
            'is_inspector': user.has_group('amanat.group_amanat_inspector'),
            'is_transit_only': user.has_group('amanat.group_amanat_transit_only'),
            'is_treasurer': user.has_group('amanat.group_amanat_treasurer'),
            'is_dilara': user.name == 'Диляра',  # Добавляем проверку имени пользователя
            'user_name': user.name,  # Добавляем имя пользователя для отладки
            # Новые группы для аналитики
            'is_vera_findir': user.has_group('amanat.group_amanat_vera_findir'),
            'is_venera_analytics': user.has_group('amanat.group_amanat_venera_analytics'),
            'is_khalida_analytics': user.has_group('amanat.group_amanat_khalida_analytics'),
            'is_elina_manager': user.has_group('amanat.group_amanat_elina_manager_dashboard'),
            'is_alina_manager': user.has_group('amanat.group_amanat_alina_manager_files'),
        }

    def write(self, vals):
        """Автоматическое создание записи менеджера при назначении в группу"""
        res = super().write(vals)
        
        # Если изменяются группы пользователей
        if 'groups_id' in vals:
            for user in self:
                # Проверяем, стал ли пользователь менеджером или старшим менеджером
                if user.has_group('amanat.group_amanat_manager') or user.has_group('amanat.group_amanat_senior_manager'):
                    # Проверяем, есть ли уже запись менеджера для этого пользователя
                    existing_manager = self.env['amanat.manager'].search([('user_id', '=', user.id)], limit=1)
                    if not existing_manager:
                        try:
                            manager = self.env['amanat.manager'].create([{
                                'name': user.name,
                                'user_id': user.id,
                            }])
                            import logging
                            _logger = logging.getLogger(__name__)
                            _logger.info(f"Автоматически создан менеджер {manager.name} (ID: {manager.id}) для пользователя {user.name}")
                        except Exception as e:
                            import logging
                            _logger = logging.getLogger(__name__)
                            _logger.error(f"Ошибка при создании менеджера для пользователя {user.name}: {e}")
        
        return res

    #----------------------------------------------------------
    # Real-time notification methods
    #----------------------------------------------------------
    
    def _get_interested_users(self, model=None):
        """Получить список пользователей, заинтересованных в real-time обновлениях"""
        try:
            # Получаем всех активных пользователей групп amanat
            amanat_group_ids = []
            
            # Пробуем найти различные группы amanat
            for group_xml_id in [
                'amanat.group_amanat_admin',
                'amanat.group_amanat_manager', 
                'amanat.group_amanat_senior_manager',
                'amanat.group_amanat_inspector'
            ]:
                try:
                    group = self.env.ref(group_xml_id)
                    if group:
                        amanat_group_ids.append(group.id)
                except:
                    continue
            
            if amanat_group_ids:
                amanat_users = self.env['res.users'].search([
                    ('active', '=', True),
                    ('groups_id', 'in', amanat_group_ids),
                    # Включаем всех пользователей для межбраузерной работы
                ])
            else:
                # Если групп amanat нет, берем всех активных пользователей
                amanat_users = self.env['res.users'].search([
                    ('active', '=', True),
                    # Включаем всех пользователей для межбраузерной работы
                ])
            
            return amanat_users
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Error getting interested users: {e}")
            # Fallback - возвращаем всех активных пользователей
            return self.env['res.users'].search([
                ('active', '=', True),
                # Включаем всех пользователей для межбраузерной работы
            ])

    def _bus_send_to_user(self, user, message):
        """Отправка bus уведомления конкретному пользователю"""
        try:
            import logging
            _logger = logging.getLogger(__name__)
            
            # Получаем partner пользователя для Odoo 18
            partner = user.partner_id
            _logger.info(f"📤 Sending bus message to partner {partner.id} ({user.name})")
            
            # Для Odoo 18 используем правильную структуру уведомления
            # Вариант 1: Стандартное уведомление через simple_notification
            simple_notification = {
                'type': 'simple_notification',
                'title': f'Real-time обновление от {message.get("user_name", "системы")}',
                'message': f'Обновлен {message.get("model_display_name", "объект")}: {len(message.get("records", []))} записей',
                'sticky': False,
                'warning': False,
            }
            
            try:
                # Отправляем стандартное уведомление через partner_id
                self.env['bus.bus']._sendone(partner, 'simple_notification', simple_notification)
                _logger.info(f"✅ Standard notification sent to partner {partner.id}")
            except Exception as e1:
                _logger.warning(f"⚠️ Standard notification failed: {e1}")
            
            # Вариант 2: Кастомный канал для real-time обновлений
            custom_channel = f"amanat_realtime_{user.id}"
            
            # Для кастомного канала используем только 2 параметра
            custom_message = {
                'type': 'amanat_realtime_update',
                'data': message,
                'user_id': user.id,
                'timestamp': message.get('timestamp')
            }
            
            try:
                # Отправляем в кастомный канал (только 2 параметра!)
                self.env['bus.bus']._sendone(custom_channel, custom_message)
                _logger.info(f"✅ Custom channel message sent to {custom_channel}")
            except Exception as e2:
                _logger.warning(f"⚠️ Custom channel failed: {e2}")
                
            # Вариант 3: Через личный канал пользователя (res.users,id)
            user_channel = f"res.users,{user.id}"
            
            try:
                # Отправляем в личный канал пользователя
                self.env['bus.bus']._sendone(user_channel, message)
                _logger.info(f"✅ User channel message sent to {user_channel}")
            except Exception as e3:
                _logger.warning(f"⚠️ User channel failed: {e3}")
            
            _logger.info(f"✅ Bus messages sent successfully to user {user.name}")
            
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"❌ Error sending bus message to user {user.name}: {e}")
            import traceback
            _logger.error(f"❌ Traceback: {traceback.format_exc()}")

    def _send_realtime_notification(self, message_type, model, records_data, changed_fields=None):
        """Отправка структурированного real-time уведомления всем заинтересованным пользователям"""
        import logging
        _logger = logging.getLogger(__name__)
        
        try:
            _logger.info(f"🔔 _send_realtime_notification: type={message_type}, model={model}")
            
            notification_data = {
                'type': message_type,
                'model': model,
                'model_display_name': self.env[model]._description if model in self.env else model,
                'user_id': self.id,
                'user_name': self.name,
                'timestamp': fields.Datetime.now().isoformat(),
                'records': records_data,
                'changed_fields': changed_fields or []
            }
            
            _logger.info(f"📋 Notification data prepared: {notification_data}")
            
            # Получаем всех заинтересованных пользователей
            interested_users = self._get_interested_users(model)
            
            _logger.info(f"👥 Found {len(interested_users)} interested users for model {model}")
            _logger.info(f"👥 Interested users: {[u.name for u in interested_users]}")
            
            if not interested_users:
                _logger.warning("⚠️ No interested users found - notification will not be sent")
                return
            
            # Отправляем уведомление каждому заинтересованному пользователю 
            for user in interested_users:
                # Для тестирования разрешаем отправку самому себе
                # В продакшене можно вернуть проверку: if user.id == self.id: continue
                
                _logger.info(f"📤 Sending notification to user: {user.name} (ID: {user.id})")
                self._bus_send_to_user(user, notification_data)
            
            _logger.info("✅ All notifications sent successfully")
            
        except Exception as e:
            _logger.error(f"❌ Error sending realtime notification: {e}")
            import traceback
            _logger.error(f"❌ Traceback: {traceback.format_exc()}")

    def notify_record_change(self, action, records, changed_fields=None):
        """Уведомление об изменении записей"""
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info(f"🚀 notify_record_change called: action={action}, records={len(records) if records else 0}")
        
        if not records:
            _logger.warning("⚠️ No records provided to notify_record_change")
            return
            
        # Подготавливаем данные записей
        records_data = []
        for record in records:
            try:
                record_data = {
                    'id': record.id,
                    'display_name': record.display_name
                }
                
                # Добавляем дополнительные поля для отображения
                if hasattr(record, '_get_realtime_fields'):
                    fields_to_read = record._get_realtime_fields()
                else:
                    # Стандартные поля
                    fields_to_read = ['name', 'state', 'create_date', 'write_date']
                
                _logger.info(f"🔍 Reading fields for record {record.id}: {fields_to_read}")
                
                for field_name in fields_to_read:
                    if field_name in record._fields and hasattr(record, field_name):
                        try:
                            value = getattr(record, field_name)
                            if field_name.endswith('_id') and hasattr(value, 'display_name'):
                                record_data[field_name] = {
                                    'id': value.id,
                                    'display_name': value.display_name
                                }
                            else:
                                record_data[field_name] = value
                        except:
                            continue
                
                records_data.append(record_data)
                _logger.info(f"✅ Prepared record data: {record_data}")
                
            except Exception as e:
                _logger.error(f"❌ Error preparing record data for {record}: {e}")
                continue
        
        if records_data:
            _logger.info(f"📤 Sending notification with {len(records_data)} records")
            self._send_realtime_notification(action, records._name, records_data, changed_fields)
        else:
            _logger.warning("⚠️ No records data prepared for notification") 
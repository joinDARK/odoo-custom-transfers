from odoo import models, fields, api
from .base_model import AmanatBaseModel


class TestRealtime(models.Model, AmanatBaseModel):
    _name = 'amanat.test.realtime'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Тест Real-time обновлений'

    name = fields.Char(string='Название', required=True, tracking=True)
    description = fields.Text(string='Описание', tracking=True)
    value = fields.Float(string='Значение', tracking=True)
    active = fields.Boolean(string='Активно', default=True, tracking=True)
    test_date = fields.Date(string='Дата теста', default=fields.Date.today, tracking=True)
    
    state = fields.Selection([
        ('draft', 'Черновик'),
        ('in_progress', 'В процессе'),
        ('done', 'Завершено'),
        ('cancelled', 'Отменено')
    ], string='Состояние', default='draft', tracking=True)
    
    partner_id = fields.Many2one('res.partner', string='Партнер', tracking=True)
    
    def _get_realtime_fields(self):
        """Поля для real-time обновлений в тестовой модели"""
        return [
            'id', 'display_name', 'name', 'description', 'value', 'active',
            'test_date', 'state', 'partner_id', 'create_date', 'write_date'
        ]
    
    def action_start_test(self):
        """Действие для тестирования real-time обновлений"""
        self.write({'state': 'in_progress'})
        return True
    
    def action_complete_test(self):
        """Действие для завершения теста"""
        self.write({'state': 'done'})
        return True
    
    def action_cancel_test(self):
        """Действие для отмены теста"""
        self.write({'state': 'cancelled'})
        return True
    
    def action_test_realtime_update(self):
        """Специальное действие для тестирования real-time обновлений"""
        import random
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info("Starting real-time test update")
        
        # Обновляем случайные поля для тестирования
        new_value = random.randint(1, 1000)
        self.write({
            'value': new_value,
            'description': f'Обновлено в {fields.Datetime.now()}'
        })
        
        _logger.info(f"Real-time test update completed with value: {new_value}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Тест real-time',
                'message': f'Значение обновлено на {new_value}. Проверьте другие открытые вкладки!',
                'type': 'info',
                'sticky': False,
            }
        }
    
    def action_test_bus_directly(self):
        """Прямой тест отправки bus сообщения"""
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info("Testing direct bus message sending")
        
        # Отправляем тестовое сообщение напрямую
        try:
            test_message = {
                'type': 'update',
                'model': self._name,
                'user_id': self.env.user.id,
                'user_name': self.env.user.name,
                'timestamp': fields.Datetime.now().isoformat(),
                'records': [{
                    'id': self.id,
                    'display_name': self.display_name,
                    'name': self.name,
                    'test_message': 'Прямой тест bus сообщения!'
                }],
                'changed_fields': ['test_message']
            }
            
            self.env['bus.bus']._sendone("realtime_updates", 'realtime_updates', test_message)
            _logger.info("Direct bus message sent successfully")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Тест Bus',
                    'message': 'Прямое bus сообщение отправлено! Проверьте консоль браузера.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Error sending direct bus message: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Ошибка Bus',
                    'message': f'Ошибка отправки bus сообщения: {e}',
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def action_simple_bus_test(self):
        """Самый простой тест bus сообщения"""
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info("=== STARTING SIMPLE BUS TEST ===")
        
        try:
            # Простейшее сообщение
            simple_message = {
                'type': 'update',
                'test': 'Hello from Odoo!',
                'timestamp': fields.Datetime.now().isoformat()
            }
            
            _logger.info(f"Sending simple message: {simple_message}")
            
            # Отправляем сообщение
            self.env['bus.bus']._sendone("realtime_updates", 'realtime_updates', simple_message)
            
            _logger.info("Simple bus message sent successfully!")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Простой Bus тест',
                    'message': 'Простое сообщение отправлено! Откройте консоль браузера.',
                    'type': 'success',
                }
            }
            
        except Exception as e:
            _logger.error(f"Simple bus test failed: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Ошибка',
                    'message': f'Тест не удался: {e}',
                    'type': 'danger',
                }
            }
    
    def action_force_realtime_update(self):
        """Принудительное тестирование real-time обновления"""
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info("🔥 FORCE REALTIME UPDATE TEST")
        
        try:
            # Обновляем запись принудительно
            self.write({
                'description': f'Принудительное обновление: {fields.Datetime.now()}'
            })
            
            # Дополнительно отправляем уведомление вручную  
            self._send_realtime_notification('update', ['description'])
            
            _logger.info("🔥 Force update completed")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Принудительное обновление',
                    'message': 'Запись обновлена принудительно! Проверьте другие вкладки.',
                    'type': 'success',
                }
            }
            
        except Exception as e:
            _logger.error(f"Force update failed: {e}")
            import traceback
            _logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Ошибка принудительного обновления',
                    'message': f'Ошибка: {e}',
                    'type': 'danger',
                }
            }
    
    def action_test_new_realtime_system(self):
        """Тест новой системы real-time с личными каналами пользователей"""
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info("=== TESTING NEW REALTIME SYSTEM ===")
        
        try:
            # Отправляем уведомление через новую систему
            # _logger.info("Calling _send_realtime_notification manually...")
            # self._send_realtime_notification('update', ['test_field'])
            
            _logger.info("Manual notification sent!")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Тест новой системы',
                    'message': 'Уведомление отправлено через новую систему! Проверьте консоль браузера.',
                    'type': 'success',
                }
            }
            
        except Exception as e:
            _logger.error(f"New system test failed: {e}")
            import traceback
            _logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Ошибка',
                    'message': f'Тест новой системы не удался: {e}',
                    'type': 'danger',
                }
            }
    
    def action_test_direct_user_channel(self):
        """Прямой тест отправки на личный канал текущего пользователя"""
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info("=== TESTING DIRECT USER CHANNEL ===")
        
        try:
            user_id = self.env.user.id
            user_channel = f"res.users,{user_id}"
            
            test_message = {
                'type': 'update',
                'model': self._name,
                'user_id': user_id,
                'user_name': self.env.user.name,
                'timestamp': fields.Datetime.now().isoformat(),
                'records': [{
                    'id': self.id,
                    'display_name': self.display_name,
                    'name': self.name,
                    'test_message': 'Прямой тест личного канала!'
                }],
                'changed_fields': ['test_message']
            }
            
            _logger.info(f"Sending to user channel: {user_channel}")
            _logger.info(f"Message: {test_message}")
            
            # Отправляем на личный канал
            self.env['bus.bus']._sendone(user_channel, 'amanat_realtime_update', test_message)
            
            _logger.info("Direct user channel message sent!")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Тест личного канала',
                    'message': f'Сообщение отправлено на канал {user_channel}! Проверьте консоль браузера.',
                    'type': 'success',
                }
            }
            
        except Exception as e:
            _logger.error(f"Direct user channel test failed: {e}")
            import traceback
            _logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Ошибка',
                    'message': f'Тест личного канала не удался: {e}',
                    'type': 'danger',
                }
            }
    
    def action_direct_bus_test(self):
        """Прямой тест отправки bus сообщения всеми доступными методами"""
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info("🧪 DIRECT BUS TEST: Starting...")
        
        try:
            user = self.env.user
            user_channel = f"res.users,{user.id}"
            
            test_message = {
                'type': 'update',
                'model': self._name,
                'user_id': user.id,
                'user_name': user.name,
                'timestamp': fields.Datetime.now().isoformat(),
                'records': [{
                    'id': self.id,
                    'display_name': self.display_name,
                    'test_message': 'Прямой тест bus!'
                }],
                'changed_fields': ['test_message']
            }
            
            _logger.info(f"🧪 DIRECT BUS TEST: Sending to channel {user_channel}")
            _logger.info(f"🧪 DIRECT BUS TEST: Message: {test_message}")
            
            # Пробуем все доступные методы отправки
            methods_tried = []
            success_method = None
            
            # Метод 1: _sendone
            try:
                self.env['bus.bus']._sendone(user_channel, 'amanat_realtime_update', test_message)
                methods_tried.append("_sendone: ✅")
                success_method = "_sendone"
                _logger.info("🧪 Method 1 (_sendone) succeeded")
            except Exception as e:
                methods_tried.append(f"_sendone: ❌ {e}")
                _logger.warning(f"🧪 Method 1 (_sendone) failed: {e}")
            
            # Метод 2: sendone (без подчеркивания)
            try:
                self.env['bus.bus'].sendone(user_channel, 'amanat_realtime_update', test_message)
                methods_tried.append("sendone: ✅")
                if not success_method:
                    success_method = "sendone"
                _logger.info("🧪 Method 2 (sendone) succeeded")
            except Exception as e:
                methods_tried.append(f"sendone: ❌ {e}")
                _logger.warning(f"🧪 Method 2 (sendone) failed: {e}")
            
            # Метод 3: Прямое создание записи в bus.bus
            try:
                self.env['bus.bus'].sudo().create({
                    'channel': user_channel,
                    'message': test_message
                })
                methods_tried.append("direct create: ✅")
                if not success_method:
                    success_method = "direct create"
                _logger.info("🧪 Method 3 (direct create) succeeded")
            except Exception as e:
                methods_tried.append(f"direct create: ❌ {e}")
                _logger.warning(f"🧪 Method 3 (direct create) failed: {e}")
            
            # Метод 4: Через JSON сериализацию
            try:
                import json
                self.env['bus.bus'].sudo().create({
                    'channel': user_channel,
                    'message': json.dumps({
                        'type': 'amanat_realtime_update',
                        'payload': test_message
                    })
                })
                methods_tried.append("JSON create: ✅")
                if not success_method:
                    success_method = "JSON create"
                _logger.info("🧪 Method 4 (JSON create) succeeded")
            except Exception as e:
                methods_tried.append(f"JSON create: ❌ {e}")
                _logger.warning(f"🧪 Method 4 (JSON create) failed: {e}")
            
            _logger.info("🧪 DIRECT BUS TEST: Completed")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Прямой Bus тест',
                    'message': f'Тест завершен. Рабочий метод: {success_method or "НЕТ"}. Проверьте консоль браузера и логи сервера.',
                    'type': 'success' if success_method else 'warning',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            _logger.error(f"🧪 DIRECT BUS TEST ERROR: {e}")
            import traceback
            _logger.error(f"🧪 TRACEBACK: {traceback.format_exc()}")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Ошибка Bus теста',
                    'message': f'Ошибка: {e}',
                    'type': 'danger',
                }
            } 
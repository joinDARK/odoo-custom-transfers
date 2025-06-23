from odoo import http
from odoo.http import request
from odoo import fields
import json
import logging

_logger = logging.getLogger(__name__)


class TestRealtimeController(http.Controller):
    
    @http.route('/amanat/test_realtime_simple', type='json', auth='user')
    def test_simple_notification(self, **kwargs):
        """Простой тест стандартного уведомления"""
        try:
            _logger.info("🧪 SIMPLE NOTIFICATION TEST: Starting...")
            
            user = request.env.user
            partner = user.partner_id
            
            # Создаем стандартное уведомление согласно Odoo 18
            message = {
                'type': 'simple_notification',
                'title': 'Тест уведомления',
                'message': f'Привет от {user.name}! Время: {fields.Datetime.now()}',
                'sticky': False,
                'warning': False,
            }
            
            _logger.info(f"🧪 Sending to partner {partner.id}: {message}")
            
            # Отправляем через partner (2 параметра!)
            request.env['bus.bus']._sendone(partner, 'simple_notification', message)
            
            _logger.info("🧪 Simple notification sent successfully")
            
            return {
                'success': True,
                'message': 'Стандартное уведомление отправлено!',
                'partner_id': partner.id,
                'user_name': user.name
            }
            
        except Exception as e:
            _logger.error(f"🧪 SIMPLE NOTIFICATION ERROR: {e}")
            import traceback
            _logger.error(f"🧪 TRACEBACK: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @http.route('/amanat/test_custom_channel', type='json', auth='user')
    def test_custom_channel(self, **kwargs):
        """Тест кастомного канала"""
        try:
            _logger.info("🧪 CUSTOM CHANNEL TEST: Starting...")
            
            user = request.env.user
            custom_channel = f"amanat_realtime_{user.id}"
            
            # Создаем сообщение для кастомного канала
            message = {
                'type': 'amanat_realtime_update',
                'data': {
                    'type': 'update',
                    'model': 'test.model',
                    'model_display_name': 'Тестовая модель',
                    'user_id': user.id,
                    'user_name': user.name,
                    'timestamp': fields.Datetime.now().isoformat(),
                    'records': [{
                        'id': 999,
                        'display_name': 'Тестовая запись',
                        'name': f'Test Record by {user.name}'
                    }],
                    'changed_fields': ['name']
                },
                'user_id': user.id,
                'timestamp': fields.Datetime.now().isoformat()
            }
            
            _logger.info(f"🧪 Sending to custom channel {custom_channel}: {message}")
            
            # Отправляем в кастомный канал (2 параметра!)
            request.env['bus.bus']._sendone(custom_channel, message)
            
            _logger.info("🧪 Custom channel message sent successfully")
            
            return {
                'success': True,
                'message': f'Сообщение отправлено в кастомный канал {custom_channel}',
                'channel': custom_channel,
                'user_name': user.name
            }
            
        except Exception as e:
            _logger.error(f"🧪 CUSTOM CHANNEL ERROR: {e}")
            import traceback
            _logger.error(f"🧪 TRACEBACK: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @http.route('/amanat/test_user_channel', type='json', auth='user')
    def test_user_channel(self, **kwargs):
        """Тест личного канала пользователя"""
        try:
            _logger.info("🧪 USER CHANNEL TEST: Starting...")
            
            user = request.env.user
            user_channel = f"res.users,{user.id}"
            
            # Создаем сообщение для личного канала
            message = {
                'type': 'update',
                'model': 'amanat.test.realtime',
                'model_display_name': 'Тест Real-time',
                'user_id': user.id,
                'user_name': user.name,
                'timestamp': fields.Datetime.now().isoformat(),
                'records': [{
                    'id': 777,
                    'display_name': 'Тест личного канала',
                    'name': f'User Channel Test by {user.name}'
                }],
                'changed_fields': ['name']
            }
            
            _logger.info(f"🧪 Sending to user channel {user_channel}: {message}")
            
            # Отправляем в личный канал пользователя (2 параметра!)
            request.env['bus.bus']._sendone(user_channel, message)
            
            _logger.info("🧪 User channel message sent successfully")
            
            return {
                'success': True,
                'message': f'Сообщение отправлено в личный канал {user_channel}',
                'channel': user_channel,
                'user_name': user.name
            }
            
        except Exception as e:
            _logger.error(f"🧪 USER CHANNEL ERROR: {e}")
            import traceback
            _logger.error(f"🧪 TRACEBACK: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @http.route('/amanat/test_all_methods', type='json', auth='user')
    def test_all_methods(self, **kwargs):
        """Тест всех методов отправки bus сообщений"""
        try:
            _logger.info("🧪 ALL METHODS TEST: Starting...")
            
            user = request.env.user
            results = []
            
            # Метод 1: Стандартное уведомление
            try:
                partner = user.partner_id
                message1 = {
                    'type': 'simple_notification',
                    'title': 'Тест всех методов',
                    'message': f'Стандартное уведомление от {user.name}',
                    'sticky': False,
                }
                request.env['bus.bus']._sendone(partner, 'simple_notification', message1)
                results.append("✅ Стандартное уведомление отправлено")
                _logger.info("🧪 Method 1 (simple_notification) successful")
            except Exception as e:
                results.append(f"❌ Стандартное уведомление: {e}")
                _logger.error(f"🧪 Method 1 error: {e}")
            
            # Метод 2: Кастомный канал
            try:
                custom_channel = f"amanat_realtime_{user.id}"
                message2 = {
                    'type': 'amanat_realtime_update',
                    'test': 'custom channel test',
                    'user_name': user.name
                }
                request.env['bus.bus']._sendone(custom_channel, message2)
                results.append("✅ Кастомный канал отправлен")
                _logger.info("🧪 Method 2 (custom channel) successful")
            except Exception as e:
                results.append(f"❌ Кастомный канал: {e}")
                _logger.error(f"🧪 Method 2 error: {e}")
            
            # Метод 3: Личный канал
            try:
                user_channel = f"res.users,{user.id}"
                message3 = {
                    'type': 'user_channel_test',
                    'message': f'Личный канал от {user.name}',
                    'timestamp': fields.Datetime.now().isoformat()
                }
                request.env['bus.bus']._sendone(user_channel, message3)
                results.append("✅ Личный канал отправлен")
                _logger.info("🧪 Method 3 (user channel) successful")
            except Exception as e:
                results.append(f"❌ Личный канал: {e}")
                _logger.error(f"🧪 Method 3 error: {e}")
            
            _logger.info("🧪 ALL METHODS TEST: Completed")
            
            return {
                'success': True,
                'message': 'Тест всех методов завершен',
                'results': results,
                'user_name': user.name
            }
            
        except Exception as e:
            _logger.error(f"🧪 ALL METHODS ERROR: {e}")
            import traceback
            _logger.error(f"🧪 TRACEBACK: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e)
            }

    # Старые методы оставляем для совместимости
    @http.route('/amanat/test_realtime', type='http', auth='user', methods=['POST'])
    def test_realtime(self, **kwargs):
        """Старый HTTP тест - оставлен для совместимости"""
        try:
            result = self.test_simple_notification()
            return json.dumps(result)
        except Exception as e:
            return json.dumps({'success': False, 'error': str(e)})
    
    @http.route('/amanat/test_bus', type='json', auth='user')
    def test_bus(self, **kwargs):
        """Старый JSON тест - оставлен для совместимости"""
        return self.test_all_methods() 
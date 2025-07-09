from odoo import models, fields, api, _


class ZayavkaSwiftExtension(models.Model):
    _inherit = 'amanat.zayavka'

    # Связь с моделью SWIFT
    swift_id = fields.Many2one(
        'amanat.swift',
        string='SWIFT/BIC информация',
        help='Информация о банке по SWIFT коду',
        tracking=True
    )
    
    # Поля для SWIFT информации (могут заполняться ботом)
    swift_code = fields.Char(
        string='SWIFT/BIC код',
        help='SWIFT код банка',
        tracking=True
    )
    
    swift_bank_name = fields.Char(
        string='Название банка (SWIFT)',
        help='Название банка из SWIFT информации',
        tracking=True
    )
    
    swift_country = fields.Char(
        string='Страна банка (SWIFT)',
        help='Страна банка из SWIFT информации',
        tracking=True
    )
    
    swift_city = fields.Char(
        string='Город банка (SWIFT)',
        help='Город банка из SWIFT информации',
        tracking=True
    )
    
    swift_address = fields.Text(
        string='Адрес банка (SWIFT)',
        help='Адрес банка из SWIFT информации',
        tracking=True
    )
    
    swift_branch_code = fields.Char(
        string='Код филиала (SWIFT)',
        help='Код филиала из SWIFT информации',
        tracking=True
    )
    
    swift_network_status = fields.Boolean(
        string='Подключен к SWIFT сети',
        help='Подключен ли банк к сети SWIFT',
        tracking=True
    )
    
    # Дополнительные поля для управления SWIFT информацией
    swift_auto_filled = fields.Boolean(
        string='SWIFT заполнен автоматически',
        default=False,
        help='Была ли SWIFT информация заполнена автоматически через бот',
        tracking=True
    )
    
    swift_last_updated = fields.Datetime(
        string='SWIFT последнее обновление',
        help='Когда SWIFT информация была обновлена последний раз',
        readonly=True
    )
    
    swift_notes = fields.Text(
        string='Заметки по SWIFT',
        help='Дополнительные заметки по SWIFT коду',
        tracking=True
    )
    
    # Поля для отслеживания SWIFT переводов
    swift_uetr = fields.Char(
        string='UETR',
        help='Unique End-to-End Transaction Reference для отслеживания перевода',
        size=36,
        tracking=True,
        index=True
    )
    
    swift_transaction_ref = fields.Char(
        string='Transaction Reference',
        help='Reference номер SWIFT перевода',
        tracking=True
    )
    
    swift_transfer_status = fields.Selection([
        ('initiated', 'Инициирован'),
        ('sent_to_bank', 'Отправлен в банк'),
        ('processing', 'В обработке'),
        ('forwarded', 'Переслан'),
        ('pending_credit', 'Ожидает зачисления'),
        ('completed', 'Завершен'),
        ('failed', 'Ошибка'),
        ('returned', 'Возвращен'),
        ('cancelled', 'Отменен'),
        ('unknown', 'Неизвестно')
    ], string='Статус SWIFT перевода', tracking=True)
    
    # Вычисляемое поле для отображения статуса SWIFT
    swift_status_display = fields.Char(
        string='Статус SWIFT кода',
        compute='_compute_swift_status_display',
        store=False,
        help='Статус SWIFT кода из связанной записи'
    )
    
    swift_status_info = fields.Html(
        string='Информация о статусе SWIFT',
        compute='_compute_swift_status_info',
        store=False,
        help='Подробная информация о статусе SWIFT кода'
    )

    @api.onchange('swift_id')
    def _onchange_swift_id(self):
        """Заполнение полей при выборе SWIFT записи"""
        if self.swift_id:
            self.swift_code = self.swift_id.bic_code
            self.swift_bank_name = self.swift_id.bank_name or self.swift_id.bank_name_short
            self.swift_country = self.swift_id.country_name
            self.swift_city = self.swift_id.city
            self.swift_address = self.swift_id.address
            self.swift_branch_code = self.swift_id.branch_code
            self.swift_network_status = self.swift_id.swift_network
            self.swift_last_updated = fields.Datetime.now()

    @api.onchange('swift_code')
    def _onchange_swift_code(self):
        """Автоматический поиск SWIFT информации при вводе кода"""
        if self.swift_code and len(self.swift_code) in [8, 11]:
            # Ищем существующую SWIFT запись
            swift_record = self.env['amanat.swift'].search([
                ('bic_code', '=', self.swift_code.upper())
            ], limit=1)
            
            if swift_record:
                self.swift_id = swift_record
                self._onchange_swift_id()
            else:
                # Можно создать новую запись автоматически
                self.swift_bank_name = ''
                self.swift_country = ''
                self.swift_city = ''
                self.swift_address = ''
                self.swift_branch_code = ''
                self.swift_network_status = False

    def action_fetch_swift_info(self):
        """Кнопка для получения SWIFT информации"""
        for record in self:
            if record.swift_code:
                # Создаем или обновляем SWIFT запись
                SwiftModel = self.env['amanat.swift']
                swift_record = SwiftModel.search_or_create_swift(record.swift_code.upper())
                
                if swift_record:
                    record.swift_id = swift_record
                    record._onchange_swift_id()
                    record.swift_auto_filled = True
                    record.message_post(
                        body=f"SWIFT информация обновлена для кода: {record.swift_code}"
                    )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('SWIFT информация обновлена'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_swift_details(self):
        """Кнопка для просмотра деталей SWIFT"""
        self.ensure_one()
        if not self.swift_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('SWIFT информация не найдена'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('SWIFT Информация'),
            'res_model': 'amanat.swift',
            'view_mode': 'form',
            'res_id': self.swift_id.id,
            'target': 'new',
            'context': {'default_bic_code': self.swift_code}
        }

    def action_track_swift_transfer(self):
        """Кнопка для отслеживания SWIFT перевода"""
        self.ensure_one()
        if not self.swift_uetr and not self.swift_transaction_ref:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Для отслеживания необходимо указать UETR или номер перевода'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Получаем статус через API
        channel = self.env['discuss.channel']
        identifier = self.swift_uetr or self.swift_transaction_ref
        identifier_type = 'uetr' if self.swift_uetr else 'reference'
        
        tracking_info = channel._get_swift_tracking_status(identifier, identifier_type)
        
        if tracking_info:
            # Обновляем статус в заявке
            if tracking_info.get('status'):
                self.swift_transfer_status = tracking_info.get('status')
            
            self.message_post(
                body=f"Статус SWIFT перевода обновлен: {tracking_info.get('status_description', 'Неизвестно')}"
            )
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Статус SWIFT перевода обновлен'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Не удалось получить статус SWIFT перевода'),
                    'type': 'error',
                    'sticky': False,
                }
            }

    @api.model
    def update_swift_from_bot(self, zayavka_id, swift_data):
        """Метод для обновления SWIFT информации из бота"""
        try:
            zayavka = self.browse(zayavka_id)
            if not zayavka.exists():
                return False
            
            # Создаем или находим SWIFT запись
            SwiftModel = self.env['amanat.swift']
            swift_record = SwiftModel.search_or_create_swift(swift_data['bic_code'])
            
            # Обновляем заявку
            zayavka.write({
                'swift_id': swift_record.id,
                'swift_code': swift_data['bic_code'],
                'swift_bank_name': swift_data.get('bank_name'),
                'swift_country': swift_data.get('country_name'),
                'swift_city': swift_data.get('city'),
                'swift_address': swift_data.get('address'),
                'swift_branch_code': swift_data.get('branch_code'),
                'swift_network_status': swift_data.get('swift_network', False),
                'swift_auto_filled': True,
                'swift_last_updated': fields.Datetime.now(),
                'swift_received_date': swift_data.get('received_date', fields.Date.today())
            })
            
            # Добавляем сообщение в чаттер
            zayavka.message_post(
                body=f"SWIFT информация добавлена через бот:<br/>"
                     f"Код: {swift_data['bic_code']}<br/>"
                     f"Банк: {swift_data.get('bank_name', 'N/A')}<br/>"
                     f"Страна: {swift_data.get('country_name', 'N/A')}"
            )
            
            return True
            
        except Exception as e:
            self.env['ir.logging'].create({
                'name': 'SWIFT Bot Update Error',
                'type': 'server',
                'level': 'ERROR',
                'message': f"Error updating zayavka {zayavka_id} with SWIFT data: {str(e)}",
                'path': 'amanat.zayavka',
                'line': '1',
                'func': 'update_swift_from_bot'
            })
            return False

    @api.depends('swift_id', 'swift_id.swift_status', 'swift_id.last_updated')
    def _compute_swift_status_display(self):
        """Вычисление отображения статуса SWIFT"""
        for record in self:
            if record.swift_id and record.swift_id.swift_status:
                status_mapping = {
                    'active': '🟢 Активный',
                    'inactive': '🔴 Неактивный',
                    'suspended': '🟡 Приостановлен',
                    'pending': '🔵 В ожидании',
                    'unknown': '⚪ Неизвестно'
                }
                record.swift_status_display = status_mapping.get(record.swift_id.swift_status, '⚪ Неизвестно')
            else:
                record.swift_status_display = '⚪ Нет данных'
    
    @api.depends('swift_id', 'swift_id.swift_status', 'swift_id.last_updated', 'swift_id.bank_name', 'swift_id.country_name')
    def _compute_swift_status_info(self):
        """Вычисление подробной информации о статусе SWIFT"""
        for record in self:
            if record.swift_id:
                swift_record = record.swift_id
                status_mapping = {
                    'active': '🟢 Активный',
                    'inactive': '🔴 Неактивный',
                    'suspended': '🟡 Приостановлен',
                    'pending': '🔵 В ожидании',
                    'unknown': '⚪ Неизвестно'
                }
                
                status_display = status_mapping.get(swift_record.swift_status, '⚪ Неизвестно')
                
                # Определяем цвет фона на основе статуса
                bg_color = '#f9f9f9'
                if swift_record.swift_status == 'active':
                    bg_color = '#d4edda'  # Зеленый
                elif swift_record.swift_status == 'inactive':
                    bg_color = '#f8d7da'  # Красный
                elif swift_record.swift_status == 'suspended':
                    bg_color = '#fff3cd'  # Желтый
                elif swift_record.swift_status == 'pending':
                    bg_color = '#d1ecf1'  # Синий
                
                info_html = f"""
                <div style="padding: 15px; border: 1px solid #ddd; border-radius: 8px; background-color: {bg_color}; margin: 10px 0;">
                    <h4 style="margin: 0 0 15px 0; color: #333; font-size: 16px;">🏦 SWIFT Информация</h4>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                        <div>
                            <p style="margin: 5px 0;"><strong>Код:</strong> {swift_record.bic_code or 'N/A'}</p>
                            <p style="margin: 5px 0;"><strong>Банк:</strong> {swift_record.bank_name or swift_record.bank_name_short or 'N/A'}</p>
                            <p style="margin: 5px 0;"><strong>Страна:</strong> {swift_record.country_name or swift_record.country_code or 'N/A'}</p>
                            <p style="margin: 5px 0;"><strong>Город:</strong> {swift_record.city or 'N/A'}</p>
                        </div>
                        <div>
                            <p style="margin: 5px 0;"><strong>Статус:</strong> {status_display}</p>
                            <p style="margin: 5px 0;"><strong>SWIFT сеть:</strong> {'✅ Подключен' if swift_record.swift_network else '❌ Не подключен'}</p>
                            <p style="margin: 5px 0;"><strong>Филиал:</strong> {swift_record.branch_code or 'N/A'}</p>
                            <p style="margin: 5px 0;"><strong>Обновлено:</strong> {swift_record.last_updated.strftime('%d.%m.%Y %H:%M') if swift_record.last_updated else 'N/A'}</p>
                        </div>
                    </div>
                    {f'<p style="margin: 10px 0 0 0; color: #666;"><strong>UETR:</strong> {swift_record.uetr_no}</p>' if swift_record.uetr_no else ''}
                    {f'<p style="margin: 5px 0 0 0; color: #666;"><strong>Адрес:</strong> {swift_record.address}</p>' if swift_record.address else ''}
                    <div style="margin-top: 10px;">
                        <a href="#" onclick="window.open('/web#id={swift_record.id}&view_type=form&model=amanat.swift', '_blank'); return false;" style="color: #007bff; text-decoration: none;">
                            📋 Открыть детали SWIFT
                        </a>
                    </div>
                </div>
                """
                record.swift_status_info = info_html
            else:
                record.swift_status_info = """
                <div style="padding: 15px; border: 1px solid #ddd; border-radius: 8px; background-color: #fff3cd; margin: 10px 0;">
                    <h4 style="margin: 0 0 10px 0; color: #856404;">⚠️ SWIFT информация не найдена</h4>
                    <p style="margin: 5px 0; color: #856404;">Для получения SWIFT информации:</p>
                    <ul style="margin: 5px 0; padding-left: 20px; color: #856404;">
                        <li>Введите BIC код в поле "SWIFT код"</li>
                        <li>Нажмите кнопку "Получить SWIFT информацию"</li>
                        <li>Или используйте команду /swift в чате</li>
                    </ul>
                </div>
                """ 
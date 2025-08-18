from odoo import models, fields, api
from .base_model import AmanatBaseModel
import requests
import base64
import logging

_logger = logging.getLogger(__name__)

class AmanatKassaFiles(models.Model, AmanatBaseModel):
    _name = 'amanat.kassa_files'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Касса файлы'

    name = fields.Char(string='Наименование файла', tracking=True)
    sequence = fields.Char(
        string='Номер',
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('amanat.kassa_files.sequence'),
        copy=False,
        tracking=True
    )
    kassa_type = fields.Selection([
        ('kassa_ivan', 'Касса Иван'),
        ('kassa_2', 'Касса 2'),
        ('kassa_3', 'Касса 3'),
        ('all', 'Все кассы'),
    ], string='Тип кассы', tracking=True)
    
    filter_field = fields.Char(string='Поле фильтрации', tracking=True)
    date_from = fields.Date(string='Дата с', tracking=True)
    date_to = fields.Date(string='Дата по', tracking=True)
    
    download_url = fields.Char(string='URL для скачивания', tracking=True)
    file_size = fields.Integer(string='Размер файла', tracking=True)
    rows_count = fields.Integer(string='Количество строк', tracking=True)
    operations_count = fields.Integer(string='Количество операций', tracking=True)
    
    server_response = fields.Text(string='Ответ сервера', tracking=True)
    creation_date = fields.Datetime(string='Дата создания', default=fields.Datetime.now, tracking=True)
    
    # Файлы
    excel_file_attachments = fields.Many2many(
        'ir.attachment', 
        'amanat_kassa_files_excel_attachment_rel',
        'kassa_file_id', 
        'attachment_id',
        string='Excel файлы',
        help='Скачанные Excel файлы'
    )
    
    file_attachments = fields.Many2many(
        'ir.attachment', 
        'amanat_kassa_files_attachment_rel',
        'kassa_file_id', 
        'attachment_id',
        string='Все документы',
        help='Все файлы касс'
    )
    
    # Computed поля для подсчета файлов
    excel_files_count = fields.Integer(
        string='Excel файлов',
        compute='_compute_files_count',
        store=False
    )
    
    total_files_count = fields.Integer(
        string='Всего файлов',
        compute='_compute_files_count',
        store=False
    )
    
    # Статус
    status = fields.Selection([
        ('pending', 'Ожидает'),
        ('downloaded', 'Скачан'),
        ('error', 'Ошибка'),
    ], string='Статус', default='pending', tracking=True)

    @api.depends('excel_file_attachments', 'file_attachments')
    def _compute_files_count(self):
        for record in self:
            record.excel_files_count = len(record.excel_file_attachments)
            record.total_files_count = len(record.file_attachments)

    def download_file_from_server(self):
        """Скачивает файл с сервера и сохраняет как вложение"""
        if not self.download_url:
            _logger.error(f"Нет URL для скачивания файла {self.name}")
            self.status = 'error'
            return False
        
        try:
            _logger.info(f"Начинаем скачивание файла {self.name} с URL: {self.download_url}")
            # Скачиваем файл
            response = requests.get(self.download_url, timeout=30)
            
            if response.status_code == 200:
                # Создаем вложение
                attachment = self.env['ir.attachment'].create({
                    'name': self.name,
                    'datas': base64.b64encode(response.content),
                    'res_model': self._name,
                    'res_id': self.id,
                    'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                })
                
                # Добавляем к файлам
                self.excel_file_attachments = [(4, attachment.id)]
                self.file_attachments = [(4, attachment.id)]
                
                # Обновляем статус
                self.status = 'downloaded'
                
                _logger.info(f"Файл {self.name} успешно скачан и сохранен")
                return True
            else:
                _logger.error(f"Ошибка скачивания файла {self.name}: {response.status_code}")
                self.status = 'error'
                return False
                
        except Exception as e:
            _logger.error(f"Ошибка при скачивании файла {self.name}: {str(e)}")
            self.status = 'error'
            return False

    def preview_excel_files(self):
        """Превью Excel файлов"""
        if not self.excel_file_attachments:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Нет файлов',
                    'message': 'Excel файлы не найдены',
                    'sticky': False,
                    'type': 'warning',
                }
            }
        
        # Открываем первый файл
        attachment = self.excel_file_attachments[0]
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def download_excel_file(self):
        """Скачивает Excel файл"""
        if not self.excel_file_attachments:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Нет файлов',
                    'message': 'Excel файлы не найдены',
                    'sticky': False,
                    'type': 'warning',
                }
            }
        
        attachment = self.excel_file_attachments[0]
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def retry_download(self):
        """Повторная попытка скачивания"""
        self.status = 'pending'
        return self.download_file_from_server()

    @api.model
    def create_from_server_response(self, server_response, kassa_type, filter_field=None, date_from=None, date_to=None):
        """Создает запись на основе ответа сервера"""
        # Извлекаем URL из объекта fileUrl
        file_url_obj = server_response.get('fileUrl', {})
        download_url = None
        
        if isinstance(file_url_obj, dict):
            download_url = file_url_obj.get('url')
        elif isinstance(file_url_obj, str):
            # На случай если сервер вернет строку напрямую
            download_url = file_url_obj
        
        values = {
            'name': server_response.get('fileName', 'Неизвестный файл'),
            'kassa_type': kassa_type,
            'filter_field': filter_field,
            'date_from': date_from,
            'date_to': date_to,
            'download_url': download_url,
            'file_size': server_response.get('fileSize', 0),
            'rows_count': server_response.get('rowsCount', 0),
            'operations_count': server_response.get('operationsCount', 0),
            'server_response': str(server_response),
        }
        
        # Создаем запись с очищенным контекстом (убираем default_status для заявок)
        kassa_file = self.with_context(default_status=None).create(values)
        
        # Автоматически скачиваем файл
        if kassa_file.download_url:
            kassa_file.download_file_from_server()
        
        return kassa_file 
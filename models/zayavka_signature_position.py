from odoo import api, fields, models

class AmanatZayavkaSignaturePosition(models.Model):
    _name = 'amanat.zayavka.signature.position'
    _description = 'Signature Position in Zayavka Document'
    _order = 'zayavka_id, document_type, page_number, sequence'

    name = fields.Char(string='Название позиции', required=True)
    zayavka_id = fields.Many2one('amanat.zayavka', string='Заявка', required=True, ondelete='cascade')
    
    # Тип документа в заявке
    document_type = fields.Selection(
        selection=[
            ('zayavka', 'Заявка'),
            ('invoice', 'Инвойс'),
            ('assignment', 'Поручение'),
            ('swift', 'SWIFT'),
            ('swift103', 'SWIFT 103'),
            ('swift199', 'SWIFT 199'),
            ('report', 'Акт-отчет'),
        ], 
        string='Тип документа', 
        required=True
    )
    
    # Позиция на странице
    page_number = fields.Integer(string='Номер страницы', required=True, default=1)
    x_position = fields.Float(string='Позиция X', required=True, help='Позиция по горизонтали в пикселях')
    y_position = fields.Float(string='Позиция Y', required=True, help='Позиция по вертикали в пикселях')
    
    # Размеры области для подписи
    width = fields.Float(string='Ширина', required=True, default=150.0)
    height = fields.Float(string='Высота', required=True, default=50.0)
    
    # Тип подписи
    signature_type = fields.Selection(
        selection=[
            ('signature', 'Подпись'),
            ('stamp', 'Печать')
        ], 
        string='Тип', 
        required=True, 
        default='signature'
    )
    
    # Обязательность заполнения
    required = fields.Boolean(string='Обязательно', default=True)
    
    # Описание для пользователя
    description = fields.Text(string='Описание')
    
    # Последовательность для сортировки
    sequence = fields.Integer(string='Последовательность', default=10)
    
    # Поля для аудита
    create_date = fields.Datetime(string='Дата создания', readonly=True)
    create_uid = fields.Many2one('res.users', string='Создал', readonly=True)
    write_date = fields.Datetime(string='Дата изменения', readonly=True)
    write_uid = fields.Many2one('res.users', string='Изменил', readonly=True)

    @api.constrains('page_number')
    def _check_page_number(self):
        """Проверяем, что номер страницы положительный"""
        for record in self:
            if record.page_number < 1:
                from odoo.exceptions import ValidationError
                raise ValidationError('Номер страницы должен быть больше 0')

    @api.constrains('x_position', 'y_position', 'width', 'height')
    def _check_position_values(self):
        """Проверяем, что позиции и размеры положительные"""
        for record in self:
            if record.x_position < 0 or record.y_position < 0:
                from odoo.exceptions import ValidationError
                raise ValidationError('Позиции должны быть неотрицательными')
            if record.width <= 0 or record.height <= 0:
                from odoo.exceptions import ValidationError
                raise ValidationError('Размеры должны быть положительными')

    def name_get(self):
        """Переопределяем отображение имени"""
        result = []
        document_type_dict = {
            'zayavka': 'Заявка',
            'invoice': 'Инвойс',
            'assignment': 'Поручение',
            'swift': 'SWIFT',
            'swift103': 'SWIFT 103',
            'swift199': 'SWIFT 199',
            'report': 'Акт-отчет',
        }
        for record in self:
            type_name = 'Подпись' if record.signature_type == 'signature' else 'Печать'
            doc_type_name = document_type_dict.get(record.document_type, record.document_type)
            name = f"{record.name} ({type_name}, {doc_type_name}, стр. {record.page_number})"
            result.append((record.id, name))
        return result 
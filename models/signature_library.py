from odoo import models, fields, api


class SignatureLibrary(models.Model):
    _name = 'signature.library'
    _description = 'Signature and Stamp Library'
    _order = 'name'

    name = fields.Char(string='Название', required=True)
    signature_type = fields.Selection([
        ('signature', 'Подпись'),
        ('stamp', 'Печать')
    ], string='Тип', required=True, default='signature')
    
    image = fields.Binary(string='Изображение', required=True)
    image_filename = fields.Char(string='Имя файла')
    
    description = fields.Text(string='Описание')
    
    # Размеры по умолчанию для подписи/печати (в пикселях)
    default_width = fields.Integer(string='Ширина по умолчанию', default=150)
    default_height = fields.Integer(string='Высота по умолчанию', default=50)
    
    active = fields.Boolean(string='Активно', default=True)
    
    # Поля для аудита
    create_date = fields.Datetime(string='Дата создания', readonly=True)
    create_uid = fields.Many2one('res.users', string='Создал', readonly=True)
    write_date = fields.Datetime(string='Дата изменения', readonly=True)
    write_uid = fields.Many2one('res.users', string='Изменил', readonly=True)

    @api.model
    def create(self, vals):
        """Автоматически устанавливаем размеры по умолчанию в зависимости от типа"""
        if vals.get('signature_type') == 'stamp' and not vals.get('default_width'):
            vals['default_width'] = 100
            vals['default_height'] = 100
        return super().create(vals)

    def name_get(self):
        """Переопределяем отображение имени для включения типа"""
        result = []
        for record in self:
            type_name = dict(self._fields['signature_type'].selection)[record.signature_type]
            name = f"{record.name} ({type_name})"
            result.append((record.id, name))
        return result 
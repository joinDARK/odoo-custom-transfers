from odoo import api, fields, models

class AmanatZayavkaSignatureAssignment(models.Model):
    _name = 'amanat.zayavka.signature.assignment'
    _description = 'Signature Assignment for Zayavka'
    _order = 'zayavka_id, document_type, position_id'

    name = fields.Char(string='Название', required=True)
    zayavka_id = fields.Many2one('amanat.zayavka', string='Заявка', required=True, ondelete='cascade')
    position_id = fields.Many2one('amanat.zayavka.signature.position', string='Позиция', required=True)
    
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
            ('screen_sber', 'Скрин сбер'),
            ('zayavka_start', 'Заявка Вход'),
            ('zayavka_end', 'Заявка Выход'),
            ('assignment_start', 'Поручение Вход'),
            ('assignment_end', 'Поручение Выход'),
        ], 
        string='Тип документа', 
        required=True
    )
    
    # Назначенная подпись/печать
    signature_id = fields.Many2one('signature.library', string='Подпись/Печать')
    
    # Информация о позиции (копируется из position_id для удобства)
    page_number = fields.Integer(string='Страница', related='position_id.page_number', readonly=True)
    x_position = fields.Float(string='Позиция X', related='position_id.x_position', readonly=True)
    y_position = fields.Float(string='Позиция Y', related='position_id.y_position', readonly=True)
    width = fields.Float(string='Ширина', related='position_id.width', readonly=True)
    height = fields.Float(string='Высота', related='position_id.height', readonly=True)
    signature_type = fields.Selection(related='position_id.signature_type', readonly=True)
    required = fields.Boolean(string='Обязательно', related='position_id.required', readonly=True)

    @api.constrains('signature_id', 'position_id')
    def _check_signature_type_match(self):
        """Проверяем соответствие типа подписи и позиции"""
        for record in self:
            if record.signature_id and record.position_id:
                if record.signature_id.signature_type != record.position_id.signature_type:
                    from odoo.exceptions import ValidationError
                    raise ValidationError(
                        f'Тип подписи "{record.signature_id.signature_type}" не соответствует '
                        f'типу позиции "{record.position_id.signature_type}"'
                    ) 
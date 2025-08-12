from odoo import models, fields, api
from odoo.exceptions import ValidationError
import mimetypes


class TemplateLibrary(models.Model):
    _name = 'template.library'
    _description = 'Document Template Library'
    _order = 'name'

    name = fields.Char(string='Название', required=True)
    template_type = fields.Selection([
        ('docx', 'Word документ (.docx)'),
        ('xlsx', 'Excel документ (.xlsx)'),
        ('pdf', 'PDF документ (.pdf)'),
        ('html', 'HTML шаблон'),
        ('other', 'Другой формат')
    ], string='Тип шаблона', required=True, default='docx')
    
    # Файл шаблона
    template_file = fields.Binary(string='Файл шаблона', required=True)
    template_filename = fields.Char(string='Имя файла шаблона')
    
    description = fields.Text(string='Описание')
    
    # Категория шаблона для группировки
    category = fields.Selection([
        ('contract', 'Договоры'),
        ('invoice', 'Счета'),
        ('report', 'Отчеты'),
        ('letter', 'Письма'),
        ('certificate', 'Справки'),
        ('statement', 'Заявления'),
        ('other', 'Прочее')
    ], string='Категория', default='other')
    


    
    # Статистика использования
    usage_count = fields.Integer(string='Количество использований', default=0, readonly=True)
    last_used = fields.Datetime(string='Последнее использование', readonly=True)

    @api.model
    def create(self, vals):
        """Автоматически определяем тип шаблона по расширению файла"""
        if vals.get('template_filename') and not vals.get('template_type'):
            filename = vals['template_filename'].lower()
            if filename.endswith('.docx'):
                vals['template_type'] = 'docx'
            elif filename.endswith('.xlsx'):
                vals['template_type'] = 'xlsx'
            elif filename.endswith('.pdf'):
                vals['template_type'] = 'pdf'
            elif filename.endswith('.html') or filename.endswith('.htm'):
                vals['template_type'] = 'html'
            else:
                vals['template_type'] = 'other'
        return super().create(vals)

    @api.constrains('template_filename')
    def _check_template_filename(self):
        """Валидация имени файла шаблона"""
        for record in self:
            if record.template_filename:
                # Проверяем, что файл имеет допустимое расширение
                allowed_extensions = ['.docx', '.xlsx', '.pdf', '.html', '.htm', '.txt', '.xml']
                filename_lower = record.template_filename.lower()
                
                if not any(filename_lower.endswith(ext) for ext in allowed_extensions):
                    raise ValidationError(
                        f'Недопустимое расширение файла. '
                        f'Разрешенные расширения: {", ".join(allowed_extensions)}'
                    )

    def name_get(self):
        """Переопределяем отображение имени для включения типа и категории"""
        result = []
        for record in self:
            type_name = dict(self._fields['template_type'].selection)[record.template_type]
            category_name = dict(self._fields['category'].selection)[record.category]
            name = f"{record.name} ({type_name} - {category_name})"
            result.append((record.id, name))
        return result
    
    def increment_usage(self):
        """Увеличить счетчик использования шаблона"""
        self.sudo().write({
            'usage_count': self.usage_count + 1,
            'last_used': fields.Datetime.now()
        })
    
    @api.model
    def get_templates_by_category(self, category):
        """Получить шаблоны по категории"""
        return self.search([('category', '=', category)])
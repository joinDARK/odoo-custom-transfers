from odoo import models, fields, api
from lxml import etree


class ListViewNumberingMixin(models.AbstractModel):
    """
    Mixin для автоматического добавления нумерации в list views
    """
    _name = 'amanat.list.view.numbering.mixin'
    _description = 'List View Numbering Mixin'

    # Виртуальное поле для отображения номера строки
    row_number = fields.Char(string='№', compute='_compute_row_number', store=False)

    @api.depends_context('list_offset', 'list_limit')
    def _compute_row_number(self):
        """Вычисляет номер строки для каждой записи"""
        offset = self.env.context.get('list_offset', 0)
        for index, record in enumerate(self):
            record.row_number = str(offset + index + 1)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """Переопределяем метод для автоматического добавления колонки номеров в list views"""
        result = super().fields_view_get(view_id=view_id, view_type=view_type, 
                                       toolbar=toolbar, submenu=submenu)
        
        if view_type == 'list' and result.get('arch'):
            # Парсим XML архитектуру view
            doc = etree.fromstring(result['arch'])
            
            # Ищем элемент list или tree
            list_element = doc.xpath('//list | //tree')[0] if doc.xpath('//list | //tree') else None
            
            if list_element is not None:
                # Проверяем, есть ли уже колонка с номерами
                existing_number_field = list_element.xpath('.//field[@name="row_number"]')
                
                if not existing_number_field:
                    # Создаем новое поле для номера строки
                    number_field = etree.Element('field', {
                        'name': 'row_number',
                        'string': '№',
                        'readonly': '1',
                        'width': '50px',
                        'class': 'o_list_number_column'
                    })
                    
                    # Вставляем в начало списка
                    list_element.insert(0, number_field)
                    
                    # Обновляем архитектуру
                    result['arch'] = etree.tostring(doc, encoding='unicode')
                    
                    # Добавляем поле в fields если его там нет
                    if 'row_number' not in result.get('fields', {}):
                        result.setdefault('fields', {})['row_number'] = {
                            'type': 'char',
                            'string': '№',
                            'readonly': True,
                            'searchable': False,
                            'sortable': False,
                        }
        
        return result

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Переопределяем search_read для передачи offset в контекст"""
        # Добавляем offset в контекст для правильного вычисления номеров строк
        context = dict(self.env.context, list_offset=offset or 0, list_limit=limit)
        return super(ListViewNumberingMixin, self.with_context(context)).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """Переопределяем read_group для работы с группировкой"""
        # Для группированных данных отключаем нумерацию
        return super().read_group(
            domain=domain, fields=fields, groupby=groupby, 
            offset=offset, limit=limit, orderby=orderby, lazy=lazy
        ) 
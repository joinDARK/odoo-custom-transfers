# models/contragent.py
from odoo import models, fields, api
from .base_model import AmanatBaseModel

class Contragent(models.Model, AmanatBaseModel):
    _name = 'amanat.contragent'
    _description = 'Контрагент'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]

    name = fields.Char(string='Имя', required=True, tracking=True)
    recon_Balance_0 = fields.Float(string='Баланс RUB сверка', tracking=True)
    recon_Balance_1 = fields.Float(string='Баланс RUB сверка баланс 1', tracking=True)
    recon_Balance_2 = fields.Float(string='Баланс RUB сверка баланс 2', tracking=True)
    recon_cash_rub = fields.Float(string='Баланс RUB сверка КЕШ', tracking=True)
    recon_usdt = fields.Float(string='Баланс USDT сверка', tracking=True)
    recon_usd = fields.Float(string='Баланс USD сверка', tracking=True)
    recon_cash_usd = fields.Float(string='Баланс USD сверка КЕШ', tracking=True)
    recon_euro = fields.Float(string='Баланс EURO сверка', tracking=True)
    recon_cash_euro = fields.Float(string='Баланс EURO сверка КЕШ', tracking=True)
    recon_cny = fields.Float(string='Баланс CNY сверка', tracking=True)
    recon_cash_cny = fields.Float(string='Баланс CNY сверка КЕШ', tracking=True)
    recon_aed = fields.Float(string='Баланс AED сверка', tracking=True)
    recon_cash_aed = fields.Float(string='Баланс AED сверка КЕШ', tracking=True)
    recon_eq_dollar = fields.Float(string='Баланс Эквивалент $', tracking=True)
    recon_eq_compare_1 = fields.Float(string='Баланс Эквивалент $ сравнение 1', tracking=True)
    recon_eq_compare_2 = fields.Float(string='Баланс Эквивалент $ сравнение 2', tracking=True)

    cont_rub = fields.Float(string='Баланс RUB конт', tracking=True)
    cont_usd = fields.Float(string='Баланс USD конт', tracking=True)
    cont_usdt = fields.Float(string='Баланс USDT конт', tracking=True)
    cont_aed = fields.Float(string='Баланс AED конт', tracking=True)
    cont_euro = fields.Float(string='Баланс EURO конт', tracking=True)
    cont_cny = fields.Float(string='Баланс CNY конт', tracking=True)
    cash_cny = fields.Float(string='Баланс CNY КЕШ', tracking=True)
    cash_aed = fields.Float(string='Баланс AED КЕШ', tracking=True)
    cash_rub = fields.Float(string='Баланс RUB КЕШ', tracking=True)
    cash_euro = fields.Float(string='Баланс EURO КЕШ', tracking=True)
    cash_usd = fields.Float(string='Баланс USD КЕШ', tracking=True)

    # Связь многие ко многим с Плательщиками
    payer_ids = fields.Many2many(
        'amanat.payer',
        'amanat_payer_contragent_rel',  # Общее имя таблицы-связи с моделью Payer
        'contragent_id',  # Поле-ссылка на эту модель
        'payer_id',  # Поле-ссылка на модель Плательщик
        string='Плательщики',
        tracking=True,
        ondelete='cascade'
    )
    payer_inn = fields.Char(
        string='ИНН (от Плательщиков)',
        compute='_compute_payer_inn',
        store=True,
        tracking=True
    )
    inn = fields.Char(string='ИНН', tracking=True)
    date_start = fields.Date(string='дата начало', tracking=True)
    date_end = fields.Date(string='дата конец', tracking=True)

    @api.depends('payer_ids.inn')
    def _compute_payer_inn(self):
        for record in self:
            # Фильтруем связанные записи, чтобы исключить несуществующие или пустые ИНН
            valid_payers = record.payer_ids.filtered(lambda r: r.exists() and r.inn)
            record.payer_inn = ", ".join(valid_payers.mapped('inn')) if valid_payers else ''
    
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Поиск с приоритетом точного совпадения и коротких названий"""
        args = args or []
        
        if name:
            # Ищем все записи по обычному поиску
            search_domain = [('name', operator, name)] + args
            all_records = self.search(search_domain, limit=limit * 3)  # Берем больше для сортировки
            
            # Разделяем записи по приоритетам
            exact_match = []          # Точное совпадение
            short_starts_with = []    # Короткие названия (до 5 символов), начинающиеся с поиска
            other_starts_with = []    # Остальные, начинающиеся с поиска  
            contains = []             # Содержащие поисковый запрос
            
            search_lower = name.lower().strip()
            
            for record in all_records:
                record_name_lower = record.name.lower() if record.name else ''
                
                # Точное совпадение
                if record_name_lower == search_lower:
                    exact_match.append(record)
                # Короткие названия, начинающиеся с поиска
                elif record_name_lower.startswith(search_lower) and len(record.name) <= 5:
                    short_starts_with.append(record)
                # Остальные, начинающиеся с поиска
                elif record_name_lower.startswith(search_lower):
                    other_starts_with.append(record)
                # Содержащие поисковый запрос
                else:
                    contains.append(record)
            
            # Сортируем каждую группу по длине названия
            short_starts_with.sort(key=lambda r: len(r.name))
            other_starts_with.sort(key=lambda r: len(r.name))
            contains.sort(key=lambda r: len(r.name))
            
            # Объединяем в нужном порядке
            final_records = exact_match + short_starts_with + other_starts_with + contains
            
            return [(record.id, record.display_name) for record in final_records[:limit]]
        else:
            # Если нет поискового запроса, обычный поиск
            records = self.search(args, limit=limit)
            return [(record.id, record.display_name) for record in records]
    
# models/contragent_contract.py
from odoo import models, fields, api
from .base_model import AmanatBaseModel


class ContragentContract(models.Model, AmanatBaseModel):
    _name = 'amanat.contragent.contract'
    _description = 'Договор с контрагентом'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _order = 'is_actual desc, start_date desc'

    name = fields.Char(string='Название договора', required=True, tracking=True)
    contragent_id = fields.Many2one(
        'amanat.contragent', 
        string='Контрагент', 
        required=True, 
        ondelete='cascade',
        tracking=True
    )
    
    # Файлы договора - используем тот же подход что и в zayavka
    contract_attachments = fields.Many2many(
        'ir.attachment',
        'contract_attachment_rel',
        'contract_id',
        'attachment_id',
        string='Файлы договора',
        tracking=True
    )
    
    start_date = fields.Date(
        string='Дата начала действия', 
        required=True, 
        tracking=True
    )
    end_date = fields.Date(
        string='Дата окончания действия', 
        required=True, 
        tracking=True
    )
    
    is_actual = fields.Boolean(
        string='Актуальный', 
        default=False, 
        tracking=True,
        help='Только один договор может быть отмечен как актуальный для одного контрагента'
    )
    
    auto_prolongation = fields.Boolean(
        string='Автопролонгация', 
        default=False, 
        tracking=True,
        help='Договор автоматически продлевается'
    )
    
    description = fields.Text(string='Описание', tracking=True)
    
    @api.model
    def create(self, vals):
        """При создании нового договора проверяем актуальность"""
        result = super().create(vals)
        if vals.get('is_actual'):
            result._ensure_single_actual()
        return result
    
    def write(self, vals):
        """При изменении договора проверяем актуальность и обновляем даты в контрагенте"""
        result = super().write(vals)
        
        # Если изменили актуальность
        if 'is_actual' in vals:
            for record in self:
                if vals['is_actual']:
                    record._ensure_single_actual()
                    record._update_contragent_dates()
                else:
                    # Если убрали актуальность, нужно обновить даты контрагента
                    record.contragent_id._compute_contract_dates()
        
        # Если изменили даты у актуального договора
        if ('start_date' in vals or 'end_date' in vals) and any(record.is_actual for record in self):
            for record in self.filtered('is_actual'):
                record._update_contragent_dates()
        
        return result
    
    def _ensure_single_actual(self):
        """Обеспечиваем что только один договор актуальный для контрагента"""
        if self.is_actual:
            # Снимаем актуальность с других договоров этого контрагента
            other_contracts = self.contragent_id.contract_ids.filtered(
                lambda c: c.id != self.id and c.is_actual
            )
            if other_contracts:
                other_contracts.write({'is_actual': False})
            
            # Обновляем даты в контрагенте
            self._update_contragent_dates()
    
    def _update_contragent_dates(self):
        """Обновляем даты действия договора в контрагенте"""
        if self.is_actual and self.contragent_id:
            self.contragent_id.write({
                'date_start': self.start_date,
                'date_end': self.end_date
            })
    
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """Проверяем что дата начала меньше даты окончания"""
        for record in self:
            if record.start_date and record.end_date and record.start_date >= record.end_date:
                raise models.ValidationError(
                    'Дата начала договора должна быть меньше даты окончания.'
                )
    
    def name_get(self):
        """Красивое отображение имени договора"""
        result = []
        for record in self:
            name = record.name
            if record.is_actual:
                name += ' (Актуальный)'
            if record.start_date and record.end_date:
                name += f' [{record.start_date} - {record.end_date}]'
            result.append((record.id, name))
        return result


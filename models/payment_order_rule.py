from odoo import models, fields, api

class PaymentOrderRule(models.Model):
    _name = 'amanat.payment_order_rule'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Правило Платежка РФ'

    name = fields.Char(
        string="Платежка РФ",
        compute='_compute_name',
        store=True, 
        tracking=True
    )
    date_start = fields.Date(string="Дата начала", tracking=True)
    date_end = fields.Date(string="Дата конца", tracking=True)
    zayavka_ids = fields.One2many(
        'amanat.zayavka',
        'payment_order_rule_id',
        string='Заявки'
    )
    percent = fields.Float(string="Процент", tracking=True)

    min_application_amount = fields.Float(string="Минимальная сумма заявки $", tracking=True)
    max_application_amount = fields.Float(string="Максимальная сумма заявки $", tracking=True)

    @api.depends('percent')
    def _compute_name(self):
        for rec in self:
            rec.name = f"Платежка РФ: {rec.percent * 100}%"
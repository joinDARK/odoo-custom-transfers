from odoo import models, fields, api
from .base_model import AmanatBaseModel

class Manager(models.Model, AmanatBaseModel):
    _name = 'amanat.manager'
    _description = 'Менеджеры'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Имя")
    phone = fields.Char(string="Телефон")
    date = fields.Date(string="Дата рождения")
    # Предполагается, что модель заявок существует (например, manager.application)
    applications = fields.Many2many(
        'amanat.zayavka',
        'amanat_zayavka_manager_rel',
        'manager_id',
        'zayavka_id',
        string="Заявки",
        tracking=True
    )
    # Поле "Проверяю" можно реализовать как флаг (Boolean) или, при необходимости, как строковое поле
    checking = fields.Many2many(
        'amanat.zayavka',
        'amanat_zayavka_checker_rel',
        'checker_id',
        'zayavka_id',
        string="Проверяю",
        tracking=True
    )
    # Поле "Задачник" реализовано как ссылка на модель задач (например, manager.task)
    task_manager = fields.Many2one('amanat.task', string="Задачник")
    total_applications = fields.Integer(
        string="Количество заявок за менеджером",
        compute="_compute_applications_stats",
        store=True
    )
    wrong_applications = fields.Integer(
        string="Количество ошибочных заявок за менеджером",
        compute="_compute_applications_stats",
        store=True
    )
    efficiency = fields.Float(
        string="Эффективность менеджера",
        compute="_compute_efficiency",
        store=True,
        digits=(16, 2)
    )

    @api.depends('applications', 'applications.status', 'applications.hide_in_dashboard')
    def _compute_applications_stats(self):
        for rec in self:
            # Считаем только заявки, которые не скрыты в дашборде
            visible_applications = rec.applications.filtered(lambda z: not z.hide_in_dashboard)
            rec.total_applications = len(visible_applications)
            
            # Ошибочные заявки - это заявки со статусом 'cancel' (отменено клиентом)
            wrong_applications = visible_applications.filtered(lambda z: z.status == 'cancel')
            rec.wrong_applications = len(wrong_applications)

    @api.depends('total_applications', 'wrong_applications')
    def _compute_efficiency(self):
        for rec in self:
            if rec.total_applications:
                rec.efficiency = (rec.total_applications - rec.wrong_applications) / rec.total_applications
            else:
                rec.efficiency = 0.0

from odoo import models, fields, api
from .base_model import AmanatBaseModel

class Manager(models.Model, AmanatBaseModel):
    _name = 'amanat.manager'
    _description = 'Менеджеры'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Имя")
    user_id = fields.Many2one('res.users', string="Пользователь", required=True, tracking=True)
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
        readonly=False,
        store=True
    )
    wrong_applications = fields.Integer(
        string="Количество ошибочных заявок за менеджером",
        compute="_compute_applications_stats",
        readonly=False,
        store=True
    )
    efficiency = fields.Float(
        string="Эффективность менеджера",
        compute="_compute_efficiency",
        store=True,
        readonly=False,
        digits=(16, 2)
    )

    # Ограничения
    _sql_constraints = [
        ('unique_user_id', 'unique(user_id)', 'Пользователь может быть связан только с одним менеджером!')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Автоматическое заполнение поля name при создании менеджера"""
        for vals in vals_list:
            # Если не указано имя, используем имя пользователя
            if not vals.get('name') and vals.get('user_id'):
                user = self.env['res.users'].browse(vals['user_id'])
                if user.exists():
                    vals['name'] = user.name
        return super().create(vals_list)

    @api.onchange('user_id')
    def _onchange_user_id(self):
        """Автоматическое заполнение имени при выборе пользователя"""
        if self.user_id and not self.name:
            self.name = self.user_id.name

    @api.model
    def find_or_create_manager(self, user_id):
        """Находит или создает менеджера для указанного пользователя"""
        manager = self.search([('user_id', '=', user_id)], limit=1)
        if not manager:
            user = self.env['res.users'].browse(user_id)
            if user.exists():
                manager = self.create([{
                    'name': user.name,
                    'user_id': user_id,
                }])
                import logging
                _logger = logging.getLogger(__name__)
                _logger.info(f"Создан менеджер {manager.name} (ID: {manager.id}) для пользователя {user.name}")
        return manager

    @api.depends('applications', 'applications.status', 'applications.hide_in_dashboard')
    def _compute_applications_stats(self):
        for rec in self:
            # Количество заявок за менеджером - простое rollup поле (все заявки)
            rec.total_applications = len(rec.applications)
            
            # Ошибочные заявки:
            # 1. Все заявки с галочкой "Не отображать в дашборде"
            # 2. Заявки со статусом '22' (отменено клиентом), но БЕЗ галочки скрытия
            hidden_applications = rec.applications.filtered(lambda z: z.hide_in_dashboard)
            visible_wrong_applications = rec.applications.filtered(lambda z: not z.hide_in_dashboard and z.status == '22')
            rec.wrong_applications = len(hidden_applications) + len(visible_wrong_applications)

    @api.depends('total_applications', 'wrong_applications')
    def _compute_efficiency(self):
        for rec in self:
            if rec.total_applications:
                rec.efficiency = (rec.total_applications - rec.wrong_applications) / rec.total_applications
            else:
                rec.efficiency = 0.0

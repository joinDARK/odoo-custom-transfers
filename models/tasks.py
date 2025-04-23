from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class Task(models.Model):
    _name = 'amanat.task'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Task Management'

    name = fields.Char(string='Задача', required=True, tracking=True)
    status = fields.Selection([
        ('not_started', 'Не приступали'),
        ('completed', 'Выполнена'),
        ('in_progress', 'В процессе'),
        ('planned', 'В планах'),
        ('postponed', 'Отложена')
    ], string='Статус', default='not_started', tracking=True)
    subtasks = fields.Text(string='Подзадачи', tracking=True)
    start_date = fields.Date(string='Дата начало', tracking=True)
    deadline = fields.Date(string='Дедлайн', tracking=True)
    completion_date = fields.Date(string='Дата выполнения', tracking=True)
    comment = fields.Text(string='Комментарий', tracking=True)
    execution_cycle = fields.Integer(string='Цикл выполнения', compute='_compute_execution_cycle', readonly=True, tracking=True)
    # Не забыть добавить поле с "Менеджеры"

    @api.depends('start_date', 'completion_date')
    def _compute_execution_cycle(self):
        for record in self:
            if record.start_date and record.completion_date:
                delta = relativedelta(record.completion_date, record.start_date)
                record.execution_cycle = delta.days
            else:
                record.execution_cycle = 0
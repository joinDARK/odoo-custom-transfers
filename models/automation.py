from odoo import models, fields, api

class Automation(models.Model):
    _name = 'amanat.automation'
    _description = 'Автоматизации'

    name = fields.Char(string='Имя', required=True)
    active = fields.Boolean(string='Активный', default=True)
    model_id = fields.Many2one('ir.model', string='Модель', required=True, ondelete='cascade')
    trigger = fields.Selection(
        selection=[
            ('on_create', 'При создании записи'),
            ('on_write', 'При обновлении записи'),
            ('on_delete', 'При ужалении записи'),
            ('custom', 'Кастомный триггер'),
        ],
        string='Триггер',
        default='on_create',
        required=True
    )
    condition = fields.Text(string='Условие', help='Python условие для выполнения скрпита.')
    action = fields.Text(string='Действие', help='Python код вызова при активации триггера.')
    description = fields.Text(string='Описание')

    @api.model
    def execute_automation(self, model_name, record_id, trigger):
        automations = self.search([
            ('model_id.model', '=', model_name),
            ('trigger', '=', trigger),
            ('active', '=', True),
        ])
        for automation in automations:
            try:
                if automation.condition:
                    condition = eval(automation.condition, {
                        'record': self.env[model_name].browse(record_id),
                        'env': self.env,
                    })
                    if not condition:
                        continue

                if automation.action:
                    eval(automation.action, {
                        'record': self.env[model_name].browse(record_id),
                        'env': self.env,
                    })
            except Exception as e:
                print(f"Error executing automation {automation.name}: {e}")
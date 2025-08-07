from odoo import models, fields

class AmanatDemo(models.Model):
    _name = "amanat.demo"
    _description = "Demo model to test drag&drop"

    name = fields.Char(required=True)
    attachment_ids = fields.Many2many(
        "ir.attachment", string="Вложения",
        relation="amanat_demo_attachment_rel",
        column1="demo_id", column2="attachment_id",
    )

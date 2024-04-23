# -*- coding: utf-8 -*-

from odoo import models, fields, api
import re

class CategorySaas(models.Model):
    _name = 'ln10_sv_saas.category'
    _inherit = ["mail.activity.mixin","mail.thread"]
    _description = 'Categoria de modulos'
     
     
     
    name=fields.Char(string="Nombre ")
    descripcion = fields.Text(string="Descripcion")
    git_url=fields.Char(string="Url Git",placeholder="https://github.com/user/ejemplo.git")
    categoria_ids=fields.Many2one('plan.saas', 'Modulos', ondelete='cascade')


    @api.constrains('git_url')
    def _check_git_url(self):
        for record in self:
            if record.git_url:
                # Expresión regular para validar la URL de Git
                git_url_pattern = r'^https?:\/\/(www\.)?github\.com\/[a-zA-Z0-9_\-]+\/[a-zA-Z0-9_\-]+\.git$'
                if not re.match(git_url_pattern, record.git_url):
                    raise models.ValidationError('La URL de Git no es válida. Debe ser una URL de repositorio válido de GitHub.')


#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

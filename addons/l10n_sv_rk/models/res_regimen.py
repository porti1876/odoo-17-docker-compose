# -*- coding:utf-8 -*-

from odoo import models, fields, api

class ResRegimen(models.Model):
    _name = 'res.regimen'
    _rec_name = "valores"
    _description = 'Catálogo de Estructuras DTE, CAT-028'

    codigo = fields.Char(string='Código')
    valores = fields.Char(string='Valores')
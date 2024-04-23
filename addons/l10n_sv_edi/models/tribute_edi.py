# -*- coding:utf-8 -*-

from odoo import models, fields, api

class ResTribute(models.Model):
    _name = 'tribute.edi'
    _description = 'Contiene  los  códigos  asignados  por  la  Administración Tributaria para los diferentes ' \
                   'tributos requeridos de acuerdo al modelo de negocio '

    codigo = fields.Char(string='Código')
    valores = fields.Char(string='Valores')
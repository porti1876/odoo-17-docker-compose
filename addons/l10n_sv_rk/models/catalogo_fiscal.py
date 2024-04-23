# -*- coding: utf-8 -*-

from odoo import models, fields, api

class RecintoFiscal(models.Model):
    _name = 'catalogo.recinto.fiscal'
    _rec_name = "descripcion"

    code = fields.Char(string='Clave')
    descripcion = fields.Char(string='Descripción')
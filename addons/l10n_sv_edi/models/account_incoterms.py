# -*- coding: utf-8 -*-

from odoo import models, fields, api

class CatalogoIncoterms(models.Model):
    _name = 'catalogo.incoterms'
    _rec_name = "description"
    _description = "Incoterms para la factura electronica de EL Salvador"

    code = fields.Char(string='código')
    description = fields.Char(string='Descripción')
    codeIncoterms  = fields.Char(string="Código incoterms")
# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    impuesto = fields.Selection(selection=[('002', 'IVA'),
                                           ('003', ' IEPS'),
                                           ('001', 'ISR'),
                                           ('004', 'Impuesto Local')], string='Impuesto')
    tipo_factor = fields.Selection(selection=[('Tasa', 'Tasa'),
                                              ('Cuota', 'Cuota'),
                                              ('Exento', 'Exento')], string='Tipo factor')
    impuesto_local = fields.Char('Impuesto Local')

    retencion_iva_mh = fields.Selection(selection=[('22', 'Retención IVA 1%'),
                                                   ('C4', 'Retención IVA 13%'),
                                                   ('C9', 'Otras retenciones IVA casos especiales'),
                                                   ], string='Retención IVA MH')

    code_dte_sv = fields.Char(string='Código para dte')

# -*- coding: utf-8 -*-
from odoo import models, fields, api


STATE = [
    ('draft', "Draft"),
    ('confirm', "Confirmed"),
    ('cancel', "Cancelled")
]
class ClientSaas(models.Model):
    _name = "ln10_sv_saas.client"
    _description = "Clientes"
    
    
    name=fields.Char(string="Nombre")
   # cliente_ids=fields.Many2one('rocket_instancias.res_instancia',string="Instance Name", ondelete='cascade')
    #cliente= fields.Many2one(string="Cliente", related='cliente_ids.cliente',ondelete='cascade')
    
   
    #ip_server=fields.Char(string="IP", related='cliente_ids.ip_server', readonly=True)
    state = fields.Selection(
        selection=STATE, string="States", default="draft")
   
   # @api.depends('cliente')
    # def _compute_nombre(self):
     #   for record in self:
     #       record.name = record.cliente.name
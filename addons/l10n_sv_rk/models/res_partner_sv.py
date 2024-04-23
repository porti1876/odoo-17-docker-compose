from odoo import models, fields, api, _
from .res_company import NitUnique
from odoo.exceptions import ValidationError
import re


class ResPartner(models.Model):
    _inherit = 'res.partner'

    export_license = fields.Char(string="Licencia de exportación", help="Ingrese licencia de exportación si creará "
                                                                        "facturas de exportación.")
    document_nit = fields.Char(string='NIT')
    document_giro_res = fields.Many2one(comodel_name='res.giro', string="Giro / Actividad Económica",
                                        help="Ingrese la actividad económica relacionada con su industria")
    document_dui = fields.Char(string='DUI')
    document_pasaporte = fields.Char(string='Pasaporte')
    document_carnet_residente = fields.Char(string='Carnet de Residente')
    journal_contacts = fields.Many2one(comodel_name='account.journal', string='Diario contable enlazado')
    
    recinto_fiscal_id  =  fields.Many2one('catalogo.recinto.fiscal', string='Récinto Fiscal')
    document_nit_compute = fields.Char(string="NIT sin guiones", compute='_compute_nit_number_partner', readonly=True)
    document_dui_compute = fields.Char(string="DUI sin guiones", compute='_compute_dui_number_partner', readonly=True)
    document_vat_compute = fields.Char(string="NRC sin guiones", compute='_compute_vat_number_partner', readonly=True)

    @api.depends('document_nit')
    def _compute_nit_number_partner(self):
        for record in self:
            record.document_nit_compute = NitUnique.remove_dash(record.document_nit)

    @api.depends('document_dui')
    def _compute_dui_number_partner(self):
        for record in self:
            record.document_dui_compute = NitUnique.remove_dash(record.document_dui)
    @api.depends('vat')
    def _compute_vat_number_partner(self):
        for record in self:
            record.document_vat_compute = NitUnique.remove_dash(record.vat)

     
   # _columns = {
       # 'tipo_persona':fields.Selection(selection=[('01', 'persona natural'), ('02','persona juridica')],
        #                            string="Tipo de persona")
    #}
    
   
    
    

    


    



class Partner(models.Model):
    _inherit = 'res.partner'

    munic_id = fields.Many2one('res.municipality', string='Municipio', ondelete='restrict')

    def _onchange_state_id(self):
        if not self.country_id:
            self.country_id = self.state_id.country_id
        if self.state_id:
            return {'domain': {'munic_id': [('dpto_id', '=', self.state_id.id)]}}
        else:
            return {'domain': {'munic_id': []}}

    @api.onchange('munic_id')
    def _onchange_munic_id(self):
        if not self.state_id:
            self.state_id = self.munic_id.dpto_id
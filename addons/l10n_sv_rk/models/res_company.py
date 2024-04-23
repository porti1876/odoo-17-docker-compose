from odoo import models, fields, api, _


class ResCompanySv(models.Model):
    _inherit = 'res.company'

    document_nit_company = fields.Char(string="NIT")
    document_giro_company = fields.Many2one(comodel_name="res.giro", string="Giro / Actividad Económica")
    document_nit = fields.Char(compute="_compute_nit_number", readonly=True)
    document_vat = fields.Char(compute="_compute_vat_number", readonly=True)
    recinto_fiscal_id = fields.Many2one('catalogo.recinto.fiscal', string='Recinto Fiscal')
    regimen_fiscal_id = fields.Many2one('res.regimen', string='Regimen Fiscal')

    @api.depends('document_nit_company')
    def _compute_nit_number(self):
        for record in self:
            record.document_nit = NitUnique.remove_dash(record.document_nit_company)
    @api.depends('vat')
    def _compute_vat_number(self):
        for record in self:
            record.document_vat = NitUnique.remove_dash(record.vat)


class NitUnique(models.AbstractModel):
    _name = 'nit.unique'
    _description = 'Método para quitar guiones de Nit y Dui'

    @staticmethod
    def remove_dash(text):
        if text:
            return text.replace('-', '')
        else:
            return ''



class ResCompanyMunic(models.Model):
    _inherit = 'res.company'

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

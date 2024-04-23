from odoo import fields, models, api, _


class ResCountryEdiSv(models.Model):
    _name = "res.country.edi"
    _description = "Paises del mundo con su código para facturación electrónica de El Salvador"

    name = fields.Char(string="País")
    code = fields.Char(string="Código en fact. electrónica", help='Código de registro para facturación electrónica')
    country_code = fields.Char(string="Abreviatura del país")

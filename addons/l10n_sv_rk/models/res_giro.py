from odoo import fields, models, api, exceptions, _


class ResActividadEconomica(models.Model):
    _name = "res.giro"
    _description = "Actividades economicas en El Salvador"

    name = fields.Char(string="Nombre de actividad económica", help="Indique a que actividad económica o giro pertenece")
    code = fields.Char(string="Código", help='Código de actividad')

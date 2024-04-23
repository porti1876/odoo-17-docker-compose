from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re
from . import res_partner_sv


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    document_dui = fields.Char(string="DUI")
    document_nit = fields.Char(string="NIT")
    document_tipo_afp = fields.Selection(string="Tipo de AFP", selection=[
        ('confia', 'Confia'),
        ('crecer', 'Crecer'),
        ('unidad de pensiones del ISSS', 'Unidad de pensiones del ISSS'),
        ('IPSFA', 'IPSFA'),
        ('otros', 'Otros'),
    ])
    document_num_afp = fields.Char(string="Número de AFP")
    document_num_isss = fields.Char(string="Número de ISSS")

    # _sql_constraints = [
    #     ('dui_uniq', 'unique (document_dui)', 'El DUI ingresado ya existe en la base de datos')
    # ]

    # @api.onchange('document_dui')
    # def validate_dui(self):
    #     if self.document_dui:
    #         match = re.match('^\+?[0-9]{8}[-][0-9]{1}$', self.document_dui)
    #         if match == None:
    #             raise ValidationError(
    #                 'Número de DUI inválido. Intente nuevamente siguiendo el siguiente patrón:  12345678-9')

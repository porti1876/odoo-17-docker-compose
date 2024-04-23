from odoo import models, fields,api,_
import string
import random

class GenerateSuperPass(models.TransientModel):
    _name = "super.password"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Generar master admin"
    
    name=fields.Char(string="nombre")
    contrasena_generada = fields.Char(string='Contraseña Generada', size=16, readonly=True)
    @api.model
    def generar_contrasena(self):
        # Caracteres permitidos: letras minúsculas, mayusculas y  dígitos
        caracteres_permitidos = string.ascii_lowercase + string.digits + string.ascii_uppercase

        # Generar una contraseña de 16 caracteres
        longitud = 16
        contrasena = ''.join(random.choice(caracteres_permitidos) for i in range(longitud))

        return contrasena

    def generar_guardar_contrasena(self):
        # Generar la contraseña
        nueva_contrasena = self.generar_contrasena()

        # Guardar la contraseña generada en el campo
        self.contrasena_generada = nueva_contrasena
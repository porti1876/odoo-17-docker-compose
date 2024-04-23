# -*- coding: utf-8 -*-


from odoo import models, fields, api,_
from odoo.exceptions import UserError
import requests
class DelProject(models.TransientModel):
    _name="delele.projects"
    _inherit = ['mail.thread']
    _description ="Eliminar proyectos"
    
    name = fields.Char(string="nombre")
    project= fields.Selection(selection="digitalocean_projec", string="Elegir proyecto a eliminar")
    
    
    
    
    @api.model
    def digitalocean_projec(self):
        """
        Obtiene los proyectos o carpetas donde se almacenan los droplets o ip
        """
        tk=self.env['ln10_sv_saas.droplets']
        token= tk.obtener_token_digi()     
    
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        url = 'https://api.digitalocean.com/v2/projects'

        response = requests.get(url, headers=headers)
    
        if response.status_code == 200:
            proyectos = response.json()['projects']
            return [(proyecto['id'],proyecto['name']) for proyecto in proyectos]
        else:
            print(f'Error al obtener los proyectos: {response.status_code}')
            return []
    
    def eliminar_proyecto_digital(self):
        company = self.env['res.company'].browse(1)
        token_digi = company.token_digi
        if not token_digi:
            raise UserError("El campo 'token_digi' no tiene un valor asignado en res.company.")
        url = f"https://api.digitalocean.com/v2/projects/{self.project}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token_digi}"
        }

        try:
            response = requests.delete(url, headers=headers)
            response.raise_for_status()  # Lanza una excepción si la solicitud no fue exitosa

            message = _("Proyecto con ID %s eliminado exitosamente.") % self.project
            self.message_post(body=message, message_type="notification")
        except requests.exceptions.RequestException as e:
            raise UserError("Error al eliminar el proyecto:", str(e))
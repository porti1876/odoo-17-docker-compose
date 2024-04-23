# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from odoo.exceptions import UserError
import requests

PURPOSE=[('digitalocean', 'Just trying out DigitalOcean'),
        ('class_project', 'Class project / Educational purposes'),
        ('website_blog', 'Website or blog'),
        ('web_app', 'Web Application'),
        ('service_api', 'Service or API'),
        ('mobile_app', 'Mobile Application'),
        ('ml_ai_data', 'Machine learning / AI / Data processing'),
        ('iot', 'IoT'),
        ('dev_tooling', 'Operational / Developer tooling'),
        ('other','Otro')]

ENVIRO=[('development', 'Development'),
        ('staging', 'Staging'),
        ('production', 'Production')]

class AddProjects(models.TransientModel):
    _name = "projects.add"
    _description = "Agregar Proyecto o Carpeta DigitalOcean "
    
    name = fields.Char(string="Nombre",required=True)
    descripcion = fields.Char(string="Descripcion")
    objetivo = fields.Selection(selection=PURPOSE, string="Objetivo", required=True)
    otro = fields.Char(string="Especificar objetivo")
    entorno = fields.Selection(selection=ENVIRO, string="Elegir El entorno de los recursos del proyecto")
    
    
    
    def create_projetc(self):
        
        company = self.env['res.company'].browse(1)
        token_digi = company.token_digi
        if not token_digi:
            raise UserError("El campo 'token_digi' no tiene un valor asignado en res.company.")
        url = 'https://api.digitalocean.com/v2/projects'
        headers = {
                'Authorization': f'Bearer {token_digi}',
                'Content-Type': 'application/json'}
        
        if self.objetivo == 'other':
            purpose = self.otro
        else:
            purpose = dict(self._fields['objetivo'].selection).get(self.objetivo)
        
        data = {
        "name": self.name,
        "description":None if not self.descripcion else self.descripcion,
        "purpose":purpose,
        "environment": None if not self.entorno else self.entorno
    }
    
        response = requests.post(url, headers=headers, json=data)
    
        if response.status_code == 201:
            print('Creado con exito.')
        else:
            print('Error. Status code:', response.status_code)
            print('Response:', response.json())
        
        
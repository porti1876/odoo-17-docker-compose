# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import digitalocean
import requests


class DeleteKeys(models.TransientModel):
    _name = "dele.keys"
    _description = "Eliminar Public Keys"
    
    name=fields.Char(string="Nombre")
    public_keys=fields.Selection(selection="get_ssh_keys", string="Selecciona SSH Kyes a eliminar")
    
    
    @api.model
    def get_ssh_keys(self):
        """
        Obtiene todas las llaves o claves ssh
        """
        company = self.env['res.company'].browse(1)
        token_digi = company.token_digi
        if not token_digi:
            raise UserError("El campo 'token_digi' no tiene un valor asignado en res.company.")     
        manager = digitalocean.Manager(token=token_digi)
     
        keys = manager.get_all_sshkeys()
      
        return [(key.fingerprint, key.name) for key in keys]
    
    def delete_keys(self):
        url = f"https://api.digitalocean.com/v2/account/keys/{self.public_keys}"
        company = self.env['res.company'].browse(1)
        token_digi = company.token_digi
        if not token_digi:
            raise UserError("El campo 'token_digi' no tiene un valor asignado en res.company.")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token_digi}"
            }

        try:
            response = requests.delete(url, headers=headers)
            response.raise_for_status()  
            print("Clave SSH eliminada exitosamente.")
        except requests.exceptions.HTTPError as err:
            print(f"Error al eliminar la clave SSH: {err}")
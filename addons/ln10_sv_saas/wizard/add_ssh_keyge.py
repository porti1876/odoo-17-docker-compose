# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
import requests
import os
from odoo.exceptions import UserError
class AddKeyGet(models.TransientModel):
    _name ="add.keyget"
    _description= "añadir ssh key"
    
    name= fields.Char(string="Nombre")
    public_key=fields.Char(string="public key")
    
    def add_keys(self):
        """
        Funcion para añadir la clave ssh key
        """
        try:
            company = self.env['res.company'].browse(1)
            token_digi = company.token_digi
            if not token_digi:
                raise UserError("El campo 'token_digi' no tiene un valor asignado en res.company.")

            url = "https://api.digitalocean.com/v2/account/keys"
        
            headers = {
                'Authorization': f'Bearer {token_digi}',
                'Content-Type': 'application/json' }
            data = {
                "public_key": self.public_key,
                "name": self.name }

            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 201:
                response_json = response.json()
                if 'ssh_key' in response_json:
                    ssh_key = response_json['ssh_key']
                    print(f"SSH Key ID: {ssh_key['id']}")
                    print(f"SSH Key Fingerprint: {ssh_key['fingerprint']}")
                    print(f"SSH Key Public Key: {ssh_key['public_key']}")
                    print(f"SSH Key Name: {ssh_key['name']}")
            elif response.status_code == 422:
                response_json = response.json()
                if 'message' in response_json:
                    error_message = response_json['message']
                    raise UserError(error_message)
                else:
                    print("Error al procesar la solicitud.")
               
            else:
                print(f"La solicitud no fue exitosa. Código de respuesta: {response.status_code}")
        
        except UserError as e:
                raise UserError(f"Error del usuario: {str(e)}")
        
        except ConnectionError as e:
            raise ConnectionError(f"Error de conexión: {str(e)}")
        
        except TimeoutError as e:
            raise TimeoutError(f"Error de tiempo de espera: {str(e)}")
        
        except Exception as e:
            raise Exception(f"Error desconocido: {str(e)}")

# -*- coding: utf-8 -*-

from odoo import models,api,_,fields
import paramiko
from odoo.exceptions import UserError
import shutil
import subprocess
import logging
import io

_logger = logging.getLogger(__name__)

class CopyFile(models.TransientModel):
    _name = 'craete.instancia'
    _description = 'Copiar archivo instancias'
    
    name = fields.Char(string="nombre", default="root",help='campo username para conectarse a ssh')
    servidor = fields.Many2one('ln10_sv_saas.droplets', 'IP')
    sshkeys=fields.Many2one('add.pkey.rskay', 'clave privada', help='campo ssh')
    pkey_private=fields.Text(related='sshkeys.pkey_private', string='pkey private', readonly=True)
    password_pkey=fields.Char(related='sshkeys.password_pkey', string='password pkey', readonly=True)
    ruta_cp =fields.Char(string="nombre de archivo de configuracion", default="/etc/odoo.conf", help='Archivo de configuracion .conf')
    ruta_fl = fields.Char(string="nombre del archivo sistema", default="odoo", help='archivo de systemctl , para detener, para o reiniciar instancia¡')
    
    
    def cp_file(self):
         
        HOST=self.servidor.ip_server
        USERNAME = self.name
        PORT=22
        ruta_archivo_origen = "/etc/odoo-server.conf"
        destino = self.ruta_cp
       
        private_key = paramiko.RSAKey(file_obj=io.StringIO(self.pkey_private),password=self.password_pkey)

        
        datos = dict(hostname=HOST,port=PORT , username=USERNAME, pkey=private_key)
        _logger.info(datos)
        try:
        # Establecer la conexión SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                     
            ssh.connect(**datos)
      
            comando_cp = f"cp {ruta_archivo_origen} {destino}"
            stdin, stdout, stderr = ssh.exec_command(comando_cp)
                       
            chown_command = "chown odoo:odoo {}".format(self.ruta_cp)
            stdin, stdout, stderr = ssh.exec_command(chown_command)
            
            remote_command_initd = "cd /etc/init.d && cp odoo-server {}".format(self.ruta_fl)
            stdin, stdout, stderr = ssh.exec_command(remote_command_initd)
            
            comando_cp_file = "cd /odoo && cp -rp odoo-server {}".format(self.ruta_fl)
            stdin, stdout, stderr = ssh.exec_command(comando_cp_file)

            exit_status = stdout.channel.recv_exit_status()

            if exit_status == 0:
                title = _("¡Excelente!")
                message = _("Instancia creada!")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': title,
                        'message': message,
                        'sticky': False, } }
            else:
               raise UserError(f"Error. Código de salida: {exit_status}")
       
        except paramiko.AuthenticationException:
            _logger.exception("Error de autenticación. Verifica las credenciales SSH.")
        except paramiko.SSHException as e:
            _logger.exception("Error al establecer la conexión SSH:", str(e))
        except Exception as e:
            _logger.exception("Ocurrió un error:", str(e))
        finally:
            ssh.close()
    
    
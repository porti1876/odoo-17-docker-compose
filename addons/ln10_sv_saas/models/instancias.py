# -*- coding: utf-8 -*-
from odoo import models, fields, api,_ ,exceptions
from odoo.exceptions import UserError, ValidationError
import paramiko
from paramiko import SSHException, AuthenticationException
import digitalocean
import sys
import getpass
import subprocess
from passlib.hash import pbkdf2_sha256
import bcrypt
import re
import os
import time
import io
import configparser
import logging
from cryptography.fernet import Fernet


_logger = logging.getLogger(__name__)


class InstanciasSaas(models.Model):
    _name = "ln10_sv_saas.instancias"
    _inherit =["mail.activity.mixin","mail.thread"]
    _description  = "Instancias IP"
    
    name=fields.Char(string="Nombre de la instancia")#default=lambda self: ('New'))
    archivo_config=fields.Text("Archivo de configuracion")
    #logs=fields.Char("Terminal")
    service=fields.Char(string="Service")
   # servidor=fields.Many2one('rocket_server.register_server',string="Servidor",store=True,ondelete="cascade")
   # ip_server=fields.Char(string="IP", related='servidor.ip_server')
    user_bd=fields.Char(string="User database")
    passw_bd=fields.Char(string="Password database", password=True)
    currency_id = fields.Many2one('res.currency', string='Currency')
    #planes_ids=fields.Many2one('rocket_planes.rocket_planes' ,string="Planes de Pago",store=True)
    #precio=fields.Monetary(string="Plan de pago", related='planes_ids.precio', currency_field="currency_id")
    aliens=fields.Char(string="aliens")
    cliente=fields.Many2one('res.partner', string="Cliente")
    state = fields.Selection([('draft', 'Borrador'), 
                             ('posted', 'Confirmado'),
                             ('aplicar','Aplicado'),
                             ('cancel', 'Cancelled'),], 
                             default='draft', string='Estado', required=True)
    #name_id=fields.Many2one('rocket_instancias.res_instancia')
    master_key = fields.Char('Password ', readonly=True)
    posted_before = fields.Boolean(copy=False)
    is_edit=fields.Boolean(default=True)
    is_edit_apli = fields.Boolean(default=True)
    
    # Campos del archivo .conf
    is_password = fields.Boolean(string="Mostrar contraseña")
    is_password = fields.Boolean(string="Mostrar contraseña", default=False)
    nameConf=fields.Char(string="file name", readonly=True)
    master_password=fields.Char(string="admin master")
    htt_port = fields.Char(string="http port")
    db_host=fields.Char(string="db host")
    db_port = fields.Char(string="db port")
    db_user = fields.Char(string="db user")
    db_password = fields.Char(string="db password")
    proxy_mode = fields.Boolean(default=True)
    logfile = fields.Char(string="logfile")
    xmlrpc_port=fields.Char(string="xmlrpc port")
    addons_path = fields.Char(string="addons path")
    
    longpolling_port = fields.Boolean(default=False)
    gevent_port=fields.Char(default="8072")
    
    #workers=fields.Integer(default=0)
    limit_time_real=fields.Integer(string="limit time real",default=120)#Tiempo real máximo permitido por solicitud (predeterminado 120)
    limit_time_cpu=fields.Integer(default=60) #Tiempo máximo de CPU permitido por solicitud (predeterminado 60)
    limit_time_real_cron=fields.Integer(default=0) #Tiempo real máximo permitido por trabajo cron. (predeterminado: --limit-time-real). Establezca en 0 para que no haya límite.
    
    
    
    #ssh conexion
    hostName=fields.Many2one('ln10_sv_saas.droplets',string="Host",store=True,ondelete="cascade")
    port_host=fields.Integer(string="PORT",default=22)
    userNameSsh=fields.Char(string="username ssh", default="root")
    clave_privada=fields.Text(string="private key")
    passwordPkey=fields.Char(string="private password")
    
    shh_ids=fields.Many2one('add.pkey.rskay', string="pkey private")
    password_pkey = fields.Char(string="Password pkey", related='shh_ids.password_pkey', readonly=True)
    ip_server=fields.Char(string="IP", related='hostName.ip_server', readonly=True)

    @api.onchange('shh_ids')
    def _onchange_ssh_ids(self):
        if self.shh_ids:
            self.password_pkey = self.shh_ids.password_pkey
        else:
            self.password_pkey = False





    
    
   
    ssh_keys = fields.Selection(selection='get_ssh_key', string='Clave SSH',store=True) 
    
    def conectar_ssh_id(self):
        
        pkey_priva=self.shh_ids.pkey_private
        
       
        private_keys=paramiko.RSAKey(file_obj=io.StringIO(pkey_priva),password=self.password_pkey)
        
        
        datos=dict(hostname=self.ip_server, port=self.port_host, username=self.userNameSsh, pkey=private_keys)
        _logger.info(datos)    
        ssh  = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
        try:
            ssh.connect(**datos)
            action=self.search([],limit=1)
            
            return {
                'type':'ir.actions.client',
                'tag':'display_notification',
                'params':{
                    'title':_('Conexion con exito!!!'),
                    'message':'%s',
                    'links':[{
                        'label':self.ip_server,
                        'url':f'#action={action}&id={self.id}&model={self._name}',
                    }]
                    
                }
            }
        except paramiko.AuthenticationException:
            raise exceptions.ValidationError("Error de autenticación. Verifica las credenciales de SSH.")
        except paramiko.SSHException as e:
            raise exceptions.ValidationError(f"Error SSH: {str(e)}")
        except Exception as e:
            raise exceptions.ValidationError(f"Ocurrió un error: {str(e)}")
        finally:
            ssh.close()

    
    
    def edit_remote_file(self):
    
            pkey_priva = self.shh_ids.pkey_private
            private_keys = paramiko.RSAKey(file_obj=io.StringIO(pkey_priva), password=self.password_pkey)
    
            datos = dict(hostname=self.ip_server, port=self.port_host, username=self.userNameSsh, pkey=private_keys)
            _logger.info(datos)
    
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
            try:
                # Crear una conexión SSH
                client.connect(**datos)

                config_file_path = f'/etc/{self.nameConf}'
        
                new_config = {
                    'admin_passwd': self.master_password,
                    'http_port': self.htt_port,
                    'db_host': self.db_host,
                    'db_port': self.db_port,
                    'db_user': self.db_user,
                    'db_password': self.db_password,
                    'proxy_mode': self.proxy_mode,
                    'xmlrpc_port': self.xmlrpc_port,
                    'longpolling_port':self.longpolling_port,
                    'gevent_port':self.gevent_port,
                    'limit_time_real':self.limit_time_real,
                    'limit_time_cpu':self.limit_time_cpu,
                    'limit_time_real_cron':self.limit_time_real_cron,
                    'logfile': self.logfile,
                    'addons_path': self.addons_path,
        }

                stdin, stdout, stderr = client.exec_command(f"cat {config_file_path}")
                current_content = stdout.read().decode('utf-8')

                lines = current_content.split('\n')
                updated_lines = []

                for line in lines:
                    stripped_line = line.strip()
                    key_value_pair = stripped_line.split('=', 1)
                    if len(key_value_pair) == 2:
                        key = key_value_pair[0].strip()
                        value = key_value_pair[1].strip()
                        if key.lower() in new_config:
                            updated_lines.append(f"{key} = {new_config[key.lower()]}")
                        else:
                            updated_lines.append(line)
                    else:
                        updated_lines.append(line)

                for key, value in new_config.items():
                    key_lower = key.lower()
                    if not any(line.lower().startswith(key_lower) for line in updated_lines):
                        updated_lines.append(f"{key_lower} = {value}")

                updated_content = '\n'.join(updated_lines)

                stdin, stdout, stderr = client.exec_command(f"echo '{updated_content}' > {config_file_path}")
                if stdout.channel.recv_exit_status() == 0:
                    title = _("Archivo")
                    message = _("Actualizado correctamente")
                    return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': title,
                    'message': message,
                    'sticky': False,
                }
            }
                else:
                    error_message = stderr.read().decode('utf-8')
                    _logger.error(f"Error al actualizar el archivo de configuración: {error_message}")

            except paramiko.AuthenticationException:
                raise exceptions.ValidationError("Error de autenticación. Verifica las credenciales de SSH.")
            except paramiko.SSHException as e:
                raise exceptions.ValidationError(f"Error SSH: {str(e)}")
            except Exception as e:
                raise exceptions.ValidationError(f"Ocurrió un error: {str(e)}")
            finally:
                client.close()

          
       
    
  
    @api.model
    def get_ssh_key(self):
        """
        Obtiene todas las llaves o claves ssh
        """
        company = self.env['res.company'].browse(1)
        token_digi = company.token_digi
        if not token_digi:
            raise UserError("El campo 'token_digi' no tiene un valor asignado en res.company.")
        
       # token_di = self.obtener_token_digi()        
        manager = digitalocean.Manager(token=token_digi)
     
        keys = manager.get_all_sshkeys()
      
        return [(key.fingerprint, key.name) for key in keys]
   
    
    #inscriptador de la contraseña
    @api.onchange('db_password')
    def encrypt_password(self):    
       if isinstance(self.db_password,str):
            pwd = self.db_password.encode('utf-8')
            salt = bcrypt.gensalt()
            self.db_password = bcrypt.hashpw(pwd, salt)

    @api.model
    def check_password(self, record_id, db_password):
        record = self.browse(record_id)
        if record and record.db_password:
            return bcrypt.checkpw(db_password.encode('utf-8'), record.db_password.encode('utf-8'))
        return False
   
    @api.onchange('hostName')
    def actualizar_clientes_server(self):  
        if self.hostName:
            if self.hostName.clientes_server >= self.hostName.maximos_clientes:
                raise UserError("Espacio insuficiente, crea un nuevo servidor")
            else:
               self.hostName.clientes_server += 1
    
        

    def reset_to_draft(self):
       for record in self:
            record.write({'state': 'draft',
                          'is_edit_apli':False
                          })
  
       
      
    #hacer que no se repita el nombre de la instancia
   # @api.constrains('name')
   # def _check_unique_name_per_client(self):
   #     for record in self:
    #        duplicate_records = self.search([('name', '=', record.name), ('id', '!=', record.id)])
     #       if duplicate_records:
      #          raise models.ValidationError("Error, Nombre de instancia ya registrada. Vuelve a intentarlo")
    
class SshPkey(models.Model):
    _name = "add.pkey.rskay"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Clave Privada ssh"
    
    name = fields.Char(string="Nombre")
    pkey_private = fields.Text(string="Clave privada")
    password_pkey=fields.Char(string="password pkey")
    username_ssh=fields.Char(string="username ssh", default="root")
    edit = fields.Boolean(default=True)
    
    
    def create_dt(self):
        existing_record = self.search([
            ('name', '=', self.name),  
            ('pkey_private', '=', self.pkey_private),
            ('username_ssh','=',self.username_ssh),
            ('password_pkey', '=', self.password_pkey)
        ])
        
        if not existing_record:
            self.create({
                'name': self.name,
                'pkey_private': self.pkey_private,
                'password_pkey': self.password_pkey,
                'username_ssh':self.username_ssh,
                'edit':False
            })
    
    
   # @api.onchange('pkey_private')
   # def encrypt_private_key(self):
    #    if isinstance(self.pkey_private, str):
     #       key = Fernet.generate_key()  
      #      cipher_suite = Fernet(key)
      #      encrypted_pkey = cipher_suite.encrypt(self.pkey_private.encode())
      #      self.pkey_private = encrypted_pkey
            
    # def decrypt_private_key(self):
      #  if self.pkey_private:
      #      cipher_suite = Fernet(self.pkey_private)
      #      decrypted_pkey = cipher_suite.decrypt(self.pkey_private).decode()
        #    return decrypted_pkey
       # return ""
       
  
  
   
class FileInstancias(models.Model):
    _name ="files.instancias"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description ="Extraer instancias"
    
    name =fields.Char(related='host.name',string="nombre", readonly=True,ondelete='cascade')
    shh_ids=fields.Many2one('add.pkey.rskay', string="pkey private")
    host=fields.Many2one('ln10_sv_saas.droplets', 'servidor')
    ip_server= fields.Char(related='host.ip_server' ,string="IP", ondelete='cascade', readonly=True)
    username=fields.Char(string="username ssh",default="root")
    port=fields.Integer(string="PORT", default=22)
    pkey_private =fields.Text(string="Clave privada ssh",related='shh_ids.pkey_private', readonly=True)
    password_pkey = fields.Char(string="Password Pkey", related='shh_ids.password_pkey', readonly=True)
   
    @api.onchange('shh_ids')
    def _onchange_ssh_ids(self):
        if self.shh_ids:
            self.password_pkey = self.shh_ids.password_pkey
        else:
            self.password_pkey = False
    
    
    def conectar_ssh(self):
        clave=self.shh_ids.pkey_private
          
        private_key = paramiko.RSAKey(file_obj=io.StringIO(clave), password=self.password_pkey)
        datos = dict(hostname=self.ip_server, port=self.port, username=self.username, pkey=private_key)
        _logger.info(datos)
        ssh  = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
        try:
            ssh.connect(**datos)
              
            title = _("¡Prueba de conexión exitosa!")
            message = _("Todo parece estar correctamente configurado!")
            return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': title,
                        'message': message,
                        'sticky': False, } }
                         
        except paramiko.AuthenticationException:
            raise exceptions.ValidationError("Error de autenticación. Verifica las credenciales de SSH.")
        except paramiko.SSHException as e:
            raise exceptions.ValidationError(f"Error SSH: {str(e)}")
        except Exception as e:
            raise exceptions.ValidationError(f"Ocurrió un error: {str(e)}")
        finally:
            ssh.close()

    def update_from_remote_confs(self):
        for record in self:
            remote_folder = "/etc/"
        #    clave = i.shh_ids.pkey_private
            private_key = paramiko.RSAKey(file_obj=io.StringIO(record.pkey_private), password=record.password_pkey)
            datos = dict(hostname=record.ip_server, port=record.port,username=record.username, pkey=private_key)
            _logger.info(datos)
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            try:
                client.connect(**datos)
                stdin, stdout, stderr = client.exec_command(f"grep -rl 'addons_path' {remote_folder}")

                conf_files = stdout.read().decode('utf-8').splitlines()

                for conf_file_path in conf_files:
                    try:
                        self._update_from_conf_file(client, conf_file_path)
                    except Exception as e:
                           _logger.error(
                        f"Error al procesar el archivo conf: {conf_file_path}. Error: {e}")
            except Exception as e:
                 _logger.error(
                f"Error al conectarse a la IP {record.ip_server}. Error: {e}")
            finally:
                client.close()
    def _update_from_conf_file(self, client, conf_file_path):
        stdin, stdout, stderr = client.exec_command(f"cat {conf_file_path}")
        conf_content = stdout.read().decode('utf-8')

        conf_values = {}
        for line in conf_content.split('\n'):
            if '=' in line:
                key, value = line.strip().split('=')
                conf_values[key.strip()] = value.strip()

        if 'addons_path' in conf_values:
          
            name_conf = os.path.basename(conf_file_path)
     
            validateFile = self.env['ln10_sv_saas.instancias'].search([
                ('nameConf', '=', os.path.basename(conf_file_path)),
                ('db_user','=', conf_values.get('db_user', ''))
               
            ])

            if not validateFile:
                new_tda = self.env['ln10_sv_saas.instancias'].create({
                    'master_password': conf_values.get('admin_passwd', ''),
                                'htt_port': int(conf_values.get('http_port', 0)),
                                'db_host': conf_values.get('db_host', ''),
                                'db_port': int(conf_values.get('db_port', 5432)),
                                'db_user': conf_values.get('db_user', ''),
                                'db_password': conf_values.get('db_password', ''),
                                'proxy_mode': conf_values.get('proxy_mode', '').lower() == 'true',
                                'xmlrpc_port': int(conf_values.get('xmlrpc_port', 0)),
                                'longpolling_port':conf_values.get('longpolling_port','').lower() == 'false',
                                'gevent_port':conf_values.get('gevent_port',''),
                                'limit_time_real':int(conf_values.get('limit_time_real',120)),
                                'limit_time_cpu':int(conf_values.get('limit_time_cpu',60)),
                                'limit_time_real_cron':int(conf_values.get('limit_time_real_cron',0)),
                                'logfile': conf_values.get('logfile', ''),
                                'addons_path': conf_values.get('addons_path', ''),
                                'nameConf': os.path.basename(conf_file_path),
                    
                })
                _logger.info("Datos Guardados")
                  
            else:
                _logger.warning(f"Configuración con htt_port  y nameConf  ya procesada.") 

    @api.model
    def update_fuction(self):
        function_id=self.search([])      
        for record in function_id:
            record.update_from_remote_confs()        
        return True
    
    
    
class ListSystemctl(models.Model):
    _name = "listas.systemctl"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Lista de archivos de systemctl"
    
    name = fields.Char(string="nombre")
    file_systemctl=fields.Text(string="Archivo systemctl", help='Archivo systemctl detener, para o reinicia instancia' )
    ip_server=fields.Char(string="IP")
    port=fields.Char(string="Port", default=22)
    username=fields.Char(string="Username ssh", default="root")
    ssh_ids=fields.Many2one('add.pkey.rskay','ssh pkey private')
    pkey_private=fields.Text(related='ssh_ids.pkey_private',string="clave privada ssh", readonly=True)
    password_pkey=fields.Char(related='ssh_ids.password_pkey',string="password pkey", readonly=True)
    
    
    def updte_file(self):      
        private_keys=paramiko.RSAKey(file_obj=io.StringIO(self.pkey_private),password=self.password_pkey)
        
        datos=dict(hostname=self.ip_server, port=self.port, username=self.username, pkey=private_keys)
        _logger.info(datos)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(**datos)
            config_file_path = f'/etc/init.d/{self.name}' 
            new_content = self.file_systemctl  
            
            stdin, stdout, stderr = client.exec_command(f"echo '{new_content}' > {config_file_path}")
            if stdout.channel.recv_exit_status() == 0:
                title = _("Systemctl!")
                message = _("Archivo actualizado")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': title,
                        'message': message,
                        'sticky': False, } }
            else:
                error_message = stderr.read().decode('utf-8')
                _logger.error(f"Error al actualizar el archivo de configuración: {error_message}")
            
            
            
        except paramiko.AuthenticationException:
            raise exceptions.ValidationError("Error de autenticación. Verifica las credenciales de SSH.")
        except paramiko.SSHException as e:
            raise exceptions.ValidationError(f"Error SSH: {str(e)}")
        except Exception as e:
            raise exceptions.ValidationError(f"Ocurrió un error: {str(e)}")
        finally:
            client.close()

    def activar(self):
        private_keys=paramiko.RSAKey(file_obj=io.StringIO(self.pkey_private),password=self.password_pkey)
        
        datos=dict(hostname=self.ip_server, port=self.port, username=self.username, pkey=private_keys)
        _logger.info(datos)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(**datos)
                    
            stdin, stdout, stderr = client.exec_command(f"systemctl enable {self.name}")
            if stdout.channel.recv_exit_status() == 0:
                title = _("Systemctl!")
                message = _("Activado")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': title,
                        'message': message,
                        'sticky': False, } }
            else:
                error_message = stderr.read().decode('utf-8')
                _logger.error(f"Error al actualizar el archivo: {error_message}")
            
            
            
        except paramiko.AuthenticationException:
            raise exceptions.ValidationError("Error de autenticación. Verifica las credenciales de SSH.")
        except paramiko.SSHException as e:
            raise exceptions.ValidationError(f"Error SSH: {str(e)}")
        except Exception as e:
            raise exceptions.ValidationError(f"Ocurrió un error: {str(e)}")
        finally:
            client.close()
    def _connect(self):
        private_keys = paramiko.RSAKey(file_obj=io.StringIO(self.pkey_private), password=self.password_pkey)
        datos = dict(hostname=self.ip_server, port=self.port, username=self.username, pkey=private_keys)
        _logger.info(datos)
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(**datos)
        return client
    
    def _execute_command(self, client, command):
        stdin, stdout, stderr = client.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        return exit_status, stdout, stderr
    
    def _handle_result(self, exit_status, action):
        if exit_status == 0:
            title = _(f"{self.name}")
            message = _(action)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': title,
                    'message': message,
                    'sticky': False,
                }
            }
       
    def perform_systemctl_action(self, action):
        client = self._connect()
        try:
            command = f"systemctl {action} {self.name}"
            exit_status, stdout, stderr = self._execute_command(client, command)
            return self._handle_result(exit_status, action)
        except paramiko.AuthenticationException:
            raise exceptions.ValidationError("Error de autenticación. Verifica las credenciales de SSH.")
        except paramiko.SSHException as e:
            raise exceptions.ValidationError(f"Error SSH: {str(e)}")
        except Exception as e:
            raise exceptions.ValidationError(f"Ocurrió un error: {str(e)}")
        finally:
            client.close()

    def startSystemctl(self):
        return self.perform_systemctl_action("start")
    
    def stopSystemctl(self):
        return self.perform_systemctl_action("stop")
    
    def restartSystemctl(self):
        return self.perform_systemctl_action("restart")
    

        
        
class FileSystemctl(models.Model):
    _name = "files.systemctl"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Extraer archivo systemctl"
    
    
    name=fields.Char(string="nombre ", related='servidores.name', readonly=True)
    shh_ids=fields.Many2one('add.pkey.rskay', string="pkey private",ondelete="cascade")
    servidores=fields.Many2one('ln10_sv_saas.droplets', 'IP',ondelete='cascade')
    ip_server=fields.Char(related='servidores.ip_server', string="Host", readonly=True)
    pkey_private=fields.Text(related='shh_ids.pkey_private', string='pkey private',readonly=True)
    password_pkey = fields.Char(string="Password Pkey", related='shh_ids.password_pkey', readonly=True)
    port=fields.Integer(string="PORT", default=22)
    username=fields.Char(string="username ssh", default="root")
    
    def update_file_systemctl(self):
        
        for i in self:
            remote_folder="/etc/init.d"
                  
            private_key = paramiko.RSAKey(file_obj=io.StringIO(i.pkey_private), password=i.password_pkey)
            datos = dict(hostname=i.ip_server, port=i.port, username=i.username, pkey=private_key)
            _logger.info(datos)
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        
            try:
                client.connect(**datos)
                stdin, stdout, stderr = client.exec_command(f"grep -rl 'Description: ODOO Business Applications' {remote_folder}")
        
                conf_files = stdout.read().decode('utf-8').splitlines()
                for conf_file_path in conf_files:
                    try:
                        validar_exis=self.env['listas.systemctl'].search([('name','=',os.path.basename(conf_file_path)),
                                                                         ('ip_server','=',i.ip_server)])
                        stdin, stdout, stderr = client.exec_command(f"cat {conf_file_path}")
                        conf_content = stdout.read().decode('utf-8')
                        if not validar_exis:
                            datos=self.env['listas.systemctl'].create({
                            'name':os.path.basename(conf_file_path),
                             'ip_server':i.ip_server,
                            'file_systemctl':conf_content
                        })
                    except Exception as e:
                        _logger.error(f"Error al procesar el archivo conf: {conf_file_path}. Error: {e}")
            except Exception as e:
                _logger.error(f"Error al conectarse a la IP {i.ip_server}. Error: {e}")
            finally:
                client.close()
                
    @api.model
    def file_xtrta(self):
        record_ids=self.search([])
        
        for xtra in record_ids:
            xtra.update_file_systemctl()
        
        return True
    
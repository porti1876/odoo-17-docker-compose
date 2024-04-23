# -*- coding: utf-8 -*-

from odoo import models, fields, api,_,exceptions
#from digitalocean import Manager
from pexpect import pxssh

import digitalocean
import time
from odoo.exceptions import UserError, ValidationError
import subprocess
import os
import json
import requests
from odoo import http
from odoo.http import request
import paramiko
import logging
import pexpect
import io
import re
import base64
import sys


from pydo import Client
from azure.core.exceptions import ClientAuthenticationError

PROVEEDORES=[('digital','Digital Ocean'),
             ('ovh','OVH Cloud'),
             ('peramx','peramix'),
             ('aws','Amazon Web Services'),
             ('linode','Linode LLC'),
             ('azure','Microsoft Azure'),
             ('google','Google Cloud')]

NEWYORK=[("nyc1","New York 1"),
         ('nyc2',"New York 2"),
         ('nyc3',"New York 3")]
SANFRANCISCO=[("sfo1","San Francisco 1"),
              ("sfo2","San Francisco 2"),
              ("sfo3","San Francisco 3")]
AMSTERDAM = [("ams2","Amsterdam 1"),
             ("ams3","Amsterdam 2")]
SINGAPORE = [("sgp1","Singapore 1")]
LONDON = [("lon1","London 1")]
FRANKFURT=[("fra1","Frankfurt")]
TORONTO =[("tor1","Toronto")]
BANGALORE=[("blr1","Bangalore")]
SYDNEY=[("syd1","Sydney")]
UBUNTU=[("ubuntu-22-10-x64","22.10 x64"),
        ("ubuntu-22-04-x64","22.04(LTS) x64"),
        ("ubuntu-20-04-x64","20.04(LTS) x64"),
        ("ubuntu-18-04-x64","18.04(LTS) x64")]

SLUG_REGULAR=[('s-1vcpu-512mb-10gb','$4/mo | 512 MB/1 CPU | 10 GB SSD Disk | 500 GB transfer'),('s-1vcpu-1gb','$6/mo | 1 GB/1 CPU | 25 GB SSD Disk  | 1000 GB transfer'),('s-1vcpu-2gb','$12/mo | 2 GB/1 CPU | 50 GB SSD Disk | 2 TB transfer'),('s-2vcpu-2gb','$18/mo | 2 GB/2 CPU | 60 GB SSD Disk | 3 GB transfer'),('s-2vcpu-4gb',' $24/mo | 4 GB/2 CPU | 80 GB SSD Disk | 4 TB transfer '),('s-4vcpu-8gb','$48/mo | 8 GB/4 CPU | 160 GB SSD Disk | 5 TB transfer '),('s-8vcpu-16gb','$96/mo |  16 GB/8 CPU | 320 GB SSD Disk | 6 TB transfer')]
SLUG_PREMIUN_INTEL=[('s-1vcpu-1gb-intel','$8/mo | 1 GB/1 intel CPU | 35 GB NVMe SSDs | 1000 GB transfer'),('s-1vcpu-2gb-intel','$16/mo |  2 GB/1 intel CPU | 70 GB NVMe SSDs | 2 TB transfer'),('s-2vcpu-2gb-intel','$24/mo | 2 GB/2 intel CPU | 90 GB NVM w SSDs | 3 TB transfer'),('s-2vcpu-4gb-intel','$32/mo |  4 GB/ 2 intel CPUs | 120 GB NVMe SSDs | 4 TB transfer'),('s-4vcpu-8gb-intel','$48/mo | 8 GB/2 intel CPU | 160 GB NVMe SSDs | 5 TB transfer'),('s-4vcpu-8gb-240gb-intel','$64/mo | 8 GB/4 intel CPU | 240 GB NVMe SSDs | 6 TB transfer'),('s-8vcpu-16gb-intel','$96/mo | 16 GB/4 intel CPU | 320 GB NVMe SSD | 8 TB transfer'),('s-8vcpu-16gb-480gb-intel','$128/mo | 16 GB/4 intel CPU | 480 GB NVMe SSDs | 9 TB transfer'),('s-8vcpu-32gb-640gb-intel','$192/mo | 32 GB/4 intel CPU | 640 GB NVMe SSDs | 10 TB transfer')]
SLUG_PREMIUN_AMD=[('s-1vcpu-1gb-amd','$7/mo | 1 GB/1 AMD CPU | 25 GB NVMe SSDs | 1000 GB transfer '),('s-1vcpu-2gb-amd','$14/mo | 2 GB/1 AMD CPU | 50 GB NVMe SSDs | 2 TB transfer'),('s-2vcpu-2gb-amd','$21/mo | 2 GB/2 AMD CPU | 60 GB NVMe SSDs | 3 TB transfer '),('s-2vcpu-4gb-amd','$28/mo | 4 GB/2 AMD CPU | 80 GB NVMe SSDs | 4 TB transfer'),('s-4vcpu-8gb-amd','$42/mo | 8 GB/2 AMD CPU | 100 GB NVMe SSDs | 5 TB transfer'),('s-4vcpu-8gb-amd','$56/mo | 8 GB/4 AMD CPU | 160 GB NVMe SSDs | 5 TB transfer'),('s-4vcpu-16gb-amd','$84/mo | 16 GB/4 AMD CPU | 200 GB NVMe SSDs | 8 TB transfer'),('s-8vcpu-32gb-amd','$168/mo | 32 GB/8 AMD CPU | 400 GB NVMe SSDs | 10 TB transfer ')]


_logger = logging.getLogger(__name__)

class Droplest(models.Model):
    _name = "ln10_sv_saas.droplets"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Crear Droplets y actualizar"
    
    name= fields.Char(string="Nombre")
    maximos_clientes=fields.Integer("Maximos de clientes",default=10)
    clientes_server=fields.Integer("Cantidad de clientes utilizando el servidor", readonly=True,default=0, store=True)
    ip_server=fields.Char("IP")
    dominio_server=fields.Char("Dominio ")
    proveedores=fields.Selection(string="Proveedores",selection=PROVEEDORES)
    estado_server = fields.Selection(
        [('lleno', 'Espacios no disponibles'), ('disponibles', 'Espacios Disponibles')],
        string='Estado del servidor',
        store=True
        ,compute="_compute_estado_server"
    
    )
    active = fields.Boolean(string="Active", default=True)
    droplet_id=fields.Integer(string="droplet_id")
    estado_bool = fields.Char(readonly=True)
    estado=fields.Char(string="Estado", default="Cargando!!!")
    
    region=fields.Selection(string="Region", selection= NEWYORK + SANFRANCISCO + AMSTERDAM + SINGAPORE + LONDON + FRANKFURT + TORONTO + BANGALORE + SYDNEY,)
   
    image = fields.Selection(
        selection=UBUNTU,
        string='Sistema Operativo'
    )
    
    options = fields.Selection(string="CPU options", selection=[('slug_regular', 'Regular \nDisk type:SSD'),('slug_intel','Premium Intel \nDisk:NVMe SSD'),('slug_amd','Premium AMD \nDisk:NVMe SSD')])
   
   
    regular= fields.Selection(string="Regular \nDisk type: SSD", selection=SLUG_REGULAR)
    intel=fields.Selection(string="Premium Intel \nDisk: NVMe SSD",selection=SLUG_PREMIUN_INTEL)
    amd=fields.Selection(string="Premium AMD \nDisk: NVMe SSD", selection=SLUG_PREMIUN_AMD)
    proveedor_name = fields.Char('Proveedor ')

   
 
    metodo_autenticidad = fields.Selection(string="Metodo de autenticacion", selection=[('ssh','Clave SSH'),('pass','Password')],store=True)
    ssh_key = fields.Selection(selection='get_ssh_keys', string='Clave SSH',store=True)
    password=fields.Char(string="Password",store=True, help="""
                        1. La contraseña debe tener al menos 8 caracteres
                        2. La contraseña debe contener al menos 1 letra mayúscula (no puede ser ni el primer ni el último carácter)
                        3. La contraseña debe contener al menos 1 número.
                        4. La contraseña no puede terminar en un número o carácter especial.
                        """)
    
    lista_proyecto=fields.Selection(selection='digitalocean_projects', string="Projects")
    edit=fields.Boolean(default=True) # Campo para que no sea editable despues de guardar registro en base de datos
    
    serv = fields.Many2one('ln10_sv_saas.droplets','server')
    
    backups=fields.Boolean(string="backups")
    
    @api.model
    def obtener_token_digi(self):
        """
        Obtiene el token guardadO de DIgitalOcean, campo en res.company
        """
        company = self.env['res.company'].browse(1)
        token_digi = company.token_digi
        if not token_digi:
            raise UserError("El campo 'token_digi' no tiene un valor asignado en res.company.")
        return token_digi
    
    @api.model
    def get_ssh_keys(self):
        """
        Obtiene todas las llaves o claves ssh
        """
        token_di = self.obtener_token_digi()        
        manager = digitalocean.Manager(token=token_di)
     
        keys = manager.get_all_sshkeys()
      
        return [(key.fingerprint, key.name) for key in keys]
    @api.model
    def digitalocean_projects(self):
        """
        Obtiene los proyectos o carpetas donde se almacenan los droplets o ip
        """
        token = self.obtener_token_digi()
    
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
        
    @api.depends('clientes_server')
    def _compute_estado_server(self):
        for record in self:
            if record.clientes_server == 10:
                record.estado_server = 'lleno'
            else:
                record.estado_server = 'disponibles'
    
    @api.constrains('password')
    def _check_password(self):
        for record in self:
            if record.password:
                if len(record.password) < 8:
                    raise ValidationError("La contraseña debe tener al menos 8 caracteres.")
                if not any(char.isupper() for char in record.password[1:-1]):
                    raise ValidationError("La contraseña debe contener al menos 1 letra mayúscula (no puede ser ni el primer ni el último carácter).")
                if not any(char.isdigit() for char in record.password):
                    raise ValidationError("La contraseña debe contener al menos 1 número.")
                if record.password[-1].isdigit() or not record.password[-1].isalnum():
                    raise ValidationError("La contraseña no puede terminar en un número o carácter especial.")
               
    def create_dropletis(self):
        """
        Funcion para crear el servidor o droplet,
        cuando se presiona o ejecuta esta funcion,
        en la vista el status esta como 'apagado'
        lo cual indica que se esta creando en 
        Digital Ocean, el registro donde el status esta 
        como apagado se ejecuta la funcion delete_records para eliminar ese registro,
        ya cuando el droplet o ip esta lista , la funcion update_fields es la encargada
        de cargar y guardar los datos de la ip y presantarlos en la vista
        """
        
        token_digi = self.obtener_token_digi()
        headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token_digi
         }
        
        size_slug = ''
        if self.options == 'slug_regular':
            size_slug = self.regular
        elif self.options == 'slug_intel':
            size_slug = self.intel
        elif self.options == 'slug_amd':
            size_slug = self.amd
            
        autencidad = ''
        if self.metodo_autenticidad == "ssh":
            autencidad = self.ssh_key
        elif self.metodo_autenticidad == "pass":
            autencidad = self.password
       
        prject=self.lista_proyecto
        data = {
        "name": self.name,
        "region": self.region,
        "size": size_slug,
        "image": self.image,
        "ssh_keys": [autencidad],
        "backups": self.backups,
        }
        
        
       
        

        url = "https://api.digitalocean.com/v2/droplets"

        response = requests.post(url, headers=headers, data=json.dumps(data))
        
        

        if response.status_code == 202:
           title = _("Creado con èxito!")
           message = _("Se actualizara en unos momentos")
           return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'sticky': False,

            }}
        else:
            raise UserError(f"error : {response.status_code}")
    
    @api.model
    def delete_records(self):      
        """
        Cuando se ejecuta la funcion create_droplets, el campo ip_server no tiene dato, 
        ignorar, esta funcion se encargara de verificar si ese campo tiene datos,
        de lo contrario si no tiene nada lo eliminara, los datos actualizados los ejecutara
        la funcion update_fields encargada de actualizar y verificar si existe ese servidor       
        """
        
        records_to_delete = self.search([('ip_server', '=', False)])
        records_to_delete.unlink()
       
        return True
    @api.model
    def update_fields(self):
        """
        Funcion encargada de obtener los datos de digital ocean,
        la ip o droplet ya activo
        """
        # try:
        token_digi = self.obtener_token_digi()
        
       

        # Realiza la solicitud GET para obtener los droplets
        url = 'https://api.digitalocean.com/v2/droplets'
        headers = {'Authorization': f'Bearer {token_digi}'}
        response = requests.get(url, headers=headers)
        droplets_data = response.json().get('droplets', [])

        # Crea o actualiza los registros en la base de datos de Odoo
        DigitalOceanDroplet = self.search([])
        for droplet_data in droplets_data:
            external_id = droplet_data['id']
            droplet = DigitalOceanDroplet.search([('droplet_id', '=', external_id)])
            #for dro in droplet:
            if not droplet:
                    DigitalOceanDroplet.create({
                    'droplet_id':external_id,
                    'name': droplet_data['name'],
                    'ip_server':droplet_data['networks']['v4'][1]['ip_address'],
                    'estado':droplet_data['status'],
                    'region': droplet_data['region']['slug'],
                    'image': droplet_data['image']['slug'],
                 
                   # 'metodo_autenticidad': droplet_data['image']['slug'],
                    'edit':False
                 
                })
           # return True
     
    def delete_droplet(self):
        """
        Función para destruir el droplet
        """
        token_digi = self.obtener_token_digi()
        try:
            manager = digitalocean.Manager(token=token_digi)
            droplet = manager.get_droplet(self.droplet_id)
            droplet.destroy()         
            self.unlink()           
            
            self.search([('droplet_id', '=', self.id)]).unlink()

            
            title = _("Droplet")
            message = _("Eliminado con éxito!")
            return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'sticky': False,
            }}
            
            
            
           
        except Exception as e:
            raise UserError(f"Error deleting droplet: {e}")
        
class InstallScriptOdoo(models.Model):
    _name = "ln10_sv_saas.install"
    _inherit = ["mail.activity.mixin", "mail.thread"]
    _description ="Ejecutar Script Odoo"
    
    name = fields.Char(string="UserName", default="root")
    server = fields.Many2one('ln10_sv_saas.droplets', 'IP' ,ondelete='cascade')
    ip_server=fields.Char(string="Host", related='server.ip_server', readonly=True)
    ssh_ids=fields.Many2one('ln10_sv_saas.pkey','pkey private', ondelete="cascade")
    pkey_private=fields.Text(string="pkey private", related='ssh_ids.pkey_private', readonly=True)
    password_pkey = fields.Char(string="password pkey", readonly=True, related='ssh_ids.password_pkey')
    edit=fields.Boolean(default=True)
    port=fields.Integer(string="port", default=22)
    
   
    
    def view_script(self):
        """
        funcion para abrir y guardar cambios del script odoo
        """
       # tree_view_id = self.env.ref('ln10_sv_saas.edit_form').id """(tree_view_id, 'tree')"""
        form_view_id = self.env.ref('ln10_sv_saas.edit_form').id  
        action = {
            'type': 'ir.actions.act_window',
            'views': [(form_view_id, 'form')],
            'view_mode': 'tree,form',
            'name': _('Editar Script Odoo'),
            'res_model': 'ln10_sv_saas.edi',
        }
        return action
   
    
    
    
    def connect_to_server(self):
        self.ensure_one()
        #ssh = self.env[]
        
        if not self.ip_server:
            return None
        
        ip_servidor = self.ip_server
        ssh_username = self.name
        
        private_key = paramiko.RSAKey(file_obj=io.StringIO(self.pkey_private), password=self.password_pkey)
        
        datos = dict(hostname=ip_servidor, port=self.port, username=ssh_username, pkey=private_key)
        _logger.info(datos)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            client.connect(**datos)
            return client
        except paramiko.AuthenticationException as e:
            _logger.exception(f"{e}")
        except paramiko.SSHException as e:
           _logger.exception(f"{e}")
        
        return None
    
    def upgrade_ip(self):
        cliente=self.connect_to_server()
        if cliente:
            try:
                comando ="sudo apt upgrade && apt update"
                
                canal = cliente.exec_command(comando)
                
        # Crear una instancia de pexpect para interactuar con el canal SSH
                child = pexpect.spawn(canal)
        
                while True:
            # Esperar hasta que aparezca una solicitud
                    index = child.expect([
                                        "Do you want to continue? [Y/n]",   
                                        " What do you want to do about modified configuration file sshd_config?", 
                                        "Newer kernel available The currently running kernel version is 5.15.0-67-generic which is not the expected kernel version 5.15.0-79-generic. Restarting the system to load the new kernel will not be handled automatically, so you should ould consider rebooting enter","Which services should be restarted?", 
                                        pexpect.EOF, pexpect.TIMEOUT])
            
                    if index == 0:
                        child.sendline("Y")  # Presionar Enter
                    elif index == 1:
                        child.sendline()  # Responder a la solicitud de servicios a reiniciar
                    elif index == 2:
                        child.sendline()  # Responder "Y"
                    elif index == 4:
                        child.sendline()  # Salir si llegamos al final del script
                    elif index == 5:
                        # Manejar el caso de TIMEOUT si es necesario
                        break
                    elif index == 6:
                        pass
        
        # Capturar la salida mientras el script se ejecuta
                salida = child.before.decode('utf-8')
                _logger.info(salida)
        
        # Cerrar la conexión SSH
                canal.close()
                cliente.close()
        
                return salida
    
            except Exception as e:
                return str(e)
        
    
    def first_step(self):
        client = self.connect_to_server()
        if client:
            try:
                comando = "sudo wget https://raw.githubusercontent.com/Yenthe666/InstallScript/16.0/odoo_install.sh"
                stdin, stdout, stderr = client.exec_command(comando)
                
                
                salida = stdout.read().decode('utf-8')
                error = stderr.read().decode('utf-8')
            
                _logger.info(salida)
                _logger.error(error)
               
            finally:
                client.close()
    def second_step(self):
        client = self.connect_to_server()
        if client:
            try:
                comando = "sudo chmod +x odoo_install.sh"
                stdin, stdout, stderr = client.exec_command(comando)
                salida = stdout.read().decode('utf-8')
                error = stderr.read().decode('utf-8')
            
                _logger.info(salida)
                _logger.error(error)
            finally:
                client.close()
    def tree_step(self):     
        if not self.ip_server:
            return None
        
         
        ip_servidor = self.ip_server
        ssh_username = self.name
        
        private_key = paramiko.RSAKey(file_obj=io.StringIO(self.pkey_private), password=self.password_pkey)
        
        datos = dict(hostname=ip_servidor, port=self.port, username=ssh_username, pkey=private_key)
        _logger.info(datos)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
        client.connect(**datos)
        
        try:

            # Ejecutar el script y redirigir la entrada/salida estándar
            client.exec_command(f'sudo  ./odoo_install.sh')
        

        # Enviar respuestas automáticas a las preguntas del script
            client.send('')  # Presionar ENTER
        
            client.send('')  # Otra respuesta (si es necesario)
       
            client.send('y')  # Confirmar (si es necesario)
     

        # Obtener la salida del script
            output = client.recv(4096).decode('utf-8')
            print(output)

            client.close()
            client.close()

            _logger.info("exito")
        except Exception as e:
            _logger.exception(f"Error in pexpect: {e}")
        finally:
            client.close()            
    def installOdoo(self):
        if not self.ip_server:
            return None
        
         
        ip_servidor = self.ip_server
        ssh_username = self.name
        
        private_key = paramiko.RSAKey(file_obj=io.StringIO(self.pkey_private), password=self.password_pkey)
        
        datos = dict(hostname=ip_servidor, port=self.port, username=ssh_username, pkey=private_key)
        _logger.info(datos)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
        client.connect(**datos)
        
        
        try:
            # Ejecuta el script de instalación de Odoo
            command = "sudo  ./odoo_install.sh"
         
              # Comando para ejecutar el script .sh en el servidor remoto


    # Ejecutar el comando y establecer un canal interactivo
            _, stdout, stderr = client.exec_command(command)
            stdin = client.invoke_shell()

             # Esperar a que el comando termine
            while not stdout.channel.exit_status_ready():
                   # Si la solicitud de presionar Enter aparece en la salida, envía Enter
                if 'Press [ENTER] to continue or Ctrl-c to cancel.' in stdout.read().decode():
                    stdin.send('\n')
                if 'Which services should be restarted?   ' in stdout.read().decode():
                    stdin.send('\n')

                # Si la solicitud de confirmación aparece en la salida, envía 'y'
                if 'Do you want to continue? [Y/n]' in stdout.read().decode():
                    stdin.send('y')

    # Capturar y mostrar la salida y errores del comando
            output = stdout.read().decode()
            errors = stderr.read().decode()
            _logger.info("Salida:\n", output)
            _logger.error("Errores:\n", errors)
        except:
             _logger.exception('An exception occurred')

           

        
    def update_list(self):
        try:
        # Establecer la conexión SSH          
            ssh_command = f"ssh {self.name}@{self.ip_server}"
            _logger.info(ssh_command)
            proceso_ssh = pexpect.spawn(ssh_command, encoding='utf-8')
            
          

        
               # Esperar a que se establezca la conexión
            proceso_ssh.expect('\$')
         
            # Ejecutar el script remoto
            comando = f"sudo ./odoo_install.sh"
            _logger.info(comando)
            proceso_ssh.sendline(comando)
         
            # Esperar a que aparezca la cadena que solicita la interacción
            i = proceso_ssh.expect(["Press \[ENTER\] to continue or Ctrl-c to cancel.",
                                "Which services should be restarted?",
                                "Do you want to continue? \[Y/n\]",
                                pexpect.EOF])
        
            if i == 0:
                proceso_ssh.sendline()
            elif i == 1:
                proceso_ssh.sendline()
            elif i == 2:
                proceso_ssh.sendline("Y")
            elif i == 3:
                pass  # No es necesario hacer nada más si es el final del script
        
            # Esperar a que termine el script
            proceso_ssh.expect('\$')
        
             # Cerrar la conexión SSH
            proceso_ssh.sendline('exit')
            proceso_ssh.expect(pexpect.EOF)
        
            _logger.info("Script ejecutado en la máquina remota.")
        
        except pexpect.ExceptionPexpect as e:
            _logger.exception("Error:", str(e))
    def install_odoo(self):
        expected_responses = {
        "Press any key to continue": "y\n",
        "[ENTER] to continue or Ctrl-c to cancel": "\n",
        "[y/n]": "y\n",
        "[Y/n]": "y\n"}
        
        servidor = self.ip_server
        nam = self.name
        if not servidor:
        # Manejar el caso en que no se haya seleccionado un servidor
            return

        ip_servidor = servidor.ip_server
        ssh_username = nam
        
        private_key = paramiko.RSAKey(file_obj=io.StringIO(self.pkey_ssh),password=self.password_pkey)

        
          
        datos = dict(hostname=ip_servidor, port=22, username=ssh_username,pkey=private_key)
        _logger.info(datos)
    # Crear una instancia de cliente SSH
    
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        client.connect(**datos)
        try:
            
            channel = client.invoke_shell()

            commands = [

            "sudo ./odoo_install.sh"
        ]

            for cmd in commands:
                channel.send(cmd + "\n")
                output = ""

                while True:
                    if channel.recv_ready():
                        output += channel.recv(4096).decode("utf-8")

                        for response, reply in expected_responses.items():
                            if response in output:
                                channel.send(reply.encode("utf-8"))
                                output = ""

                    if output.endswith("$ "):
                        break

                time.sleep(0.1)
                
                if self.check_file_exists(channel, "/etc/odoo-server.conf"):
                    print("El archivo /etc/odoo-server.conf ya existe. Deteniendo la instalación.")
                    return

        finally:
            client.close()
            
    def check_file_exists(channel, filepath):
        command = f"ls {filepath}\n"
        channel.send(command)
        time.sleep(1)

        output = channel.recv(4096).decode("utf-8")
        return filepath in output

        
class PkeyPrivate(models.Model):
    _name = "ln10_sv_saas.pkey"
    _inherit = ["mail.activity.mixin","mail.thread"]
    _description  = "Añadir Clave Privada"
    
    name = fields.Char(string="nombre")
    pkey_private = fields.Text(string="Clave privada")
    password_pkey=fields.Char(string="password pkey")
    edit = fields.Boolean(default=True)
    
    
    def create_dt(self):
        existing_record = self.search([
            ('name', '=', self.name),  
            ('pkey_private', '=', self.pkey_private),
            ('password_pkey', '=', self.password_pkey)
        ])
        
        if not existing_record:
            self.create({
                'name': self.name,
                'pkey_private': self.pkey_private,
                'password_pkey': self.password_pkey,
                'edit':False
            })

class EditOdoo(models.Model):
    _name = "ln10_sv_saas.edit"
    _inherit = ["mail.activity.mixin", "mail.thread"]
    _description  = "Editar y Guardar script odoo"
    
    name = fields.Char(string="Nombre", related='odoo_ids.name',readonly=True)
    odooInstall =fields.Text(string="./odooInstall")
    odoo_ids = fields.Many2one('ln10_sv_saas.install','odoo installs', ondelete="cascade")
    ip_server=fields.Char(string="host", readonly=True, related='odoo_ids.ip_server')
    pkey_private=fields.Text(string="pke", readonly=True, related='odoo_ids.pkey_private')
    password_pkey=fields.Char(string="password pkey", related='odoo_ids.password_pkey', readonly=True)
    port=fields.Integer(string="port", related='odoo_ids.port', readonly=True)

    def execute_sh(self):
        """
        Funcion ejecutar script de odoo en modo prueba
        """
        private=paramiko.RSAKey(file_obj=io.StringIO(self.pkey_private), password=self.password_pkey)
        datos=dict(hostname=self.ip_server, port=self.port, username=self.name, pkey=private)
        _logger.info(datos)
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(**datos)
            
            contenido_script = self.odooInstall
            channel = ssh.get_transport().open_session()
            channel.exec_command(contenido_script)

            #   Esperar a que el script pida la pulsación de Enter y enviar Enter
            while not channel.recv_ready():                       
                time.sleep(1)
            channel.recv(1024)  # Limpiar el buffer
            channel.send("\n")

# Esperar a que el script pida la confirmación y enviar "Y" 
            while not channel.recv_ready():
                time.sleep(1)  
            channel.recv(1024)  # Limpiar el buffer
            channel.send("Y")

# Recoger la salida del comando
            stdout_output = channel.recv(4096).decode()
            stderr_output = channel.recv_stderr(4096).decode()

            _logger.info("Salida estándar:")
            _logger.info(stdout_output)

            _logger.error("Salida de error:")
            _logger.error(stderr_output)


           
        except paramiko.AuthenticationException as e:
            raise exceptions.ValidationError("Autenticacion fallida", str(e))
        except paramiko.SSHException as e:
            raise exceptions.ValidationError("error ssh", str(e))
        except Exception as e:
            raise exceptions.ValidationError(f"Ocurrió un error: {str(e)}")
        finally:
            ssh.close()
 
        
        
        
    def action_show_file(self):
        """
        Funcion para abrir script odoo
        """
        private_key = paramiko.RSAKey(file_obj=io.StringIO(self.pkey_private),password=self.password_pkey)
         
        datos = dict(hostname=self.ip_server, port=self.port, username=self.name,pkey=private_key)
        _logger.info(datos)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            
            ssh.connect(**datos)          
            command = f"cat odoo_install.sh"
            stdin, stdout, stderr = ssh.exec_command(command)
            file_content = stdout.read()
            self.odooInstall = file_content
        except paramiko.AuthenticationException as e:
            raise exceptions.ValidationError("Autenticacion fallida", str(e))
        except paramiko.SSHException as e:
            raise exceptions.ValidationError("error ssh", str(e))
        except Exception as e:
            raise exceptions.ValidationError(f"Ocurrió un error: {str(e)}")
        finally:
            ssh.close()
 
    
    def actualizar(self):   
        """
        funcion para  enviar los cambios del script
        """   
        private_key = paramiko.RSAKey(file_obj=io.StringIO(self.pkey_private),password=self.password_pkey)
        
        datos = dict(hostname=self.ip_server, port=self.port, username=self.name,pkey=private_key)
        _logger.info(datos)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(**datos)
            remote_file_path = 'odoo_install.sh'

                #          Nuevo contenido del archivo
            new_content = self.odooInstall

          #  sftp = client.open_sftp()
           
            # Reemplazar el contenido completo del archivo remoto con el nuevo contenido
            with client.open_sftp() as sftp:
                with sftp.open(remote_file_path, 'w') as remote_file:
                    remote_file.write(new_content.encode('utf-8'))

            
        except paramiko.AuthenticationException:
            raise exceptions.ValidationError("Error de autenticación. Verifica las credenciales de SSH.")
        except paramiko.SSHException as e:
            raise exceptions.ValidationError(f"Error SSH: {str(e)}")
        except Exception as e:
            raise exceptions.ValidationError(f"Ocurrió un error: {str(e)}")
        finally:
            sftp.close()
            client.close()
 
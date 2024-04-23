# -*- coding: utf-8 -*-

from odoo import models,api,_,fields
import psycopg2

from psycopg2 import errors

from odoo.exceptions import UserError

import logging


_logger = logging.getLogger(__name__)

class CreateUserPsql(models.TransientModel):
    _name = "creates.psql"
    _description = "Crear users postgres"
    
    name = fields.Char(string="new username")
    password = fields.Char(string="new user password", required=True)
    servidor = fields.Many2one('ln10_sv_saas.droplets', 'IP')
    ip_server=fields.Char(related='servidor.ip_server',string="ip server" , ondelete='cascade', readonly=True)
   # password_postgres=fields.Char(string="Password User",required=True)
    user_postgres = fields.Char(string="superuser postgres", default="postgres")
    pass_user = fields.Char(string="Password User")
    port = fields.Char(string="port", default="5432")
    datos_user = fields.Char(string='-',default="Datos para crear usuarios de postgres", readonly=True)
    datos_psl=fields.Char(string='-',default="Datos para conectarse a postgres", readonly=True)
  
    def create_postgres_user(self):
       
      
    # Datos de conexión a la base de datos de PostgreSQL en la IP remota
        host = self.ip_server
        port = self.port 
        superuser = self.user_postgres  
        superuser_password =self.pass_user
        dbname='template1'
    # Intentamos conectar a la base de datos de PostgreSQL en la IP remota como superusuario
        try:
            conn = psycopg2.connect(
            dbname=dbname,
            user=superuser,
            password=superuser_password,
            host=host,
            port=port
        )
        except psycopg2.Error as e:
            _logger.error("Error al conectar a la base de datos remota como superusuario:", e)
            return False

    # Creamos el usuario de PostgreSQL en la IP remota
        try:
            with conn.cursor() as cursor:
               # cursor.execute('CREATE USER "{}" WITH PASSWORD %s'.format(username), (password,))
                _logger.info(f"Creando usuario: {self.name}")
                cursor.execute('CREATE USER "{}" WITH PASSWORD %s'.format(self.name), (self.password,))
                conn.commit()
                _logger.info("Usuario creado correctamente.")

                _logger.info(f"Otorgando permisos a: {self.name}")
                cursor.execute('ALTER USER "{}" WITH SUPERUSER CREATEDB CREATEROLE'.format(self.name))
                conn.commit()
                _logger.info("Permisos otorgados correctamente.")
                
        except errors.DuplicateObject as e:
            _logger.error("Error al crear el usuario de PostgreSQL en la IP remota:", e)
            raise UserError(f"El usuario '{self.name}' ya existe.")

        
        except psycopg2.Error as e:
            _logger.error("Error al crear el usuario de PostgreSQL en la IP remota:", e)
            return False
        finally:
            conn.close()

        return True
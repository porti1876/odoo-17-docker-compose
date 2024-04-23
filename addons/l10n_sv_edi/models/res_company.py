# -*- coding: utf-8 -*-

import base64
import json
import requests
# import schedule
import time
import requests
from odoo import fields, models, api, _,exceptions
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil import parser


# from odoo.odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    proveedor_timbrado = fields.Selection(
        selection=[('multifactura', _('Servidor 1')),
                   ('gecoerp', _('Servidor 2')),
                   ('multifactura2', _('Servidor 3')),
                   ('multifactura3', _('Servidor 4')), ],
        string=_('Proveedor de timbrado'),)

    bg_color = fields.Char(string="Fondo de encabezados DTE")

    api_key = fields.Char(string=_('API Key'))
    modo_prueba = fields.Selection(string='Modo de ambiente',
                                   selection=[('00', 'Modo de prueba'),
                                              ('01', 'Modo de producción')
                                              ])   
    serie_factura = fields.Char(string=_('Serie factura'))
    archivo_cer = fields.Binary(string=_('Archivo .cer'))
    archivo_key = fields.Binary(string=_('Archivo .key'))
    contrasena = fields.Char(string='Contraseña pública', help="Esta es la contraseña pública y se usa para generar "
                                                               "el token de autenticación.", store=True)
    nombre_fiscal = fields.Char(string=_('Razón social'))
    serie_complemento = fields.Char(string=_('Serie complemento de pago'))
    telefono_sms = fields.Char(string=_('Teléfono celular'))
    saldo_timbres = fields.Float(string=_('Saldo de timbres'), readonly=True)
    saldo_alarma = fields.Float(string=_('Alarma timbres'), default=10)
    correo_alarma = fields.Char(string=_('Correo de alarma'))
    fecha_csd = fields.Datetime(string=_('Fecha y Hora de generación', readonly=True))
    estado_csd = fields.Char(string=_('Estado de token'), readonly=True)
    aviso_csd = fields.Char(string=_('Aviso vencimiento (días antes)'), default=14)
    fecha_timbres = fields.Date(string=_('Vigencia timbres'), readonly=True)
    token_code = fields.Char(string="Codigo de token", readonly=True, password=True)
    document_nit = fields.Char(String="NIT", store=True)
    token_label = fields.Char(string='Estado del token', compute='_compute_token_label')
    is_token_visible = fields.Boolean(string="Mostrar token")
    is_token_visible = fields.Boolean(string="Mostrar token", default=False)
    private_pass_mh = fields.Char(string="Contraseña privada", help="Esta es la contraseña privada y se usa para "
                                                                    "firmado de documentos")
    cod_estable_mh = fields.Char(string="Código de  establecimiento MH", help="Código del establecimiento asignado por el MH", size=4)
    cod_pv_mh = fields.Char(string="Código de PDV MH", help="Código del Punto de Venta (Emisor) asignado por el MH", size=4)
    cod_estable = fields.Char(string="Código de establecimiento contribuyente",help="Código del establecimiento asignado por el contribuyente", size=4)
    cod_pv = fields.Char(string="Código de PDV contribuyente",help="Código del Punto de Venta (Emisor) asignado por el contribuyente", size=4)
    
    
    
    @api.model
    def get_saldo_by_cron(self):
        companies = self.search([('proveedor_timbrado', '!=', False)])
        for company in companies:
            company.get_saldo()
            if company.saldo_timbres < company.saldo_alarma and company.correo_alarma:  # valida saldo de timbres
                email_template = self.env.ref("l10n_sv_edi.email_template_alarma_de_saldo", False)
                if not email_template: return
                emails = company.correo_alarma.split(",")
                for email in emails:
                    email = email.strip()
                    if email:
                        email_template.send_mail(company.id, force_send=True, email_values={'email_to': email})
            if company.aviso_csd and company.fecha_csd and company.correo_alarma:  # valida vigencia de CSD
                if datetime.today() - timedelta(days=int(company.aviso_csd)) > company.fecha_csd:
                    email_template = self.env.ref("l10n_sv_edi.email_template_alarma_de_csd", False)
                    if not email_template: return
                    emails = company.correo_alarma.split(",")
                    for email in emails:
                        email = email.strip()
                        if email:
                            email_template.send_mail(company.id, force_send=True, email_values={'email_to': email})
            if company.fecha_timbres and company.correo_alarma:  # valida vigencia de timbres
                if (datetime.today() + timedelta(days=7)).date() > company.fecha_timbres:
                    email_template = self.env.ref("l10n_sv_edi.email_template_alarma_vencimiento", False)
                    if not email_template: return
                    emails = company.correo_alarma.split(",")
                    for email in emails:
                        email = email.strip()
                        if email:
                            email_template.send_mail(company.id, force_send=True, email_values={'email_to': email})
        return True

    def get_saldo(self):
        values = {
            'rfc': self.vat,
            'api_key': self.proveedor_timbrado,
            'modo_prueba': self.modo_prueba,
        }
        url = ''
        if self.proveedor_timbrado == 'multifactura':
            url = '%s' % ('http://facturacion.itadmin.com.mx/api/saldo')
        elif self.proveedor_timbrado == 'gecoerp':
            if self.modo_prueba:
                # url = '%s' % ('https://ws.gecoerp.com/itadmin/pruebas/invoice/?handler=OdooHandler33')
                url = '%s' % ('https://itadmin.gecoerp.com/invoice/?handler=OdooHandler33')
            else:
                url = '%s' % ('https://itadmin.gecoerp.com/invoice/?handler=OdooHandler33')
        if not url:
            return
        try:
            response = requests.post(url, auth=None, verify=False, data=json.dumps(values),
                                     headers={"Content-type": "application/json"})
            json_response = response.json()
        except Exception as e:
            print(e)
            json_response = {}

        if not json_response:
            return

        estado_factura = json_response['estado_saldo']
        if estado_factura == 'problemas_saldo':
            raise UserError(_(json_response['problemas_message']))
        if json_response.get('saldo'):
            xml_saldo = base64.b64decode(json_response['saldo'])
        values2 = {
            'saldo_timbres': xml_saldo,
            'fecha_timbres': parser.parse(json_response['vigencia']) if json_response['vigencia'] else '',
        }
        self.update(values2)

    def validar_csd(self):
        values = {
            'rfc': self.vat,
            'archivo_cer': self.archivo_cer.decode("utf-8"),
            'archivo_key': self.archivo_key.decode("utf-8"),
            'contrasena': self.contrasena,
        }
        url = ''
        if self.proveedor_timbrado == 'multifactura':
            url = '%s' % ('http://facturacion.itadmin.com.mx/api/validarcsd')
        elif self.proveedor_timbrado == 'multifactura2':
            url = '%s' % ('http://facturacion2.itadmin.com.mx/api/validarcsd')
        elif self.proveedor_timbrado == 'multifactura3':
            url = '%s' % ('http://facturacion3.itadmin.com.mx/api/validarcsd')
        if not url:
            return
        try:
            response = requests.post(url, auth=None, verify=False, data=json.dumps(values),
                                     headers={"Content-type": "application/json"})
            json_response = response.json()
        except Exception as e:
            print(e)
            json_response = {}

        if not json_response:
            return
        # _logger.info('something ... %s', response.text)

        respuesta = json_response['respuesta']
        if json_response['respuesta'] == 'Certificados CSD correctos':
            self.fecha_csd = parser.parse(json_response['fecha'])
            values2 = {
                'fecha_csd': self.fecha_csd,
                'estado_csd': json_response['respuesta'],
            }
            self.update(values2)
        else:
            raise UserError(respuesta)

    def borrar_csd(self):
        values = {
            'rfc': self.vat,
        }
        url = ''
        if self.proveedor_timbrado == 'multifactura':
            url = '%s' % ('http://facturacion.itadmin.com.mx/api/borrarcsd')
        elif self.proveedor_timbrado == 'multifactura2':
            url = '%s' % ('http://facturacion2.itadmin.com.mx/api/borrarcsd')
        elif self.proveedor_timbrado == 'multifactura3':
            url = '%s' % ('http://facturacion3.itadmin.com.mx/api/borrarcsd')
        if not url:
            return
        try:
            response = requests.post(url, auth=None, verify=False, data=json.dumps(values),
                                     headers={"Content-type": "application/json"})
            json_response = response.json()
        except Exception as e:
            print(e)
            json_response = {}

        if not json_response:
            return
        # _logger.info('something ... %s', response.text)
        respuesta = json_response['respuesta']
        raise UserError(respuesta)

    def borrar_estado(self):
        values2 = {
            'fecha_csd': '',
            'estado_csd': '',
        }
        self.update(values2)

    def button_dummy(self):
        self.get_saldo()

             
    @api.model
    def generate_dte_tokens(self):  # Genera el token automatico            
          
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "requests"
        }
        payload = {
            "user": self.document_nit,
            "pwd": self.contrasena
        }
        url = ''
        if self.modo_prueba == '00':
           
            url = "https://apitest.dtes.mh.gob.sv/seguridad/auth"
           # schedule.every(2).minutes.do(url)
          #  schedule.every(1).minutes.do(self.generate_dte_tokens)

        elif self.modo_prueba == '01':
           
            url = "https://api.dtes.mh.gob.sv/seguridad/auth"
         #   schedule.every(24).hours.do(url)
         #   schedule.every(24).hours.do(self.generate_dte_tokens)

        if not url:
            return
          
        
        try:
            response = requests.post(url, headers=headers, data=payload)
            json_response = response.json()
          
        except Exception as e:
            print(e)
            raise UserError('Ocurrió un error al conectarse al servidor de DGII')

        if response.status_code == 200 and "token" in json_response.get("body", {}):
            values_token = {
                'token_code': json_response["body"]["token"],
                'fecha_csd': fields.Datetime.now()
            }
          
            self.write(values_token)
            self.update(values_token)
         
        
        else:
            raise UserError('Credenciales incorrectas o respuesta del servidor de DGII incorrecta')
      
       
        return True
    
    #Generar token modo de ambiente :modo de prueba
    @api.model
    def update_token_test(self):
        token_update = self.search([])
            #recorre cada que llegue su tiempo establecido
        for tk in token_update:
            tk.generate_dte_tokens()
    
    
    #Generar token modo de ambiente:modo de produccion
    @api.model
    def update_token_produccion(self):
        token_update = self.search([])
            #recorre cada que llegue su tiempo establecido
        for tk in token_update:
            tk.generate_dte_tokens()
    
    #valida cada funcion y asi se ejecuta segun sea el caso
    @api.onchange("modo_prueba")
    def _validar_tokens(self):
        if self.modo_prueba == "00":
            self.update_token_test()
        elif self.modo_prueba == "01":
            self.update_token_produccion()
    
    #recorre cada funcion del onchange _validar_tokens,           
    @api.model
    def validar_token_s_ocha(self):
        token = self.search([])
        for tokens in token:
            tokens._validar_tokens() 
               


    def get_token_dte(self): # Genera el token haciendo clic button Validar token
        fields_to_check = [('document_nit', 'Debe ingresar el documento NIT'),
                           ('archivo_cer', 'Debe ingresar el certificado'),
                           ('archivo_key', 'Debe ingresar la llave de autorización'),
                           ('contrasena', 'Debe ingresar la contraseña correspondiente'),
                           ('modo_prueba', 'Debe seleccionar el modo de facturación DTE')]

        for field, error_msg in fields_to_check:
            if not getattr(self, field):
                raise UserError(error_msg)

        payload = {
            "user": self.document_nit,
            "pwd": self.contrasena
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "requests"
        }
        url = ''
        if self.modo_prueba == '00':
            url = "https://apitest.dtes.mh.gob.sv/seguridad/auth"
        elif self.modo_prueba == '01':
            url = "https://api.dtes.mh.gob.sv/seguridad/auth"
        if not url:
            return
        try:
            response = requests.post(url, headers=headers, data=payload)
            json_response = response.json()
        except Exception as e:
            print(e)
            raise UserError('Ocurrió un error al conectarse al servidor de DGII')

        if response.status_code == 200 and "token" in json_response.get("body", {}):
            values_token = {
                'token_code': json_response["body"]["token"],
                'fecha_csd': fields.Datetime.now()
            }
            self.update(values_token)
        else:
            raise UserError('Credenciales incorrectas o respuesta del servidor de DGII incorrecta')

    def borrar_token_dte(self):
        values_delete_token = {
            'fecha_csd': '',
            'token_code': '',
        }
        self.update(values_delete_token)

    def borrar_credenciales(self):
        values_delete_credentials = {
            'archivo_key': '',
            'archivo_cer': '',
            'contrasena': '',
            'private_pass_mh': '',
        }
        self.update(values_delete_credentials)

    @api.depends('token_code')
    def _compute_token_label(self):
        for company in self:
            if company.token_code:
                company.token_label = 'Generado correctamente'
            else:
                company.token_label = 'Token no generado'

      



class GenerateTokenCronResCompany(models.Model):
    _inherit = 'res.company'

    def generate_dte_token(self):
        # Se verifica si se han ingresado las credenciales
        payload = {
            "user": self.document_nit,
            "pwd": self.contrasena
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "requests"
        }
        url = ''
        if self.modo_prueba == '00':
            url = "https://apitest.dtes.mh.gob.sv/seguridad/auth"
        elif self.modo_prueba == '01':
            url = "https://api.dtes.mh.gob.sv/seguridad/auth"
        if not url:
            return
        try:
            response = requests.post(url, headers=headers, data=payload)
            json_response = response.json()
        except Exception as e:
            print(e)
            raise UserError('Ocurrió un error al conectarse al servidor de DGII')

        if response.status_code == 200 and "token" in json_response.get("body", {}):
            values_token = {
                'token_code': json_response["body"]["token"],
                'fecha_csd': fields.Datetime.now()
            }
            self.update(values_token)
        else:
            raise UserError('Credenciales incorrectas o respuesta del servidor de DGII incorrecta')

# -*- coding: utf-8 -*-
import json
import uuid
from datetime import datetime

import pytz
import requests

from odoo import models,fields,api, _
from odoo.exceptions import UserError, Warning, ValidationError


class ReasonCancelation(models.TransientModel):
    _name ='reason.cancelation'
    _description = 'reason.cancelation'

    move_id = fields.Many2one('account.move', string="Nombre de factura", default=lambda self: self._context.get('active_id'), readonly=True)
    user_id = fields.Many2one(
        'res.users',
        string='Usuario responsable de anular DTE',
        default=lambda self: self.env.user,
        domain=[('share', '=', False)], readaonly=True)
    company_id = fields.Many2one('res.company',string="Compañia", default=lambda self: self.env.company, readonly=True)

    tipo_cancelacion = fields.Selection(
        selection=[('1', ('Error en la Información del Documento Tributario Electrónico a invalidar.')),
                   ('2', ('Rescindir de la operación realizada.')),
                   ('3', ('Otro')),
                   ],
        string=('Tipo de cancelación'), required=True,
    )
    motivo_anulacion = fields.Char(string="Motivo de anulación", required=True)

    fecha_cancelacion = fields.Datetime(string='Fecha de cancelación', default=fields.Datetime.now)



    foliosustitucion = fields.Char(string=_('Folio Sustitucion'))


    # Codigo de generacion

    uuid_code_anul = fields.Char(string='Código de generación de anulación', readonly=True, store=True,
                                       default=lambda self: str(uuid.uuid4()).upper())

    tipo_identificacion_responsable = fields.Selection(
        selection=[
            ('13', 'DUI'),
            ('36', 'NIT'),
            ('03', 'Pasaporte'),
            ('02', 'Carnet de Residente'),
            ('37', 'Otro'),
        ],
        string='Tipo de Identificación de la persona responsable de invalidación'
    )
    documento_firmado = fields.Char(string="Firma de documento anulado", default="Anulación no firmada")

    confirmacion = fields.Char(string="Confirmación de anulación")
    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)
        defaults['company_id'] = self.env.company.id
        return defaults

    def Confirmar(self):
        if self.env.context.get('active_id') and self.env.context.get('active_model') == "account.move":
            move_obj = self.env['account.move'].browse(self.env.context['active_id'])
            ctx = {'motivo_cancelacion':self.motivo_cancelacion,'foliosustitucion':self.foliosustitucion or False}
            return move_obj.with_context(ctx).action_cfdi_cancel()
        if self.env.context.get('active_id') and self.env.context.get('active_model') == "account.payment":
            move_obj = self.env['account.payment'].browse(self.env.context['active_id'])
            ctx = {'motivo_cancelacion':self.motivo_cancelacion,'foliosustitucion':self.foliosustitucion or False}
            return move_obj.with_context(ctx).action_cfdi_cancel()
        if self.env.context.get('active_id') and self.env.context.get('active_model') == "cfdi.traslado":
            move_obj = self.env['cfdi.traslado'].browse(self.env.context['active_id'])
            ctx = {'motivo_cancelacion':self.motivo_cancelacion,'foliosustitucion':self.foliosustitucion or False}
            return move_obj.with_context(ctx).action_cfdi_cancel()
        if self.env.context.get('active_id') and self.env.context.get('active_model') == "factura.global":
            move_obj = self.env['factura.global'].browse(self.env.context['active_id'])
            ctx = {'motivo_cancelacion':self.motivo_cancelacion,'foliosustitucion':self.foliosustitucion or False}
            return move_obj.with_context(ctx).action_cfdi_cancel()
        if self.env.context.get('active_id') and self.env.context.get('active_model') == "hr.payslip":
            move_obj = self.env['hr.payslip'].browse(self.env.context['active_id'])
            ctx = {'motivo_cancelacion':self.motivo_cancelacion,'foliosustitucion':self.foliosustitucion or False}
            return move_obj.with_context(ctx).action_cfdi_cancel()


    def firmar_anular_dte(self):
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        tz = pytz.timezone('America/El_Salvador')
        hora_actual = datetime.now(tz).strftime('%H:%M:%S')
        url = 'http://167.99.8.116:8113/firmardocumento/?content-Type=application/JSON&nit=06142809011497'

        num_documento_options = {
            '36': self.move_id.partner_id.document_nit_compute,
            '13': self.move_id.partner_id.document_dui,
            '03': self.move_id.partner_id.document_pasaporte,
            '02': self.move_id.partner_id.document_carnet_residente,
            '37': self.move_id.tipo_identificacion_receptor_otro,
        }
        payload = json.dumps({
            'nit': self.company_id.document_nit,
            'activo': "True",
            'passwordPri': self.company_id.private_pass_mh,
            'dteJson':
                {
                    "identificacion": {
                        "version": 2,
                        "ambiente": self.company_id.modo_prueba,
                        "codigoGeneracion": self.move_id.uuid_generation_code,
                        "fecAnula": self.fecha_cancelacion.strftime('%Y-%m-%d'),
                        "horAnula": hora_actual,
                    },
                    "emisor": {
                        "nit": self.company_id.document_nit,
                        "nombre": self.company_id.name,
                        "tipoEstablecimiento": self.move_id.tipo_establecimiento,
                        "nomEstablecimiento": self.company_id.name,
                        "codEstableMH": None if not self.company_id.cod_estable_mh else self.company_id.cod_estable_mh,
                        "codEstable":None if not self.company_id.cod_estable else self.company_id.cod_estable,
                        "codPuntoVentaMH": None if not self.company_id.cod_pv_mh else self.company_id.cod_pv_mh,
                        "codPuntoVenta":  None if not self.company_id.cod_pv else self.company_id.cod_pv,
                        "telefono": None if not self.company_id.phone else self.company_id.phone,
                        "correo": self.company_id.email,
                    },
                    "documento": {
                        "tipoDte": self.move_id.journal_id.document_type_sv,
                        "codigoGeneracion": self.move_id.uuid_generation_code,
                        "selloRecibido": self.move_id.confirmacion,
                        "numeroControl": self.move_id.name,
                        "fecEmi": self.move_id.fecha_emision.strftime('%Y-%m-%d'),
                        "montoIva": None,
                        "codigoGeneracionR": self.uuid_code_anul,
                        "tipoDocumento": self.move_id.tipo_identificacion_receptor,
                        "numDocumento": num_documento_options.get(self.move_id.tipo_identificacion_receptor, None),
                        "nombre": self.move_id.partner_id.name,
                        "telefono": None if not self.move_id.partner_id.phone else self.move_id.partner_id.phone.replace(
                            " ", ""),
                        "correo": self.move_id.partner_id.email
                    },
                    "motivo": {
                        "tipoAnulacion": int(self.tipo_cancelacion),
                        "motivoAnulacion": None if not self.motivo_anulacion else self.motivo_anulacion,
                        "nombreResponsable": self.user_id.name,
                        "tipDocResponsable": "36",
                        "numDocResponsable": self.user_id.document_nit_compute,
                        "nombreSolicita": self.user_id.name,
                        "tipDocSolicita": "36",
                        "numDocSolicita": self.user_id.document_nit_compute
                    },
                }
        })
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.company_id.token_code
        }

        try:
            response = requests.post(url, headers=headers, data=payload)
            json_response = response.json()
        except Exception as e:
            raise ValidationError('Ocurrió un error al conectarse al servicio de firmado')

        if response.status_code == 200:
            if json_response.get('status') == 'OK':
                values = {
                    'documento_firmado': json_response['body']
                }
                self.write(values)
                value_move = {
                    'estado_dte': 'anulada',
                    'state': 'cancel',
                }
                self.move_id.write(value_move)
                self.move_id.message_post(body="El DTE ha sido anulado", message_type="notification")

            else:
                raise ValidationError(json_response.get('body', {}).get('mensaje', 'Error desconocido'))
        else:
            raise ValidationError('Error al conectarse al servidor de DGII: %s' % response.content)


        # Envio a endopoint de invalidacion de hacienda luego del firmado

        payload_anular = json.dumps({
            "ambiente": self.company_id.modo_prueba,
            "idEnvio": 100,  # idEnvio es tipo de dato numero entero
            "version": 2,
            "documento": self.documento_firmado,
        })
        headers_anular = {
            'Authorization': self.company_id.token_code,
            'Content-Type': 'application/json',
            'User-Agent': 'requests'
        }
        url_anu = ''
        if self.company_id.modo_prueba == '00':
            url_anu = "https://apitest.dtes.mh.gob.sv/fesv/anulardte"
        elif self.company_id.modo_prueba == '01':
            url_anu = "https://api.dtes.mh.gob.sv/fesv/anulardte"
        if not url_anu:
            return
        try:
            response = requests.post(url_anu, headers=headers_anular, data=payload_anular)
            json_response = response.json()
        except Exception as e:
            print(e)
            raise ValidationError('Ocurrió un error al conectarse al servidor de DGII: Verifica las credenciales de '
                                  'la empresa o genera un nuevo token de autenticación')

        if response.status_code == 200:
            if json_response.get('estado') == 'PROCESADO':
                values_anulado = {
                    'sello_recibido_anulado': json_response['selloRecibido'],
                    'uuid_generation_code_anuladado': json_response['codigoGeneracion'],
                    'date_anulado': json_response['fhProcesamiento'],
                }
                self.move_id.write(values_anulado)
            else:
                raise ValidationError(json_response.get('body', {}).get('mensaje', 'Error desconocido'))
        else:
            error_response = json.loads(response.content)
            error_message = 'Error al validar información del DTE: \n' + \
                            f"Estado: {error_response.get('estado')}\n" + \
                            f"Clasificación del mensaje: {error_response.get('clasificaMsg')}\n" + \
                            f"Descripción del mensaje: {error_response.get('descripcionMsg')}\n" + \
                            f"Descripción del mensaje: {error_response.get('observaciones')}\n"
            raise ValidationError(error_message)
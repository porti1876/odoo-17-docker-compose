# -*- coding: utf-8 -*-
import ast
import base64
import json
import urllib
import io
import os
import requests
import datetime
import csv
from datetime import datetime,date
from lxml import etree
from odoo import fields, models, api, _
# import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning
from dateutil.relativedelta import relativedelta

from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.lib.units import mm

from odoo.addons.account_edi.models.mail_template import MailTemplate
from . import amount_to_text_es_MX
import pytz
import re
import logging
import uuid
import qrcode
import psycopg2
import tempfile
_logger = logging.getLogger(__name__)


# ruta_data_cat_pago  = os.path.abspath("data/catalogo.forma.pago.csv")

class AccountMove(models.Model):
    _inherit = 'account.move'

    fecha_pagado = fields.Date(string="Fecha de pagado")
    forma_pago_id = fields.Many2one(
        'catalogo.forma.pago', string='Forma de pago')

    otra_forma_pago = fields.Char(string="Otra forma de pago", store=True)
    
    counter_firmas=fields.Integer(string="Contador firmas", readonly=True,store=True)
   
    
   
    
   # @api.depends('counter_firmas')
   # def _compute_contador(self):
   #     for record in self:
   #         record.total_firmas = record.counter_firmas + 1
            
            
            
            
    @api.onchange("forma_pago_id")
    def _onchange_forma_pago_id(
            self):  # Funcion para que valide si en el campo forma_pago_id se selecciona el id 14 sea visible otra_forma_pago
        # file_path = os.path.join(os.path.dirname(__file__), "data", "catalogo.forma.pago.csv")
        selected_forma_pago_id = self.forma_pago_id.id

        if selected_forma_pago_id == 14:

            self.otra_forma_pago = ''
        else:

            self.otra_forma_pago = False

    # @api.depends('invoice_payments_widget')
    # def _compute_payment_date(self):
    #     for record in self:
    #         if record.invoice_payments_widget:
    #             payments_widget = record.invoice_payments_widget
    #             first_payment_date = payments_widget['content'][0]['date']
    #             if payments_widget['content']:
    #                 payment = payments_widget['content'][0]
    #                 record.first_payment_date = payment['date']
    #             else:
    #                 record.first_payment_date = False
    #         else:
    #             record.first_payment_date = False

    # journal_id = fields.Many2one(compute='_compute_journal_id')
    total_exportacion = fields.Monetary(
        compute='_compute_total_exportacion', string='Total Exportación', readonly=True)
    factura_cfdi = fields.Boolean('Factura CFDI')
    tipo_comprobante = fields.Selection(
        selection=[('I', 'Ingreso'),
                   ('E', 'Egreso'),
                   ('T', 'Traslado'),
                   ],
        string=_('Tipo de comprobante'),
    )

    methodo_pago = fields.Selection(
        selection=[('PUE', _('Pago en una sola exhibición')),
                   ('PPD', _('Pago en parcialidades o diferido')), ],
        string=_('Método de pago'),
    )
    # uso_cfdi_id = fields.Many2one(
    #     'catalogo.uso.cfdi', string='Uso CFDI (cliente)')
    estado_factura = fields.Selection(
        selection=[('factura_no_generada', 'Factura no generada'), ('factura_correcta', 'Factura correcta'),
                   ('solicitud_cancelar', 'Cancelación en proceso'), (
                       'factura_cancelada', 'Factura cancelada'),
                   ('solicitud_rechazada', 'Cancelación rechazada'), ],
        string=_('Estado de factura'),
        default='factura_no_generada',
        readonly=True
    )
    pdf_l10n_sv_edi = fields.Binary("CDFI Invoice")
    qrcode_image = fields.Binary("QRCode")
    numero_cetificado = fields.Char(string=_('Numero de cetificado'))
    cetificaso_sat = fields.Char(string=_('Cetificao SAT'))
    folio_fiscal = fields.Char(string=_('Folio Fiscal'), readonly=True)
    fecha_certificacion = fields.Char(string=_('Fecha y Hora Certificación'))
    cadena_origenal = fields.Char(
        string=_('Cadena Origenal del Complemento digital de SAT'))
    selo_digital_cdfi = fields.Char(string=_('Selo Digital del CDFI'))
    selo_sat = fields.Char(string=_('Selo del SAT'))
    moneda = fields.Char(string=_('Moneda'))
    tipocambio = fields.Char(string=_('TipoCambio'))
    # folio = fields.Char(string=_('Folio'))
    # version = fields.Char(string=_('Version'))
    number_folio = fields.Char(string=_('Folio'), compute='_get_number_folio')
    amount_to_text = fields.Char('Amount to Text', compute='_get_amount_to_text',
                                 size=256,
                                 help='Amount of the invoice in letter')
    amount_to_text_exp = fields.Char('Amount to Text In DTESV EXPOR', compute='_get_amount_to_text_exp',
                                     size=256,
                                     help='Amount of the invoice in letter in fex dte sv')
    amount_to_text_ret = fields.Char('Amount to Text In DTESV Retencion', compute='_get_amount_to_text_ret',
                                     size=256,
                                     help='Amount of the invoice in letter in comprobante retencion dte sv')
    qr_value = fields.Char(string=_('QR Code Value'))
    fecha_emision = fields.Datetime(
        string='Fecha y Hora de emisión', default=fields.Datetime.now)

    fecha_emision_nd_nc = fields.Datetime(
        string='Fecha y Hora de emisión', default=fields.Datetime.now)
    fecha_factura = fields.Datetime(
        string='Fecha Factura Confirmada', default=fields.Datetime.now, readonly=True)
    # serie_emisor = fields.Char(string=_('A'))
    tipo_relacion = fields.Selection(
        selection=[('01', 'Nota de crédito de los documentos relacionados'),
                   ('02', 'Nota de débito de los documentos relacionados'),
                   ('03', 'Devolución de mercancía sobre facturas o traslados previos'),
                   ('04', 'Sustitución de los CFDI previos'),
                   ('05', 'Traslados de mercancías facturados previamente'),
                   ('06', 'Factura 6generada por los traslados previos'),
                   ('07', 'CFDI por aplicación de anticipo'), ],
        string=_('Tipo relación'),
    )
    uuid_relacionado = fields.Char(string=_('CFDI Relacionado'))
    confirmacion = fields.Char(
        string='Sello de confirmación', readonly=True, default="Sello no generado")
    total_factura = fields.Float("Total factura")
    subtotal = fields.Float("Subtotal factura")
    discount = fields.Float("Descuento factura")
    facatradquirente = fields.Char(string=_('Fac Atr Adquirente'))
    exportacion = fields.Selection(
        selection=[('01', 'No aplica'),
                   ('02', 'Definitiva'),
                   ('03', 'Temporal'), ],
        string=_('Exportacion'), default='01',
    )
    proceso_timbrado = fields.Boolean(string=_('Proceso de timbrado'))
    tax_payment = fields.Text(string=_('Taxes'))
    factura_global = fields.Boolean('Factura global')
    fg_periodicidad = fields.Selection(
        selection=[('01', '01 - Diario'),
                   ('02', '02 - Semanal'),
                   ('03', '03 - Quincenal'),
                   ('04', '04 - Mensual'),
                   ('05', '05 - Bimestral'), ],
        string=_('Periodicidad'),
    )
    fg_meses = fields.Selection(
        selection=[('01', '01 - Enero'),
                   ('02', '02 - Febrero'),
                   ('03', '03 - Marzo'),
                   ('04', '04 - Abril'),
                   ('05', '05 - Mayo'),
                   ('06', '06 - Junio'),
                   ('07', '07 - Julio'),
                   ('08', '08 - Agosto'),
                   ('09', '09 - Septiembre'),
                   ('10', '10 - Octubre'),
                   ('11', '11 - Noviembre'),
                   ('12', '12 - Diciembre'),
                   ('13', '13 - Enero - Febrero'),
                   ('14', '14 - Marzo - Abril'),
                   ('15', '15 - Mayo - Junio'),
                   ('16', '16 - Julio - Agosto'),
                   ('17', '17 - Septiembre - Octubre'),
                   ('18', '18 - Noviembre - Diciembre'), ],
        string=_('Mes'),
    )
    fg_ano = fields.Char(string=_('Año'))

    # Campos de Catálogo de Giro

    # CAT-003
    modelo_facturacion = fields.Selection(
        selection=[
            ('1', 'Modelo Facturación previo'),
            ('2', 'Modelo Facturación diferido'),
        ],
        string="Modelo de Facturación", default='1'
    )
    # CAT-004
    tipo_transmision = fields.Selection(
        selection=[
            ('1', 'Transmisión normal'),
            ('2', 'Transmisión por contingencia'),
        ],
        string="Tipo de Transmisión", default='1'
    )
    # CAT-005
    tipo_contingencia = fields.Selection(
        selection=[
            ('None', 'N/A'),
            ('1', 'No disponibilidad de sistema del MH'),
            ('2', 'No disponibilidad de sistema del emisor'),
            ('3', 'Falla en el suministro de servicio de Internet del Emisor'),
            ('4',
             'Falla en el suministro de servicio de energía eléctrica del emisor que impida la transmisión de los DTE'),
            ('5', 'Otro'),
        ],
        string='Tipo de Contingencia', default='None'
    )

    motivo_contig = fields.Char(string='Motivo de contingencia',
                                help="Indique el motivo por el cual la factura se esta emitiendo de manera de contingencia")
    tipo_contingencia_otro = fields.Char(string="Otro", size=500)

    # CAT-007
    tipo_generacion_documento = fields.Selection(
        selection=[
            ('1', 'Físico'),
            ('2', 'Electrónico'),
        ],
        string='Tipo de Generación del Documento', default='1'
    )
    # CAT-009 Provisional
    tipo_establecimiento = fields.Selection(
        selection=[
            ('01', 'Sucursal / Agencia'),
            ('02', 'Casa matriz'),
            ('03', 'Bodega'),
            ('07', 'Predio y/o patio'),
            ('20', 'Otro'),
        ],
        string='Tipo de establecimiento', default='01'
    )
    # CAT-010
    servicio_medico = fields.Boolean(default=False, string='Campo médico')
    codigo_tipo_servicio_medico = fields.Selection(
        selection=[
            ('1', 'Cirugía'),
            ('2', 'Operación'),
            ('3', 'Tratamiento médico'),
            ('4', 'Cirugía instituto salvadoreño de Bienestar Magisterial'),
            ('5', 'Operación Instituto Salvadoreño de Bienestar Magisterial'),
            ('6', 'Tratamiento médico Instituto Salvadoreño de Bienestar Magisterial'),
        ],
        string='Código de Tipo de Servicio Médico'
    )
    # CAT-021
    otros_documentos_asociados = fields.Selection(
        selection=[
            ('1', 'Emisor'),
            ('2', 'Receptor'),
            ('3', 'Médico (solo aplica para contribuyentes obligados a la presentación de F-958)'),
            ('4', 'Transporte (Factura de exportación)'),
        ],
        string='Otros Documentos Asociados'
    )

    cod_asociado = fields.Char(string="Identificación del documento asociado")

    detalle_documento = fields.Char(string="Descripción de documento asociado")

    # CAT-022
    tipo_identificacion_receptor = fields.Selection(
        selection=[
            ('13', 'DUI'),
            ('36', 'NIT'),
            ('03', 'Pasaporte'),
            ('02', 'Carnet de Residente'),
            ('37', 'Otro'),
        ],
        string='Tipo de Identificación del Receptor'
    )

    is_company = fields.Boolean(
        related='partner_id.is_company', string='Es compañía')

    document_dui_move = fields.Char(
        related='partner_id.document_dui', string='DUI', readonly=True)
    document_nit = fields.Char(
        related='partner_id.document_nit', string='NIT', readonly=True)
    document_pasaporte = fields.Char(
        related='partner_id.document_pasaporte', string='Pasaporte', readonly=True)
    document_carnet_residente = fields.Char(related='partner_id.document_carnet_residente', string='Carnet Residente',
                                            readonly=True)

    tipo_documento_otro = fields.Char(string="Especificar que tipo de documento es",
                                      help="En caso de que no se tenga otro documento enlazado al formulario de "
                                           "contacto, especificar que tipo de documento se esta usando")
    tipo_identificacion_receptor_otro = fields.Char(string='Núm de documento')

    # CAT-023
    tipo_documento_contingencia = fields.Selection(
        selection=[
            ('01', 'Factura Electrónico'),
            ('03', 'Comprobante de Crédito Fiscal Electrónico'),
            ('04', 'Nota de Remisión Electrónica'),
            ('05', 'Nota de Crédito Electrónica'),
            ('06', 'Nota de Débito Electrónica'),
            ('11', 'Factura de Exportación Electrónica'),
            ('14', 'Factura de Sujeto Excluido Electrónica'),
        ],
        string='Tipo de Documento en Contingencia'
    )

    # CAT-024
    tipo_invalidacion = fields.Selection(
        selection=[
            ('1', 'Error en la Información del Documento Tributario Electrónico a invalidar.'),
            ('2', 'Rescindir de la operación realizada.'),
            ('3', 'Otro'),
        ],
        string='Tipo de Invalidación'
    )

    # CAT-025
    titulo_a_que_se_remiten_bienes = fields.Selection(
        selection=[
            ('01', 'Depósito'),
            ('02', 'Propiedad'),
            ('03', 'Consignación'),
            ('04', 'Traslado'),
            ('05', 'Otros'),
        ],
        string='Título a que se Remiten los Bienes'
    )

    # CAT-026
    tipo_donacion = fields.Selection(
        selection=[
            ('1', 'Efectivo'),
            ('2', 'Bien'),
            ('3', 'Servicio'),
        ],
        string='Tipo de Donación'
    )

    # CAT-030
    modo_transporte = fields.Selection(
        selection=[
            ('1', 'Terrestre'),
            ('2', 'Marítimo'),
            ('3', 'Aéreo'),
            ('4', 'Multimodal, Terrestre-marítimo'),
            ('5', 'Multimodal, Terrestre-aéreo'),
            ('6', 'Multimodal, Marítimo- aéreo'),
            ('7', 'Multimodal, Terrestre-Marítimo- aéreo')
        ],
        string='Transporte',
        default=None
    )

    # CAT-031 INCOTERMS
    catalogo_inco = fields.Many2one(
        comodel_name="catalogo.incoterms", string="Incoterm SV")
    catalago_inco = fields.Many2one(
        comodel_name="catalogo.incoterms", string="Incoterm SV")

    # CAT-Extra Campos extra de facturas DTE
    codigo_lote = fields.Char(string='Código de procesamiento DTE por lote')

    # Campos Digitados DTE Exportación
    flete = fields.Monetary(string='Flete')
    seguro = fields.Monetary(string='Seguro')

    es_exportacion = fields.Boolean(compute='_compute_es_exportacion', string='Es Exportación', default=False,
                                    store=True)

    # Campos incompletos de modelo exportacion

    placa_trans = fields.Char(string='Placa de Transporte')
    num_conductor = fields.Char(string='Número de Conductor')
    nombre_conductor = fields.Char(string='Nombre de Conductor')

    # Campos para impuestos retencion y percepcion

    retencion_fc = fields.Float(string="Retención", compute="_compute_iva_retenido_fc")
    percepcion_fc = fields.Float(string="Percepción", compute="_compute_iva_percibido_fc")
    rete_renta = fields.Float(string="Retención de renta 10%", compute="_compute_retencion")

    # Campos para documento contable de liquidacion

    fecha_inicio_dcl = fields.Date(string="Fecha inicio Periodo de liquidación")
    fecha_final_dcl = fields.Date(string="Fecha Final Periodo de liquidación")
    porcentaje_comision_cdl = fields.Float(string="Porcentaje de comisión")
    comision_dcl = fields.Float(string="Comisión", compute="_compute_comision_dcl")
    iva_comision_dcl = fields.Float(string="Iva de Comisión", compute="_compute_iva_comision_dcl")
    amount_total_liquidar_dcl = fields.Float(string="Valor liquido a pagar", compute="_compute_amount_liquidar")

    @api.depends('comision_dcl')
    def _compute_iva_comision_dcl(self):
        for move in self:
            move.iva_comision_dcl = move.comision_dcl * 0.13

    @api.depends('porcentaje_comision_cdl', 'amount_untaxed')
    def _compute_comision_dcl(self):
        for move in self:
            move.comision_dcl = (move.porcentaje_comision_cdl/100) * move.amount_untaxed

    @api.depends('porcentaje_comision_cdl', 'amount_untaxed')
    def _compute_amount_liquidar(self):
        for move in self:
            move.amount_total_liquidar_dcl = move.amount_total - move.comision_dcl - move.iva_comision_dcl


    @api.depends('invoice_line_ids.tax_ids', 'invoice_line_ids.price_subtotal')
    def _compute_retencion(self):
        for move in self:
            total_amount = sum(move.invoice_line_ids.mapped('price_subtotal'))
            impuestos_renta = move.invoice_line_ids.mapped('tax_ids').filtered(lambda tax: tax.amount == -10)

            if impuestos_renta:
                anticipo_amount = total_amount * 0.10
                move.rete_renta = anticipo_amount
            else:
                move.rete_renta = 0.0


    @api.depends('invoice_line_ids.tax_ids', 'invoice_line_ids.price_subtotal')
    def _compute_iva_percibido_fc(self):
        for move in self:
            total_amount = sum(move.invoice_line_ids.mapped('price_subtotal'))
            impuestos_1 = move.invoice_line_ids.mapped('tax_ids').filtered(lambda tax: tax.amount == 1)

            if impuestos_1:
                anticipo_amount = total_amount * 0.01
                move.percepcion_fc = anticipo_amount
            else:
                move.percepcion_fc = 0.0

    @api.depends('invoice_line_ids.tax_ids', 'invoice_line_ids.price_subtotal')
    def _compute_iva_retenido_fc(self):
        for move in self:
            total_amount = sum(move.invoice_line_ids.mapped('price_subtotal'))
            impuestos_1 = move.invoice_line_ids.mapped('tax_ids').filtered(lambda tax: tax.amount == -1)

            if impuestos_1:
                anticipo_amount = total_amount * (-0.01)
                move.retencion_fc = round(anticipo_amount, 4)
            else:
                move.retencion_fc = 0

    @api.depends('journal_id')
    def _compute_es_exportacion(self):
        for record in self:
            if record.journal_id.document_type_sv == 11 or record.journal_id.document_type_sv == '11':
                record.es_exportacion = True
            else:
                record.es_exportacion = False

    @api.depends('amount_total', 'flete', 'seguro')
    def _compute_total_exportacion(self):
        for record in self:
            record.total_exportacion = record.amount_total + record.flete + record.seguro

    observaciones = fields.Char(string='Observaciones')
    num_pago_electronico = fields.Char(string='Número de Pago Electrónico')

    # Codigo de generacion

    uuid_generation_code = fields.Char(string='Código de generación', readonly=True, store=True,
                                       default=lambda self: str(uuid.uuid4()).upper(), tracking=True)

    documento_firmado = fields.Text(string='Número de firmado', readonly=True)

    estado_firmado = fields.Char(string='Estado del firmado', readonly=True)

    estado_dte = fields.Selection(string='Estado del documento DTE', selection=[
        ('no_facturado', 'DTE No Generado'),
        ('procesado',
         'DTE Procesado'),
        ('anulada',
         'DTE Anulado'),
        ('procesado_contingencia',
         'DTE Procesado Contingencia'),
        ('procesado_lote',
         'DTE Procesado por Lote')
    ], default='no_facturado',
                                  help="Ver el estado de proceso de la factura", readonly=True, tracking=True)

    number_journal = fields.Selection(related="journal_id.document_type_sv",

                                      string="Tipo de documento relacionado en el diario", readonly=True)

    json_data = fields.Char(string="JSON del firmador", readonly=True)
    json_mh = fields.Char(string="JSON de respuesta MH", readonly=True)
    json_total = fields.Text(string="JSON DTE", readonly=True)

    # sequence_number_next = fields.Integer(string='Id Envío', compute='_compute_sequence_number_next')

    id_envio = fields.Integer(
        string="Id envio",
        default=lambda self: self.env['ir.sequence'].next_by_code('increment_id_envio'))

    original_invoice_id = fields.Many2one(
        'account.move', string='Factura relacionada')

    # campos solo DTE contingencias

    documento_firmado_contingencia = fields.Char(
        string='Número de firmado', readonly=True)

    # mensaje por parte del MH
    mensaje = fields.Char(string="Mensaje recibido",
                          default="No recibido", readonly=True)
    # hora de fin del DTE
    hora_final = fields.Char(string='Hora fin de la contingencia',
                             help="La hora final tiene que ser en siguiente formato HH:MM:SS ")

    estado_contingencia = fields.Char(
        string="Estado de firmado", readonly=True)

    sello_recibido = fields.Char(
        string='Sello de Confirmación', readonly=True, default="Sello no generado")

    estado_dte_contingencia = fields.Char(string='Estado del documento DTE', default='Factura no generada',
                                          help="Ver el estado de proceso de la factura", readonly=True, tracking=True)

    venta_cuenta_terceros = fields.Many2one('res.partner', string="Venta a cuenta de terceros",
                                            domain=[('document_nit', '!=', False)],
                                            help="Establece un tercero al cual asigsnarle la venta, necesita configurar el Nombre y NIT en el contacto")

    # num_correlativo solo para dte contingencia
    # num_correlativo= fields.Many2one('ir.sequence',string="Número Correlativo", readonly=True)

    numero_correlativo = fields.Char(
        string='Número correlativo', readonly=True)

    # @api.model
    # def create(self, vals):
    #   if vals.get('num_correlativo', False):
    #      sequence = self.env['ir.sequence'].browse(vals['num_correlativo'])
    #     vals['name'] = sequence.next_by_id()
    # return super(AccountMove, self).create(vals)
    qr_link = fields.Char(string='Enlace QR', compute='_compute_qr_link', default="Código QR no generado",
                          readonly=True)

    # validar para que sea mayor  a 100 caracteres
    # @api.constrains('cod_asociado')
    # def _check_word_count(self):
    #   for record in self:
    #      if record.cod_asociado and len(record.cod_asociado) < 100:
    #         raise ValidationError("El campo 'Documento Asociado' no puede tener menos de 100 caracteres.")
    # validar para que sea mayor  a 300 caracteres
    # @api.constrains('detalle_documento')
    # def _check_word_counter(self):
    #    for record in self:
    #       if record.detalle_documento and len(record.detalle_documento) < 300:

    #          raise ValidationError("El campo 'Descripción de documento asociado' no puede tener menos de 300 caracteres.")

    # sequence_number_next = fields.Integer(string='Id Envío', compute='_compute_sequence_number_next')

    last_numbers = fields.Integer(
        string='ID Envio', compute='_compute_last_numbers', readonly=True)

    original_invoice_id = fields.Many2one(
        'account.move', string='Factura relacionada')

    # numero_control = fields.Char(string='Número de Control', compute='_compute_numero_control',
    #                              readonly=True, store=True)

    # @api.depends('journal_id', 'journal_id.document_type_sv', 'company_id')
    # def _compute_numero_control(self):
    #     for record in self:
    #         codigo_casa_matriz = '00' + record.tipo_establecimiento
    #         tipo_documento = record.journal_id.document_type_sv
    #         codigo_punto_venta = '0000'
    #         secuencia = self.env.ref('l10n_sv_rk.sequence_consumidor_final_dte').next_by_id()
    #         secuencia_sin_prefix = int(secuencia.replace('FE-FC', ''))
    #         numero_control = f'DTE-{tipo_documento}-{codigo_casa_matriz}{codigo_punto_venta}-{secuencia_sin_prefix:015}'
    #         record.numero_control = numero_control
    #
    #         numero_control = False
    #         if record.journal_id.document_type_sv == '01':  # asumiendo que solo quieres generar número de control para facturas
    #             secuencia = self.env.ref('nombre_de_modulo.sequence_consumidor_final_dte').next_by_id()
    #             codigo_casa_matriz = '00' + record.tipo_establecimiento
    #             codigo_punto_venta = '0000'
    #             tipo_documento = record.journal_id.document_type_sv
    #             numero_control = f'DTE-{tipo_documento}-{codigo_casa_matriz}{codigo_punto_venta}-{secuencia:015}'
    #         record.numero_control = numero_control
    suma_total=fields.Integer(string="Total de firmas", readonly=True,store=True)
    #account_move_ids = fields.One2many('account.move', 'destino_model_id', string='Account Moves')

    # Campos cuando se invalida documento.

    uuid_generation_code_anuladado = fields.Char(string="Código de generación al invalidar DTE", readonly=True, store=True)

    sello_recibido_anulado = fields.Char(string="Sello de recibido al invalidar DTE", readonly=True, store=True)

    date_anulado = fields.Char(string="Fecha de anulación", readonly=True, store=True)

    values = {
        'estado_firmado': False,
        'documento_firmado': False
    }

    
    #metodo para la autorizacion del firmador y contador de firmas
    def enviar_solicitud(self,url, payload):
        headers = {
           'Content-Type': 'application/json',
            'Authorization': self.company_id.token_code
        }

        try:
           response = requests.post(url, headers=headers, data=payload)
           json_response = response.json()
        except Exception as e:
            print(e)
            raise ValidationError('Ocurrió un error al conectarse al servicio de firmado')
        
       # estado_firmado = json_response['status']
        documento_firmado = json_response['body']
          
        if response.status_code == 200:
            if json_response.get('status') == 'OK':
                self.values['estado_firmado'] = json_response['status']
                self.values['documento_firmado'] = documento_firmado
                
                documento_firmado_anterior = None
                counter_firmas = self.counter_firmas or 0
 
                if self.values['documento_firmado'] != documento_firmado_anterior:
                        counter_firmas += 1
                documento_firmado_anterior = self.values['documento_firmado']

                self.values['counter_firmas'] = counter_firmas
               
                self.write(self.values)

                payload_string = json.loads(payload)
                dte_json = payload_string['dteJson']
                self.json_data = json.dumps(dte_json)
                self.message_post(body=f"El documento se firmo de manera correcta.", message_type="notification")
            else:
               raise ValidationError(json_response.get('body', {}).get('mensaje', 'Error desconocido'))
        else:
           raise ValidationError('Error al conectarse al servidor de DGII: %s' % response.content)
     
    #actualiza el campo suma_total
    @api.model
    def actualizar_suma_totals(self):       
        
        query = "SELECT SUM(counter_firmas) FROM account_move;" 
        self.env.cr.execute(query)
        resultado = self.env.cr.fetchone()
        suma_total = resultado[0] if resultado else 0.0

        self.suma_total = suma_total
        
        return True
    
    @api.model
    def actualizar_suma_total(self):
        mes = datetime.now().month

        query = "SELECT SUM(counter_firmas) FROM account_move WHERE EXTRACT(MONTH FROM fecha_factura) = %s;"
        self.env.cr.execute(query, (mes,))
        resultado = self.env.cr.fetchone()
        suma_total = resultado[0] if resultado else 0.0

        self.suma_total = suma_total
        

        return True
    
    
    #recorre por cada tiempo transcurrido y muestra los datos 
    @api.model
    def actualizar_cp(self):
        update_time = self.search([])
        for up in update_time:
            up.actualizar_suma_total()

    


   

    
    def url_hora(self):
        tz = pytz.timezone('America/El_Salvador')
        hora_actual = datetime.now(tz).strftime('%H:%M:%S')
        url = 'http://167.99.8.116:8113/firmardocumento/?content-Type=application/JSON&nit=06140506171049'
           

        return {
            'tz': tz,
            'hora_actual': hora_actual,
            'url': url
        }


    # Metodo para firmar Consumidor Final Electronico
    def firmar_documentos_fc(self):
        tz = pytz.timezone('America/El_Salvador')
        hora_actual = datetime.now(tz).strftime('%H:%M:%S')
        url = 'http://167.99.8.116:8113/firmardocumento/?content-Type=application/JSON&nit=06142809011497'

        num_documento_options = {
            '36': self.partner_id.document_nit_compute,
            '13': self.partner_id.document_dui,
            '03': self.partner_id.document_pasaporte,
            '02': self.partner_id.document_carnet_residente,
            '37': self.tipo_identificacion_receptor_otro,
        }
        items = []
        for i, invoice_line in enumerate(self.invoice_line_ids):
            item = {
                "numItem": i + 1,  # Agregar 1 al número de secuencia para empezar desde 1 en lugar de 0
                "tipoItem": int(invoice_line.product_id.type_item_edi),
                "numeroDocumento": None,
                "cantidad": invoice_line.quantity,
                "codigo": None if not invoice_line.product_id.default_code else invoice_line.product_id.default_code,
                "codTributo": None if not invoice_line.product_id.tributo_iva else invoice_line.product_id.tributo_iva,
                "uniMedida": int(invoice_line.product_id.cat_unidad_medida.clave),
                "descripcion": invoice_line.name,
                "precioUni": round(invoice_line.price_unit * 1.13,
                                   5) if invoice_line.move_type_ids == 'gravadas' else round(invoice_line.price_unit,
                                                                                             5),
                "montoDescu": round((invoice_line.price_unit * 1.13) * (invoice_line.quantity) * (invoice_line.discount/100),4)
                                        if invoice_line.move_type_ids == 'gravadas' else round((invoice_line.price_unit) * (invoice_line.quantity) * (invoice_line.discount/100),4) ,
                "ventaNoSuj": round(invoice_line.price_subtotal, 5) if invoice_line.move_type_ids == 'nosujetas' else 0,
                "ventaExenta": round(invoice_line.price_subtotal, 5) if invoice_line.move_type_ids == 'exentas' else 0,
                "ventaGravada": round(invoice_line.price_subtotal * 1.13,
                                      5) if invoice_line.move_type_ids == 'gravadas' else 0,
                "tributos": None,
                "psv": invoice_line.price_unit,
                "noGravado": 0,
                "ivaItem": round(invoice_line.price_subtotal * 0.13,
                                 4) if invoice_line.move_type_ids == 'gravadas' else 0,
            }
            items.append(item)

        payload = json.dumps({
            'nit': self.company_id.document_nit,
            'activo': "True",
            'passwordPri': self.company_id.private_pass_mh,
            'dteJson':
                {
                    "identificacion": {
                        "version": self.journal_id.version,
                        "ambiente": self.company_id.modo_prueba,
                        "tipoDte": self.journal_id.document_type_sv,
                        "numeroControl": self.name,
                        "codigoGeneracion": self.uuid_generation_code,
                        "tipoModelo": int(self.modelo_facturacion),
                        "tipoOperacion": int(self.tipo_transmision),
                        "fecEmi": self.fecha_emision.strftime('%Y-%m-%d'),
                        "horEmi": hora_actual,
                        "tipoMoneda": self.currency_id.name,
                        "tipoContingencia": None if self.tipo_contingencia == "None" else self.tipo_contingencia,
                        "motivoContin": None if not self.motivo_contig else self.motivo_contig
                    },
                    "documentoRelacionado": None if not self.original_invoice_id else [
                        {
                            "tipoDocumento": self.original_invoice_id.number_journal,
                            "tipoGeneracion": int(self.original_invoice_id.tipo_generacion_documento),
                            "numeroDocumento": self.original_invoice_id.uuid_generation_code,
                            "fechaEmision": self.original_invoice_id.fecha_emision.strftime('%Y-%m-%d'),
                        }
                    ],
                    "emisor": {
                        "nit": self.company_id.document_nit,
                        "nrc": self.company_id.document_vat,
                        "nombre": self.company_id.name,
                        "codActividad": self.company_id.document_giro_company.code,
                        "descActividad": self.company_id.document_giro_company.name,
                        "nombreComercial": self.company_id.name,
                        "tipoEstablecimiento": self.tipo_establecimiento,
                        "direccion": {
                            "departamento": self.company_id.state_id.code,
                            "municipio": self.company_id.munic_id.code,
                            "complemento": self.company_id.street
                        },
                        "telefono": self.company_id.phone,
                        "correo": self.company_id.email,
                        "codEstableMH": None if not self.company_id.cod_estable_mh else self.company_id.cod_estable_mh,
                        "codEstable": None if not self.company_id.cod_estable else self.company_id.cod_estable,
                        "codPuntoVentaMH": None if not self.company_id.cod_pv_mh else self.company_id.cod_pv_mh,
                        "codPuntoVenta": None if not self.company_id.cod_pv else self.company_id.cod_pv
                    },
                    "receptor": {
                        "tipoDocumento": None if not self.tipo_identificacion_receptor else self.tipo_identificacion_receptor,
                        "numDocumento": num_documento_options.get(self.tipo_identificacion_receptor, None),
                        "nrc": None if not self.partner_id.vat else self.partner_id.document_vat_compute,
                        "nombre": self.partner_id.name,
                        "codActividad": None if not self.partner_id.document_giro_res else self.partner_id.document_giro_res.code,
                        "descActividad": None if not self.partner_id.document_giro_res else self.partner_id.document_giro_res.name,
                        "direccion": None if not self.partner_id.munic_id else {
                            "departamento": self.partner_id.state_id.code,
                            "municipio": self.partner_id.munic_id.code,
                            "complemento": self.partner_id.street
                        },
                        "telefono": None if not self.partner_id.phone else self.partner_id.phone,
                        "correo": None if not self.partner_id.email else self.partner_id.email
                    },
                    "otrosDocumentos": None if not self.otros_documentos_asociados else [
                        {
                            "codDocAsociado": int(self.otros_documentos_asociados),
                            "descDocumento": None if not self.cod_asociado else self.cod_asociado,
                            "detalleDocumento": None if not self.detalle_documento else self.detalle_documento,
                            "medico": None if self.otros_documentos_asociados != 3 else {
                                "nombre": self.cod_asociado,
                                "nit": self.detalle_documento,
                                "docIdentificacion": self.detalle_documento,
                                "tipoServicio": int(self.codigo_tipo_servicio_medico)
                            }
                        }
                    ],
                    "ventaTercero": None if not self.venta_cuenta_terceros else {
                        "nit": self.venta_cuenta_terceros.document_nit_compute,
                        "nombre": self.venta_cuenta_terceros.name
                    },
                    "cuerpoDocumento": items,
                    "resumen": {
                        "totalNoSuj": sum(
                            line.price_subtotal for line in self.invoice_line_ids if line.move_type_ids == 'nosujetas'),
                        "totalExenta": sum(
                            line.price_subtotal for line in self.invoice_line_ids if line.move_type_ids == 'exentas'),
                        "totalGravada": round(sum(line.price_subtotal for line in self.invoice_line_ids if
                                                  line.move_type_ids == 'gravadas') * 1.13, 2),
                        "subTotalVentas": self.amount_total if self.retencion_fc == 0 else round(
                            self.amount_untaxed * 1.13, 2),
                        "descuNoSuj": 0,
                        "descuExenta": 0,
                        "descuGravada": 0,
                        "porcentajeDescuento": 0,
                        "totalDescu": round(sum((line.price_unit * line.quantity) * (line.discount/100) for line in self.invoice_line_ids),2),
                        "tributos": None,
                        "subTotal": self.amount_total if self.retencion_fc == 0 else round(self.amount_untaxed * 1.13,
                                                                                           2),
                        "ivaRete1": round(-self.retencion_fc, 2),
                        "reteRenta": round(self.rete_renta,2),
                        "montoTotalOperacion": round(self.amount_untaxed * 1.13,
                                                     2) if self.retencion_fc != 0 else self.amount_total,
                        "totalNoGravado": 0,
                        "totalPagar": self.amount_total,
                        "totalLetras": self.amount_to_text,
                        "totalIva": round(self.amount_tax - self.retencion_fc, 2),
                        "saldoFavor": 0,
                        "condicionOperacion": 1 if not self.invoice_payment_term_id else int(
                            self.invoice_payment_term_id.condicion_operacion),
                        "pagos": None if not self.forma_pago_id else
                        [{
                            'codigo': self.forma_pago_id.code,
                            'montoPago': self.amount_total,
                            'referencia': None,
                            'plazo': None,
                            'periodo': None,

                        }],
                        "numPagoElectronico": None if not self.num_pago_electronico else self.num_pago_electronico
                    },
                    "extension": None,
                    "apendice": [
                        {
                            "campo": "numeroInterno",
                            "etiqueta": "numeroInterno",
                            "valor": self.payment_reference
                        }
                    ]
                }
        })
        print(payload)
        self.enviar_solicitud(url,payload)


      
    def firmar_documentos_ccf(self):
        tz = pytz.timezone('America/El_Salvador')
        hora_actual = datetime.now(tz).strftime('%H:%M:%S')
        url = 'http://167.99.8.116:8113/firmardocumento/?content-Type=application/JSON&nit=06142809011497'

        num_documento_options = {
            '36': self.partner_id.document_nit_compute,
            '13': self.partner_id.document_dui_compute,
            '03': self.partner_id.document_pasaporte,
            '02': self.partner_id.document_carnet_residente,
            '37': self.tipo_identificacion_receptor_otro,
        }
        items = []
        for i, invoice_line in enumerate(self.invoice_line_ids):
            taxes = []
            for tax in invoice_line.tax_ids:
                if tax.amount != -1 and tax.amount != 1:  # Agrega esta condición para omitir los impuestos con valor -1
                    tax_dict = tax.code_dte_sv
                    taxes.append(tax_dict)

            taxes_resume = []
            for tax in invoice_line.tax_ids:
                if tax.amount != -1 and tax.amount != 1:  # Agrega esta condición para omitir los impuestos con valor -1
                    tax_dict_res = {
                        "codigo": tax.code_dte_sv,
                        "descripcion": tax.name,
                        "valor": round((tax.amount / 100) * self.amount_untaxed, 2)
                        # Agrega aquí los demás campos que necesites
                    }
                    taxes_resume.append(tax_dict_res)

            item = {
                "numItem": i + 1,  # Agregar 1 al número de secuencia para empezar desde 1 en lugar de 0
                "tipoItem": int(invoice_line.product_id.type_item_edi),
                "numeroDocumento": None,
                "codigo": None if not invoice_line.product_id.default_code else invoice_line.product_id.default_code,
                "codTributo": None if not invoice_line.product_id.tributo_iva else invoice_line.product_id.tributo_iva,
                "descripcion": invoice_line.name,
                "cantidad": invoice_line.quantity,
                "uniMedida": int(invoice_line.product_id.cat_unidad_medida.clave),
                "precioUni": float(invoice_line.price_unit),
                "montoDescu": round((invoice_line.price_unit) * (invoice_line.quantity) * (invoice_line.discount/100),4),
                "ventaNoSuj": round(invoice_line.price_subtotal, 5) if invoice_line.move_type_ids == 'nosujetas' else 0,
                "ventaExenta": round(invoice_line.price_subtotal, 5) if invoice_line.move_type_ids == 'exentas' else 0,
                "ventaGravada": round(invoice_line.price_subtotal,
                                      5) if invoice_line.move_type_ids == 'gravadas' else 0,
                "tributos": None if not taxes else taxes,
                "psv": invoice_line.price_unit,
                "noGravado": 0,
            }
            items.append(item)

        payload = json.dumps({
            'nit': self.company_id.document_nit,
            'activo': "True",
            'passwordPri': self.company_id.private_pass_mh,
            'dteJson':
                {
                    "identificacion": {
                        "version": self.journal_id.version,
                        "ambiente": self.company_id.modo_prueba,
                        "tipoDte": self.journal_id.document_type_sv,
                        "numeroControl": self.name,
                        "codigoGeneracion": self.uuid_generation_code,
                        "tipoOperacion": int(self.tipo_transmision),
                        "tipoModelo": int(self.modelo_facturacion),
                        "fecEmi": self.fecha_emision.strftime('%Y-%m-%d'),
                        "horEmi": hora_actual,
                        "tipoMoneda": self.currency_id.name,
                        "tipoContingencia": None if self.tipo_contingencia == "None" else int(self.tipo_contingencia),
                        "motivoContin": None if not self.motivo_contig else self.motivo_contig
                    },
                    "documentoRelacionado": None if not self.original_invoice_id else [
                        {
                            "tipoDocumento": self.original_invoice_id.number_journal,
                            "tipoGeneracion": int(self.original_invoice_id.tipo_generacion_documento),
                            "numeroDocumento": self.original_invoice_id.uuid_generation_code,
                            "fechaEmision": self.original_invoice_id.fecha_emision.strftime('%Y-%m-%d'),
                        }
                    ],
                    "emisor": {
                        "nit": self.company_id.document_nit,
                        "nrc": self.company_id.document_vat,
                        "nombre": self.company_id.name,
                        "codActividad": self.company_id.document_giro_company.code,
                        "descActividad": self.company_id.document_giro_company.name,
                        "nombreComercial": self.company_id.name,
                        "tipoEstablecimiento": self.tipo_establecimiento,
                        "direccion": {
                            "departamento": self.company_id.state_id.code,
                            "municipio": self.company_id.munic_id.code,
                            "complemento": self.company_id.street
                        },
                        "telefono": self.company_id.phone,
                        "correo": self.company_id.email,
                        "codEstableMH": None if not self.company_id.cod_estable_mh else self.company_id.cod_estable_mh,
                        "codEstable": None if not self.company_id.cod_estable else self.company_id.cod_estable,
                        "codPuntoVentaMH": None if not self.company_id.cod_pv_mh else self.company_id.cod_pv_mh,
                        "codPuntoVenta": None if not self.company_id.cod_pv else self.company_id.cod_pv
                    },
                    "receptor": {
                        "nit": self.partner_id.document_nit_compute,
                        "nrc": self.partner_id.document_vat_compute,
                        "nombre": self.partner_id.name,
                        "codActividad": None if not self.partner_id.document_giro_res else self.partner_id.document_giro_res.code,
                        "descActividad": None if not self.partner_id.document_giro_res else self.partner_id.document_giro_res.name,
                        "nombreComercial": self.partner_id.name,
                        "direccion": None if not self.partner_id.munic_id else {
                            "departamento": self.partner_id.state_id.code,
                            "municipio": self.partner_id.munic_id.code,
                            "complemento": self.partner_id.street
                        },
                        "telefono": None if not self.partner_id.phone else self.partner_id.phone,
                        "correo": self.partner_id.email
                    },
                    "otrosDocumentos": None if not self.otros_documentos_asociados else [
                        {
                            "codDocAsociado": int(self.otros_documentos_asociados),
                            "descDocumento": None if not self.cod_asociado else self.cod_asociado,
                            "detalleDocumento": None if not self.detalle_documento else self.detalle_documento,
                            "medico": None if self.otros_documentos_asociados != 3 else {
                                "nombre": self.cod_asociado,
                                "nit": self.detalle_documento,
                                "docIdentificacion": self.detalle_documento,
                                "tipoServicio": int(self.codigo_tipo_servicio_medico)
                            }
                        }
                    ],
                    "ventaTercero": None if not self.venta_cuenta_terceros else {
                        "nit": self.venta_cuenta_terceros.document_nit_compute,
                        "nombre": self.venta_cuenta_terceros.name
                    },
                    "cuerpoDocumento": items,
                    "resumen": {
                        "totalNoSuj": sum(
                            line.price_subtotal for line in self.invoice_line_ids if line.move_type_ids == 'nosujetas'),
                        "totalExenta": sum(
                            line.price_subtotal for line in self.invoice_line_ids if line.move_type_ids == 'exentas'),
                        "totalGravada": round(sum(line.price_subtotal for line in self.invoice_line_ids if
                                                  line.move_type_ids == 'gravadas'), 2),
                        "subTotalVentas": self.amount_untaxed,
                        "descuNoSuj": 0,
                        "descuExenta": 0,
                        "descuGravada": 0,
                        "porcentajeDescuento": 0,
                        "totalDescu": round(sum((line.price_unit * line.quantity) * (line.discount/100) for line in self.invoice_line_ids),2),
                        "tributos": None if not taxes_resume else taxes_resume,
                        "subTotal": self.amount_untaxed,
                        "ivaPerci1": round(self.percepcion_fc,2),
                        "ivaRete1": round(-self.retencion_fc, 2),
                        "reteRenta": round(self.rete_renta,2),
                        "montoTotalOperacion": round(self.amount_untaxed * 1.13,
                                                     2) if self.retencion_fc != 0 or self.percepcion_fc != 0 else self.amount_total,
                        "totalNoGravado": 0,
                        "totalPagar": self.amount_total,
                        "totalLetras": self.amount_to_text,
                        "saldoFavor": 0,
                        "condicionOperacion": 1 if not self.invoice_payment_term_id else int(
                            self.invoice_payment_term_id.condicion_operacion),
                        "pagos": None if not self.forma_pago_id else
                        [{
                            'codigo': self.forma_pago_id.code,
                            'montoPago': self.amount_total,
                            'referencia': None,
                            'plazo': None,
                            'periodo': None,

                        }],
                        "numPagoElectronico": None if not self.num_pago_electronico else self.num_pago_electronico
                    },
                    "extension": None,
                    "apendice": [
                        {
                            "campo": "refInterno",
                            "etiqueta": "referenciaInterna",
                            "valor": None if not self.payment_reference else self.payment_reference
                        }
                    ]
                }
        })
        print(payload)
        self.enviar_solicitud(url,payload)
       

    # Factura de Exportación Electrónica (fex)
    def firmar_documentos_fex(self):
        tz = pytz.timezone('America/El_Salvador')
        hora_actual = datetime.now(tz).strftime('%H:%M:%S')
        url = 'http://167.99.8.116:8113/firmardocumento/?content-Type=application/JSON&nit=06142809011497'

        num_documento_options = {
            '36': self.partner_id.document_nit_compute,
            '13': self.partner_id.document_dui_compute,
            '03': self.partner_id.document_pasaporte,
            '02': self.partner_id.document_carnet_residente,
            '37': self.tipo_identificacion_receptor_otro,
        }

        # Declaración de variables auxiliares
        items = []
        cantidad_lineas = 0
        has_product = False
        has_service = False
        tipo_item: int = 1
        totalGravada = 0
        monto_descuento_total = 0
        aux_por_desc = 0
        porcentaje_descuento = 0
        total_dte = 0

        # Extracción de datos de lista de productos en factura
        for i, invoice_line in enumerate(self.invoice_line_ids):
            taxes = []
            for tax in invoice_line.tax_ids:
                tax_dict = tax.code_dte_sv

                taxes.append(tax_dict)
            item = {
                "numItem": i + 1,
                "cantidad": invoice_line.quantity,
                "codigo": None if not invoice_line.product_id.default_code else invoice_line.product_id.default_code,
                "uniMedida": int(invoice_line.product_id.cat_unidad_medida.clave),
                "descripcion": invoice_line.name,
                "precioUni": round(invoice_line.price_unit, 2),
                "montoDescu": round((invoice_line.price_unit) * (invoice_line.quantity) * (invoice_line.discount/100),4),
                "ventaGravada": invoice_line.price_subtotal,
                "tributos": None,
                "noGravado": 0
            }
            items.append(item)

            # Cálculo de total de formulario electrónico
            total_dte += ((round(invoice_line.price_unit * 1.13, 2) * invoice_line.quantity) - (
                (round(invoice_line.price_unit * 1.13, 2) * invoice_line.discount)))

            # Cálculo de descuento total por cada línea de producto 1/2
            if invoice_line.discount:
                cantidad_lineas += 1
                aux_por_desc += invoice_line.discount
                monto_descuento_total += invoice_line.price_subtotal * invoice_line.discount

            # Cálculo de tipo de productos en factura 1/2
            if invoice_line.product_id.type_item_edi == 1:
                has_product = True
            elif invoice_line.product_id.type_item_edi == 2:
                has_product = True
            elif invoice_line.product_id.type_item_edi == 3:
                has_product = True
                has_service = True
            totalGravada += round(invoice_line.price_total)

        # Cálculo de descuento total por cada línea de producto 1/2
        porcentaje_descuento = round(
            aux_por_desc / (1 if cantidad_lineas == 0 else cantidad_lineas), 2)

        # Cálculo de tipo de productos en factura 2/2
        if has_product:
            tipo_item = 1
        elif has_service:
            tipo_item = 2
        elif has_product and has_service:
            tipo_item = 3

        payload = json.dumps({

            # 'nit': self.partner_id.document_nit,
            # 'activo': "True",
            # 'passwordPri': self.company_id.private_pass_mh,
            # "content-Type": "application/JSON",
            "nit": self.company_id.document_nit,
            "activo": "True",
            "passwordPri": self.company_id.private_pass_mh,
            "dteJson": {
                "identificacion": {
                    "version": self.journal_id.version,
                    "ambiente": self.company_id.modo_prueba,
                    "tipoDte": self.journal_id.document_type_sv,
                    "numeroControl": self.name,
                    "codigoGeneracion": self.uuid_generation_code,
                    "tipoModelo": int(self.modelo_facturacion),
                    "tipoOperacion": int(self.tipo_transmision),
                    "tipoContingencia": None if self.tipo_contingencia == "None" else self.tipo_contingencia,
                    "motivoContigencia": None if not self.motivo_contig else self.motivo_contig,
                    "fecEmi": self.fecha_emision.strftime('%Y-%m-%d'),
                    "horEmi": hora_actual,
                    "tipoMoneda": self.currency_id.name
                },
                "emisor": {
                    "nit": self.company_id.document_nit,
                    "nrc": self.company_id.document_vat,
                    "nombre": self.company_id.name,
                    "codActividad": self.company_id.document_giro_company.code,
                    "descActividad": self.company_id.document_giro_company.name,
                    "nombreComercial": self.company_id.name,
                    "tipoEstablecimiento": self.tipo_establecimiento,
                    "direccion": {
                        "departamento": self.company_id.state_id.code,
                        "municipio": self.company_id.munic_id.code,
                        "complemento": self.company_id.street
                    },
                    "telefono": self.company_id.phone,
                    "correo": self.company_id.email,
                    "codEstableMH": None if not self.company_id.cod_estable_mh else self.company_id.cod_estable_mh,
                    "codEstable": None if not self.company_id.cod_estable else self.company_id.cod_estable,
                    "codPuntoVentaMH": None if not self.company_id.cod_pv_mh else self.company_id.cod_pv_mh,
                    "codPuntoVenta": None if not self.company_id.cod_pv else self.company_id.cod_pv,
                    "tipoItemExpor": tipo_item,
                    "recintoFiscal": self.company_id.recinto_fiscal_id.code,
                    "regimen": self.company_id.regimen_fiscal_id.codigo
                },
                "receptor": {
                    "nombre": self.partner_id.name,
                    "tipoDocumento": None if not self.tipo_identificacion_receptor else self.tipo_identificacion_receptor,
                    "numDocumento": num_documento_options.get(self.tipo_identificacion_receptor, None),
                    "nombreComercial": self.partner_id.name,
                    "codPais": self.partner_id.codigo_pais.code,
                    "nombrePais": self.partner_id.codigo_pais.name,
                    "complemento": self.partner_id.street,
                    "tipoPersona": 1 if self.is_company else 2,
                    "descActividad": None if not self.partner_id.document_giro_res else self.partner_id.document_giro_res.name,
                    "telefono": None if not self.partner_id.phone else self.partner_id.phone,
                    "correo": None if not self.partner_id.email else self.partner_id.email
                },
                "otrosDocumentos": None if not self.otros_documentos_asociados == 4 else [{
                    "codDocAsociado": int(self.otros_documentos_asociados),
                    "descDocumento": None if self.cod_asociado else self.cod_asociado,
                    "detalleDocumento": None if self.detalle_documento else self.detalle_documento,
                    "modoTransp": None if self.modo_transporte else self.modo_transporte,
                    "placaTrans": None if self.placa_trans else self.placa_trans,
                    "numConductor": None if self.num_conductor else self.num_conductor,
                    "nombreConductor": None if self.nombre_conductor else self.nombre_conductor
                }],
                "ventaTercero": None if not self.venta_cuenta_terceros else {
                    "nit": self.venta_cuenta_terceros.document_nit_compute,
                    "nombre": self.venta_cuenta_terceros.name
                },
                "cuerpoDocumento": items,
                "resumen": {
                    "totalGravada": self.amount_total,
                    "descuento": round(monto_descuento_total * self.subtotal, 2),
                    "porcentajeDescuento": porcentaje_descuento,
                    "totalDescu": round(sum(
                        (line.price_unit * line.quantity) * (line.discount / 100) for line in self.invoice_line_ids),
                                        2),
                    "montoTotalOperacion": self.total_exportacion if self.flete or self.seguro else self.amount_total,
                    "totalNoGravado": self.subtotal,
                    "totalPagar": self.total_exportacion if self.flete or self.seguro else self.amount_total,
                    "totalLetras": self.amount_to_text if not self.flete or self.seguro else self.amount_to_text_exp,
                    "condicionOperacion": 1 if not self.invoice_payment_term_id else int(
                        self.invoice_payment_term_id.condicion_operacion),
                    "pagos": None if not self.forma_pago_id.code else [{
                        "codigo": self.forma_pago_id.code,
                        "montoPago": self.amount_total,
                        "referencia": self.payment_reference,
                        "plazo": None,
                        "periodo": None
                    }],
                    "codIncoterms": None if not self.catalogo_inco else self.catalogo_inco.code,
                    "descIncoterms": None if not self.catalogo_inco else str(
                        self.catalogo_inco.codeIncoterms + "-" + self.catalogo_inco.description),
                    "observaciones": "Ninguna" if not self.observaciones else self.observaciones,
                    "flete": self.flete,
                    "numPagoElectronico": None if not self.num_pago_electronico else self.num_pago_electronico,
                    "seguro": self.seguro
                },
                "apendice":
                    [{
                        "campo": "refInterno",
                        "etiqueta": "referenciaInterna",
                        "valor": None if not self.payment_reference else self.payment_reference
                    }]
            }
        })
        self.enviar_solicitud(url,payload)
       


    # TODO: Incorporar campos nuevos de dcl en metodo de firmado

    # Documento contable de liquidacion electronica
    def firmar_documentos_fc_cd(self):
        tz = pytz.timezone('America/El_Salvador')
        hora_actual = datetime.now(tz).strftime('%H:%M:%S')
        url = 'http://167.99.8.116:8113/firmardocumento/?content-Type=application/JSON&nit=06142809011497'

        num_documento_options = {
            '36': self.partner_id.document_nit_compute,
            '13': self.partner_id.document_dui_compute,
            '03': self.partner_id.document_pasaporte,
            '02': self.partner_id.document_carnet_residente,
            '37': self.tipo_identificacion_receptor_otro,
        }

        # Extracción de datos de lista de productos en factura
        for i, invoice_line in enumerate(self.invoice_line_ids):
            item = {
                "numItem": i + 1,
                "cantidad": invoice_line.quantity,
                "codigo": None if not invoice_line.product_id.default_code else invoice_line.product_id.default_code,
                "uniMedida": 59,
                "descripcion": invoice_line.name,
                "precioUni": round(invoice_line.price_unit * 1.13, 2),
                "montoDescu": round((invoice_line.price_unit) * (invoice_line.quantity) * (invoice_line.discount/100),4),
                "ventaGravada": round(invoice_line.price_subtotal * 1.13, 2),
                "tributos": None,
                "noGravado": 0
            }
            items.append(item)


        payload = json.dumps({
            "nit": self.company_id.document_nit,
            "activo": "False",
            "passwordPri": self.company_id.private_pass_mh,
            "dteJson": {
                "identificacion": {
                    "version": self.journal_id.version,
                    "ambiente": self.company_id.modo_prueba,
                    "tipoDte": self.journal_id.document_type_sv,
                    "numeroControl": self.name,
                    "codigoGeneracion": self.uuid_generation_code,
                    "tipoModelo": int(self.modelo_facturacion),
                    "tipoOperacion": int(self.tipo_transmision),
                    "tipoContingencia": None if self.tipo_contingencia == "None" else self.tipo_contingencia,
                    "motivoContin": None if not self.motivo_contig else self.motivo_contig,
                    "fecEmi": self.fecha_emision.strftime('%Y-%m-%d'),
                    "horEmi": hora_actual,
                    "tipoMoneda": self.currency_id.name
                },
                "emisor": {
                    "nit": self.company_id.document_nit,
                    "nrc": self.company_id.document_vat,
                    "nombre": self.company_id.name,
                    "codActividad": self.company_id.document_giro_company.code,
                    "descActividad": self.company_id.document_giro_company.name,
                    "nombreComercial": self.company_id.name,
                    "tipoEstablecimiento": self.tipo_establecimiento,
                    "direccion": {
                        "departamento": self.company_id.state_id.code,
                        "municipio": self.company_id.munic_id.code,
                        "complemento": self.company_id.street
                    },
                    "telefono": self.company_id.phone,
                    "codigoMH": None if not self.company_id.cod_estable_mh else self.company_id.cod_estable_mh,
                    "codigo": None if not self.company_id.cod_estable else self.company_id.cod_estable,
                    "puntoVentaMH": None if not self.company_id.cod_pv_mh else self.company_id.cod_pv_mh,
                    "puntoVenta": None if not self.company_id.cod_pv else self.company_id.cod_pv,
                    "correo": self.company_id.email
                },
                "receptor": {
                    "tipoDocumento": None if not self.tipo_identificacion_receptor else self.tipo_identificacion_receptor,
                    "numDocumento": num_documento_options.get(self.tipo_identificacion_receptor, None),
                    "nrc": self.partner_id.vat,
                    "nombre": self.partner_id.name,
                    "codActividad": self.partner_id.document_giro_res.code,
                    "descActividad": None if not self.partner_id.document_giro_res else self.partner_id.document_giro_res.name,
                    "nombreComercial": self.partner_id.name,
                    "direccion": {
                        "departamento": self.partner_id.state_id.code,
                        "municipio": self.partner_id.munic_id.code,
                        "complemento": self.partner_id.street
                    },
                    "telefono": None if not self.partner_id.phone else self.partner_id.phone,
                    "correo": None if not self.partner_id.email else self.partner_id.email
                },
                "cuerpoDocumento": items,
                "resumen": {
                    "totalSujetoRetencion": 1,
                    "totalIVAretenido": 0,
                    "totalIVAretenidoLetras": "cinco dólares"
                },
                "extension": None,
                "apendice": None
            }
        })
        self.enviar_solicitud(url,payload)

    

    # Comprobante de Retención Electrónica (cr)
    def firmar_documentos_cr(self):
        tz = pytz.timezone('America/El_Salvador')
        hora_actual = datetime.now(tz).strftime('%H:%M:%S')
        url = 'http://167.99.8.116:8113/firmardocumento/?content-Type=application/JSON&nit=06142809011497'

        num_documento_options = {
            '36': self.partner_id.document_nit_compute,
            '13': self.partner_id.document_dui_compute,
            '03': self.partner_id.document_pasaporte,
            '02': self.partner_id.document_carnet_residente,
            '37': self.tipo_identificacion_receptor_otro,
        }

        # Declaración de variables auxiliares
        items = []
        cantidad_lineas = 0
        has_product = False
        has_service = False
        tipo_item: int = None
        totalGravada = 0
        monto_descuento_total = 0
        aux_por_desc = 0
        porcentaje_descuento = 0

        # Extracción de datos de lista de productos en factura
        for i, invoice_line in enumerate(self.invoice_line_ids):
            item = {
                "numItem": i + 1,
                "tipoDte": self.original_invoice_id.number_journal,
                "tipoDoc": int(self.original_invoice_id.tipo_generacion_documento),
                "numDocumento": self.original_invoice_id.uuid_generation_code,
                "fechaEmision": self.original_invoice_id.fecha_emision.strftime('%Y-%m-%d'),
                "montoSujetoGrav": self.original_invoice_id.amount_untaxed,
                "codigoRetencionMH": '22',
                "ivaRetenido": -(self.original_invoice_id.retencion_fc),
                "descripcion": invoice_line.product_id.name
            }
            items.append(item)

            # Cálculo de descuento total por cada línea de producto 1/2
            if invoice_line.discount:
                cantidad_lineas += 1
                aux_por_desc += invoice_line.discount
                monto_descuento_total += invoice_line.price_subtotal * invoice_line.discount

            # Cálculo de tipo de productos en factura 1/2
            if invoice_line.product_id.type_item_edi == 1:
                has_product = True
            elif invoice_line.product_id.type_item_edi == 2:
                has_product = True
            elif invoice_line.product_id.type_item_edi == 3:
                has_product = True
                has_service = True
            totalGravada += round(invoice_line.price_total)

        # Cálculo de descuento total por cada línea de producto 1/2
        # porcentaje_descuento = round(aux_por_desc / cantidad_lineas, 2)

        # Cálculo de tipo de productos en factura 2/2
        if has_product:
            tipo_item = 1
        elif has_service:
            tipo_item = 2
        elif has_product and has_service:
            tipo_item = 3

        payload = json.dumps({

            # 'nit': self.partner_id.document_nit,
            # 'activo': "True",
            # 'passwordPri': self.company_id.private_pass_mh,
            # "content-Type": "application/JSON",
            "nit": self.company_id.document_nit,
            "activo": "False",
            "passwordPri": self.company_id.private_pass_mh,
            "dteJson": {
                "identificacion": {
                    "version": self.journal_id.version,
                    "ambiente": self.company_id.modo_prueba,
                    "tipoDte": self.journal_id.document_type_sv,
                    "numeroControl": self.name,
                    "codigoGeneracion": self.uuid_generation_code,
                    "tipoModelo": int(self.modelo_facturacion),
                    "tipoOperacion": int(self.tipo_transmision),
                    "tipoContingencia": None if self.tipo_contingencia == "None" else self.tipo_contingencia,
                    "motivoContin": None if not self.motivo_contig else self.motivo_contig,
                    "fecEmi": self.fecha_emision.strftime('%Y-%m-%d'),
                    "horEmi": hora_actual,
                    "tipoMoneda": self.currency_id.name
                },
                "emisor": {
                    "nit": self.company_id.document_nit,
                    "nrc": self.company_id.document_vat,
                    "nombre": self.company_id.name,
                    "codActividad": self.company_id.document_giro_company.code,
                    "descActividad": self.company_id.document_giro_company.name,
                    "nombreComercial": self.company_id.name,
                    "tipoEstablecimiento": self.tipo_establecimiento,
                    "direccion": {
                        "departamento": self.company_id.state_id.code,
                        "municipio": self.company_id.munic_id.code,
                        "complemento": self.company_id.street
                    },
                    "telefono": self.company_id.phone,
                    "codigoMH": None if not self.company_id.cod_estable_mh else self.company_id.cod_estable_mh,
                    "codigo": None if not self.company_id.cod_estable else self.company_id.cod_estable,
                    "puntoVentaMH": None if not self.company_id.cod_pv_mh else self.company_id.cod_pv_mh,
                    "puntoVenta": None if not self.company_id.cod_pv else self.company_id.cod_pv,
                    "correo": self.company_id.email
                },
                "receptor": {
                    "tipoDocumento": None if not self.tipo_identificacion_receptor else self.tipo_identificacion_receptor,
                    "numDocumento": num_documento_options.get(self.tipo_identificacion_receptor, None),
                    "nrc": self.partner_id.document_vat_compute,
                    "nombre": self.partner_id.name,
                    "codActividad": self.partner_id.document_giro_res.code,
                    "descActividad": None if not self.partner_id.document_giro_res else self.partner_id.document_giro_res.name,
                    "nombreComercial": self.partner_id.name,
                    "direccion": {
                        "departamento": self.partner_id.state_id.code,
                        "municipio": self.partner_id.munic_id.code,
                        "complemento": self.partner_id.street
                    },
                    "telefono": None if not self.partner_id.phone else self.partner_id.phone,
                    "correo": None if not self.partner_id.email else self.partner_id.email
                },
                "cuerpoDocumento": items,
                "resumen": {
                    "totalSujetoRetencion": (self.original_invoice_id.amount_untaxed),
                    "totalIVAretenido": -(self.original_invoice_id.retencion_fc),
                    "totalIVAretenidoLetras": self.amount_to_text_ret
                },
                "extension": None,
                "apendice": None
            }
        })
        print(payload)
        self.enviar_solicitud(url,payload)

    # Nota de credito
    def firmar_documentos_ncre(self):
        if not self.payment_reference:
            raise ValidationError("El campo referencia de pago es obligatoria")
        else:
            tz = pytz.timezone('America/El_Salvador')
            hora_actual = datetime.now(tz).strftime('%H:%M:%S')
            url = 'http://167.99.8.116:8113/firmardocumento/?content-Type=application/JSON&nit=06142809011497'

            num_documento_options = {
                '36': self.partner_id.document_nit_compute,
                '13': self.partner_id.document_dui_compute,
                '03': self.partner_id.document_pasaporte,
                '02': self.partner_id.document_carnet_residente,
                '37': self.tipo_identificacion_receptor_otro,
            }
            items = []
            for i, invoice_line in enumerate(self.invoice_line_ids):
                taxes = []
                for tax in invoice_line.tax_ids:
                    if tax.amount != -1 and tax.amount != 1:  # Agrega esta condición para omitir los impuestos con valor -1
                        tax_dict = tax.code_dte_sv
                        taxes.append(tax_dict)

                taxes_resume = []
                for tax in invoice_line.tax_ids:
                    if tax.amount != -1 and tax.amount != 1:  # Agrega esta condición para omitir los impuestos con valor -1
                        tax_dict_res = {
                            "codigo": tax.code_dte_sv,
                            "descripcion": tax.name,
                            "valor": round((tax.amount / 100) * self.amount_untaxed, 2)
                            # Agrega aquí los demás campos que necesites
                        }
                        taxes_resume.append(tax_dict_res)

                item = {
                    "numItem": i + 1,  # Agregar 1 al número de secuencia para empezar desde 1 en lugar de 0
                    "tipoItem": int(invoice_line.product_id.type_item_edi),
                    "numeroDocumento": self.original_invoice_id.uuid_generation_code,
                    "codigo": None if not invoice_line.product_id.default_code else invoice_line.product_id.default_code,
                    "codTributo": None if not invoice_line.product_id.tributo_iva else invoice_line.product_id.tributo_iva,
                    "descripcion": invoice_line.name,
                    "cantidad": invoice_line.quantity,
                    "uniMedida": int(invoice_line.product_id.cat_unidad_medida.clave),
                    "precioUni": float(invoice_line.price_unit),
                    "montoDescu": round((invoice_line.price_unit) * (invoice_line.quantity) * (invoice_line.discount/100),4),
                    "ventaNoSuj": round(invoice_line.price_subtotal, 5) if invoice_line.move_type_ids == 'nosujetas' else 0,
                    "ventaExenta": round(invoice_line.price_subtotal, 5) if invoice_line.move_type_ids == 'exentas' else 0,
                    "ventaGravada": round(invoice_line.price_subtotal,
                                          5) if invoice_line.move_type_ids == 'gravadas' else 0,
                    "tributos": None if not taxes else taxes,
                }
                items.append(item)

            payload = json.dumps({
                'nit': self.company_id.document_nit,
                'activo': "True",
                'passwordPri': self.company_id.private_pass_mh,
                'dteJson':
                    {
                        "identificacion": {
                            "version": self.journal_id.version,
                            "ambiente": self.company_id.modo_prueba,
                            "tipoDte": self.journal_id.document_type_sv,
                            "numeroControl": self.name,
                            "codigoGeneracion": self.uuid_generation_code,
                            "tipoModelo": int(self.modelo_facturacion),
                            "tipoOperacion": int(self.tipo_transmision),
                            "fecEmi": self.fecha_emision_nd_nc.strftime('%Y-%m-%d'),
                            "horEmi": hora_actual,
                            "tipoMoneda": self.currency_id.name,
                            "tipoContingencia": None if self.tipo_contingencia == "None" else self.tipo_contingencia,
                            "motivoContin": None if not self.motivo_contig else self.motivo_contig
                        },
                        "documentoRelacionado": [
                            {
                                "tipoDocumento": self.original_invoice_id.number_journal,
                                "tipoGeneracion": int(self.original_invoice_id.tipo_generacion_documento),
                                "numeroDocumento": self.original_invoice_id.uuid_generation_code,
                                "fechaEmision": self.original_invoice_id.fecha_emision.strftime('%Y-%m-%d'),
                            }
                        ],
                        "emisor": {
                            "nit": self.company_id.document_nit,
                            "nrc": self.company_id.document_vat,
                            "nombre": self.company_id.name,
                            "codActividad": self.company_id.document_giro_company.code,
                            "descActividad": self.company_id.document_giro_company.name,
                            "nombreComercial": self.company_id.name,
                            "tipoEstablecimiento": self.tipo_establecimiento,
                            "direccion": {
                                "departamento": self.company_id.state_id.code,
                                "municipio": self.company_id.munic_id.code,
                                "complemento": self.company_id.street
                            },
                            "telefono": self.company_id.phone,
                            "correo": self.company_id.email
                        },
                        "receptor": {
                            "nit": self.partner_id.document_nit_compute,
                            "nrc": self.partner_id.document_vat_compute,
                            "nombre": self.partner_id.name,
                            "codActividad": None if not self.partner_id.document_giro_res else self.partner_id.document_giro_res.code,
                            "descActividad": None if not self.partner_id.document_giro_res else self.partner_id.document_giro_res.name,
                            "nombreComercial": self.partner_id.name,
                            "direccion": None if not self.partner_id.munic_id else {
                                "departamento": self.partner_id.state_id.code,
                                "municipio": self.partner_id.munic_id.code,
                                "complemento": self.partner_id.street
                            },
                            "telefono": None if not self.partner_id.phone else self.partner_id.phone,
                            "correo": self.partner_id.email
                        },
                        "ventaTercero": None if not self.venta_cuenta_terceros else {
                            "nit": self.venta_cuenta_terceros.document_nit_compute,
                            "nombre": self.venta_cuenta_terceros.name
                        },
                        "cuerpoDocumento": items,
                        "resumen": {
                            "totalNoSuj": round(sum(
                                line.price_subtotal for line in self.invoice_line_ids if line.move_type_ids == 'nosujetas'),2),
                            "totalExenta": round(sum(
                                line.price_subtotal for line in self.invoice_line_ids if line.move_type_ids == 'exentas'),2),
                            "totalGravada": round(sum(line.price_subtotal for line in self.invoice_line_ids if
                                                      line.move_type_ids == 'gravadas'), 2),
                            "subTotalVentas": self.amount_untaxed,
                            "descuNoSuj": 0,
                            "descuExenta": 0,
                            "descuGravada": 0,
                            "totalDescu": round(sum((line.price_unit * line.quantity) * (line.discount/100) for line in self.invoice_line_ids),2),
                            "tributos": taxes_resume,
                            "subTotal": self.amount_untaxed,
                            "ivaPerci1": round(self.percepcion_fc,2),
                            "ivaRete1": round(-self.retencion_fc, 2),
                            "reteRenta": round(self.rete_renta, 2),
                            "montoTotalOperacion": self.amount_total,
                            "totalLetras": self.amount_to_text,
                            "condicionOperacion": 1 if not self.invoice_payment_term_id else int(
                                self.invoice_payment_term_id.condicion_operacion),
                        },
                        "extension": None,
                        "apendice": [
                            {
                                "campo": "refInterno",
                                "etiqueta": "referenciaInterna",
                                "valor": None if not self.payment_reference else self.payment_reference
                            }
                        ]
                    }
            })
            self.enviar_solicitud(url,payload)

      
    # Nota de debito
    def firmar_documentos_ndeb(self):
        tz = pytz.timezone('America/El_Salvador')
        hora_actual = datetime.now(tz).strftime('%H:%M:%S')
        url = 'http://167.99.8.116:8113/firmardocumento/?content-Type=application/JSON&nit=06142809011497'

        num_documento_options = {
            '36': self.partner_id.document_nit_compute,
            '13': self.partner_id.document_dui_compute,
            '03': self.partner_id.document_pasaporte,
            '02': self.partner_id.document_carnet_residente,
            '37': self.tipo_identificacion_receptor_otro,
        }
        items = []
        for i, invoice_line in enumerate(self.invoice_line_ids):
            taxes = []
            for tax in invoice_line.tax_ids:
                if tax.amount != -1 and tax.amount != 1:  # Agrega esta condición para omitir los impuestos con valor -1
                    tax_dict = tax.code_dte_sv
                    taxes.append(tax_dict)

            taxes_resume = []
            for tax in invoice_line.tax_ids:
                if tax.amount != -1 and tax.amount != 1:  # Agrega esta condición para omitir los impuestos con valor -1
                    tax_dict_res = {
                        "codigo": tax.code_dte_sv,
                        "descripcion": tax.name,
                        "valor": round((tax.amount / 100) * self.amount_untaxed, 2)
                        # Agrega aquí los demás campos que necesites
                    }
                    taxes_resume.append(tax_dict_res)

            item = {
                "numItem": i + 1,  # Agregar 1 al número de secuencia para empezar desde 1 en lugar de 0
                "tipoItem": int(invoice_line.product_id.type_item_edi),
                "numeroDocumento": self.original_invoice_id.uuid_generation_code,
                "codigo": None if not invoice_line.product_id.default_code else invoice_line.product_id.default_code,
                "codTributo": None if not invoice_line.product_id.tributo_iva else invoice_line.product_id.tributo_iva,
                "descripcion": invoice_line.name,
                "cantidad": invoice_line.quantity,
                "uniMedida": int(invoice_line.product_id.cat_unidad_medida.clave),
                "precioUni": float(invoice_line.price_unit),
                "montoDescu": round((invoice_line.price_unit) * (invoice_line.quantity) * (invoice_line.discount/100),4),
                "ventaNoSuj": round(invoice_line.price_subtotal, 5) if invoice_line.move_type_ids == 'nosujetas' else 0,
                "ventaExenta": round(invoice_line.price_subtotal, 5) if invoice_line.move_type_ids == 'exentas' else 0,
                "ventaGravada": round(invoice_line.price_subtotal,
                                      5) if invoice_line.move_type_ids == 'gravadas' else 0,
                "tributos": None if not taxes else taxes,
            }
            items.append(item)

        payload = json.dumps({
            'nit': self.company_id.document_nit,
            'activo': "True",
            'passwordPri': self.company_id.private_pass_mh,
            'dteJson':
                {
                    "identificacion": {
                        "version": self.journal_id.version,
                        "ambiente": self.company_id.modo_prueba,
                        "tipoDte": self.journal_id.document_type_sv,
                        "numeroControl": self.name,
                        "codigoGeneracion": self.uuid_generation_code,
                        "tipoModelo": int(self.modelo_facturacion),
                        "tipoOperacion": int(self.tipo_transmision),
                        "fecEmi": self.fecha_emision_nd_nc.strftime('%Y-%m-%d'),
                        "horEmi": hora_actual,
                        "tipoMoneda": self.currency_id.name,
                        "tipoContingencia": None if self.tipo_contingencia == "None" else self.tipo_contingencia,
                        "motivoContin": None if not self.motivo_contig else self.motivo_contig
                    },
                    "documentoRelacionado": [
                        {
                            "tipoDocumento": self.original_invoice_id.number_journal,
                            "tipoGeneracion": int(self.original_invoice_id.tipo_generacion_documento),
                            "numeroDocumento": self.original_invoice_id.uuid_generation_code,
                            "fechaEmision": self.original_invoice_id.fecha_emision.strftime('%Y-%m-%d'),
                        }
                    ],
                    "emisor": {
                        "nit": self.company_id.document_nit,
                        "nrc": self.company_id.document_vat,
                        "nombre": self.company_id.name,
                        "codActividad": self.company_id.document_giro_company.code,
                        "descActividad": self.company_id.document_giro_company.name,
                        "nombreComercial": self.company_id.name,
                        "tipoEstablecimiento": self.tipo_establecimiento,
                        "direccion": {
                            "departamento": self.company_id.state_id.code,
                            "municipio": self.company_id.munic_id.code,
                            "complemento": self.company_id.street
                        },
                        "telefono": self.company_id.phone,
                        "correo": self.company_id.email
                    },
                    "receptor": {
                        "nit": self.partner_id.document_nit_compute,
                        "nrc": self.partner_id.document_vat_compute,
                        "nombre": self.partner_id.name,
                        "codActividad": None if not self.partner_id.document_giro_res else self.partner_id.document_giro_res.code,
                        "descActividad": None if not self.partner_id.document_giro_res else self.partner_id.document_giro_res.name,
                        "nombreComercial": self.partner_id.name,
                        "direccion": None if not self.partner_id.munic_id else {
                            "departamento": self.partner_id.state_id.code,
                            "municipio": self.partner_id.munic_id.code,
                            "complemento": self.partner_id.street
                        },
                        "telefono": None if not self.partner_id.phone else self.partner_id.phone,
                        "correo": self.partner_id.email
                    },
                    "ventaTercero": None if not self.venta_cuenta_terceros else {
                        "nit": self.venta_cuenta_terceros.document_nit_compute,
                        "nombre": self.venta_cuenta_terceros.name
                    },
                    "cuerpoDocumento": items,
                    "resumen": {
                        "totalNoSuj": sum(
                            line.price_subtotal for line in self.invoice_line_ids if line.move_type_ids == 'nosujetas'),
                        "totalExenta": sum(
                            line.price_subtotal for line in self.invoice_line_ids if line.move_type_ids == 'exentas'),
                        "totalGravada": round(sum(line.price_subtotal for line in self.invoice_line_ids if
                                                  line.move_type_ids == 'gravadas'), 2),
                        "subTotalVentas": self.amount_untaxed,
                        "descuNoSuj": 0,
                        "descuExenta": 0,
                        "descuGravada": 0,
                        "totalDescu": round(sum((line.price_unit * line.quantity) * (line.discount/100) for line in self.invoice_line_ids),2),
                        "tributos": None if not taxes_resume else taxes_resume,
                        "subTotal": self.amount_untaxed,
                        "ivaPerci1": round(self.percepcion_fc,2),
                        "ivaRete1": round(-self.retencion_fc, 2),
                        "reteRenta": round(self.rete_renta,2),
                        "montoTotalOperacion": round(self.amount_total,
                                                 2) if self.retencion_fc != 0 or self.percepcion_fc != 0 else self.amount_total,
                        "totalLetras": self.amount_to_text,
                        "condicionOperacion": 1 if not self.invoice_payment_term_id else int(
                            self.invoice_payment_term_id.condicion_operacion),
                        "numPagoElectronico": None if not self.num_pago_electronico else self.num_pago_electronico
                    },
                    "extension": None,
                    "apendice": [
                        {
                            "campo": "refInterno",
                            "etiqueta": "referenciaInterna",
                            "valor": None if not self.payment_reference else self.payment_reference
                        }
                    ]
                }
        })
        print(payload)
        self.enviar_solicitud(url,payload)

    
             
    # Nota de remision
    def firmar_documentos_nrem(self):
        if not self.titulo_a_que_se_remiten_bienes:
            raise ValidationError(
                "Seleccione el título a que se remiten los bienes.")
        else:
            tz = pytz.timezone('America/El_Salvador')
            hora_actual = datetime.now(tz).strftime('%H:%M:%S')
            url = 'http://167.99.8.116:8113/firmardocumento/?content-Type=application/JSON&nit=06142809011497ccc'

            num_documento_options = {
                '36': self.partner_id.document_nit_compute,
                '13': self.partner_id.document_dui_compute,
                '03': self.partner_id.document_pasaporte,
                '02': self.partner_id.document_carnet_residente,
                '37': self.tipo_identificacion_receptor_otro,
            }
            items = []
            for i, invoice_line in enumerate(self.invoice_line_ids):
                taxes = []
                for tax in invoice_line.tax_ids:
                    tax_dict = tax.code_dte_sv

                    taxes.append(tax_dict)

                taxes_resume = []
                for tax in invoice_line.tax_ids:
                    tax_dict_res = {
                        "codigo": tax.code_dte_sv,
                        "descripcion": tax.name,
                        "valor": self.amount_tax,
                        # Agrega aquí los demás campos que necesites
                    }
                    taxes_resume.append(tax_dict_res)

                item = {
                    "numItem": i + 1,  # Agregar 1 al número de secuencia para empezar desde 1 en lugar de 0
                    "tipoItem": int(invoice_line.product_id.type_item_edi),
                    "numeroDocumento": None,
                    "codigo": None if not invoice_line.product_id.default_code else invoice_line.product_id.default_code,
                    "codTributo": None if not invoice_line.product_id.tributo_iva else invoice_line.product_id.tributo_iva,
                    "descripcion": invoice_line.name,
                    "cantidad": invoice_line.quantity,
                    "uniMedida": int(invoice_line.product_id.cat_unidad_medida.clave),
                    "precioUni": float(invoice_line.price_unit),
                    "montoDescu": round(
                        (invoice_line.price_unit) * (invoice_line.quantity) * (invoice_line.discount / 100), 4),
                    "ventaNoSuj": 0,
                    "ventaExenta": 0,
                    "ventaGravada": float(invoice_line.price_subtotal),
                    "tributos": taxes,
                }
                items.append(item)

            payload = json.dumps({
                'nit': self.company_id.document_nit,
                'activo': "True",
                'passwordPri': self.company_id.private_pass_mh,
                'dteJson':
                    {
                        "identificacion": {
                            "version": self.journal_id.version,
                            "ambiente": self.company_id.modo_prueba,
                            "tipoDte": self.journal_id.document_type_sv,
                            "numeroControl": self.name,
                            "codigoGeneracion": self.uuid_generation_code,
                            "tipoOperacion": int(self.tipo_transmision),
                            "tipoModelo": int(self.modelo_facturacion),
                            "fecEmi": self.fecha_emision.strftime('%Y-%m-%d'),
                            "horEmi": hora_actual,
                            "tipoMoneda": self.currency_id.name,
                            "tipoContingencia": None if self.tipo_contingencia == "None" else int(
                                self.tipo_contingencia),
                            "motivoContin": None if not self.motivo_contig else self.motivo_contig
                        },
                        "documentoRelacionado": None,
                        "emisor": {
                            "nit": self.company_id.document_nit,
                            "nrc": self.company_id.document_vat,
                            "nombre": self.company_id.name,
                            "codActividad": self.company_id.document_giro_company.code,
                            "descActividad": self.company_id.document_giro_company.name,
                            "nombreComercial": self.company_id.name,
                            "tipoEstablecimiento": self.tipo_establecimiento,
                            "direccion": {
                                "departamento": self.company_id.state_id.code,
                                "municipio": self.company_id.munic_id.code,
                                "complemento": self.company_id.street
                            },
                            "telefono": self.company_id.phone,
                            "correo": self.company_id.email,
                            "codEstableMH": None if not self.company_id.cod_estable_mh else self.company_id.cod_estable_mh,
                            "codEstable": None if not self.company_id.cod_estable else self.company_id.cod_estable,
                            "codPuntoVentaMH": None if not self.company_id.cod_pv_mh else self.company_id.cod_pv_mh,
                            "codPuntoVenta": None if not self.company_id.cod_pv else self.company_id.cod_pv
                        },
                        "receptor": {
                            "tipoDocumento": None if not self.tipo_identificacion_receptor else self.tipo_identificacion_receptor,
                            "numDocumento": num_documento_options.get(self.tipo_identificacion_receptor, None),
                            "nrc": None if not self.partner_id.vat else self.partner_id.document_vat_compute,
                            "nombre": self.partner_id.name,
                            "codActividad": None if not self.partner_id.document_giro_res else self.partner_id.document_giro_res.code,
                            "descActividad": None if not self.partner_id.document_giro_res else self.partner_id.document_giro_res.name,
                            "nombreComercial": self.company_id.name,
                            "direccion": None if not self.partner_id.munic_id else {
                                "departamento": self.partner_id.state_id.code,
                                "municipio": self.partner_id.munic_id.code,
                                "complemento": self.partner_id.street
                            },
                            "telefono": None if not self.partner_id.phone else self.partner_id.phone,
                            "correo": None if not self.partner_id.email else self.partner_id.email,
                            "bienTitulo": self.titulo_a_que_se_remiten_bienes
                        },
                        "ventaTercero": None if not self.venta_cuenta_terceros else {
                            "nit": self.venta_cuenta_terceros.document_nit_compute,
                            "nombre": self.venta_cuenta_terceros.name
                        },
                        "cuerpoDocumento": items,
                        "resumen": {
                            "totalNoSuj": 0,
                            "totalExenta": 0,
                            "totalGravada": self.amount_untaxed,
                            "subTotalVentas": self.amount_untaxed,
                            "subTotal": self.amount_untaxed,
                            "tributos": taxes_resume,
                            "descuNoSuj": 0,
                            "descuExenta": 0,
                            "descuGravada": 0,
                            "porcentajeDescuento": 0,
                            "totalDescu": round(sum(
                                (line.price_unit * line.quantity) * (line.discount / 100) for line in
                                self.invoice_line_ids), 2),
                            "montoTotalOperacion": self.amount_total,
                            "totalLetras": self.amount_to_text,
                        },
                        "extension": None,
                        "apendice": [
                            {
                                "campo": "refInterno",
                                "etiqueta": "referenciaInterna",
                                "valor": None if not self.payment_reference else self.payment_reference
                            }
                        ]
                    }
            })
            self.enviar_solicitud(url,payload)


     # factura de comoprobante de donacion
    def firmar_documentos_cd(self):    
        #llamar metodo url_hora para obtener la hora  actual y la url
        obtener_url_hr=self.url_hora()
        
        num_documento_options = {
            '36': self.partner_id.document_nit_compute,
            '13': self.partner_id.document_dui_compute,
            '03': self.partner_id.document_pasaporte,
            '02': self.partner_id.document_carnet_residente,
            '37': self.tipo_identificacion_receptor_otro,
        }

        items = []
        # Parte el cuerpo Documento
      
        for i, invoice_line in enumerate(self.invoice_line_ids):
                # validar para que sea solo para tipo de donacion e bien de lo contrario sea cero
          # formula en linea rect ,Depreciación= Costo de Adquisición- Valor Residual / Vida Útil
            if self.tipo_donacion == "2":
                try:
                   depreciacion_anual = (float(invoice_line.price_unit) - float(invoice_line.product_id.valor_residual)) / invoice_line.product_id.anho
                   depreciacion_anual_redondeada = round(depreciacion_anual,2)
                except ZeroDivisionError:
                   mjs = "No se puede dividir entre cero"
                   raise UserError(mjs)
            else:
                depreciacion_anual_redondeada = 0
                    
            #calcular valor residual, al finalizar el contrato, aplica solo para productos tipo bien
            # valor_residual = (precio unitario -(depreciacion anual x cada año))
            

            item = {
                    "numItem": i + 1,  # Agregar 1 al número de secuencia para empezar desde 1 en lugar de 0
                    "tipoDonacion": int(self.tipo_donacion),
                    "cantidad": invoice_line.quantity,
                    "codigo": None if not invoice_line.product_id.default_code else invoice_line.product_id.default_code,
                    "uniMedida": int(invoice_line.product_id.cat_unidad_medida.clave),
                    "descripcion": invoice_line.name,
                    "depreciacion": depreciacion_anual_redondeada,
                    "valorUni": invoice_line.price_unit,
                    "valor": round(invoice_line.price_unit * invoice_line.quantity - depreciacion_anual_redondeada, 2)
                }
            items.append(item)
             
            total_price = sum(item["valor"] for item in items)

        
          # fin   cuerpoDocumento

        #   INicio de resumen 
        price = []

        try:
            for invoice in self.invoice_line_ids:
                if len(self.invoice_line_ids.product_id) >= 2:
                    valor_total = round(total_price, 2)
                elif self.tipo_donacion == "2":
                    valor_total = round(invoice_line.price_unit * invoice.quantity - depreciacion_anual_redondeada, 2)
                else:
                    valor_total = round(self.invoice_line_ids.price_unit * self.invoice_line_ids.quantity, 2)

                prin = {
                    "valorTotal": valor_total,
                    "totalLetras": self.amount_to_text,
                    "pagos": [{
                        "codigo":None if not  self.forma_pago_id.code else  self.forma_pago_id.code,
                        "montoPago": self.amount_total,
                        "referencia": self.payment_reference}]
                }

                price.append(prin)

        except Exception as e:
            print
            raise UserError("Debe seleccionar el tipo de donacion")
        # FIn de resumen 

      
    
        payload = json.dumps({
            'nit': self.company_id.document_nit,
            'activo': True,
            'passwordPri': self.company_id.private_pass_mh,
            'dteJson':
                {
                    "identificacion": {
                        "version": self.journal_id.version,
                        "ambiente": self.company_id.modo_prueba,
                        "tipoDte": self.journal_id.document_type_sv,
                        "numeroControl": self.name,
                        "codigoGeneracion": self.uuid_generation_code,
                        "tipoModelo": int(self.modelo_facturacion),
                        "tipoOperacion": int(self.tipo_transmision),
                        "fecEmi": self.fecha_emision.strftime('%Y-%m-%d'),
                        "horEmi": obtener_url_hr['hora_actual'],
                        "tipoMoneda": self.currency_id.name,

                    },
                    "donatario": {
                        "tipoDocumento": self.tipo_identificacion_receptor,
                        "numDocumento": self.company_id.document_nit,
                        "nrc": self.company_id.vat,
                        "nombre": self.company_id.name,
                        "codActividad": self.company_id.document_giro_company.code,
                        "descActividad": self.company_id.document_giro_company.name,
                        "nombreComercial": self.company_id.name,
                        "tipoEstablecimiento": self.tipo_establecimiento,
                        "direccion": {
                            "departamento": self.company_id.state_id.code,
                            "municipio": self.company_id.munic_id.code,
                            "complemento": self.company_id.street
                        },
                        "telefono": str(self.company_id.phone),
                        "correo": self.company_id.email,
                        "codEstableMH": None if not self.company_id.cod_estable_mh else self.company_id.cod_estable_mh,
                        "codEstable": None if not self.company_id.cod_estable else self.company_id.cod_estable,
                        "codPuntoVentaMH": None if not self.company_id.cod_pv_mh else self.company_id.cod_pv_mh,
                        "codPuntoVenta": None if not self.company_id.cod_pv else self.company_id.cod_pv
                    },
                    "donante": {
                        "tipoDocumento": self.tipo_identificacion_receptor,
                        "numDocumento": num_documento_options.get(self.tipo_identificacion_receptor),
                        "nrc": None if not self.partner_id.vat else self.partner_id.vat,
                        "nombre": self.partner_id.name,
                        "codActividad": None if not self.partner_id.document_giro_res else self.partner_id.document_giro_res.code,
                        "descActividad":None if not self.partner_id.document_giro_res else self.partner_id.document_giro_res.name,
                        "direccion":  {
                            "departamento": self.partner_id.state_id.code if self.partner_id.state_id and self.partner_id.state_id.code else None,
                            "municipio": self.partner_id.munic_id.code if self.partner_id.munic_id and self.partner_id.munic_id.code else None,
                            "complemento": self.partner_id.street if self.partner_id.street else None
                            },
                        "telefono": str(self.partner_id.phone),
                        "correo": self.partner_id.email,
                        "codDomiciliado": int(self.partner_id.domicilio_fiscal),
                        "codPais": self.partner_id.codigo_pais.code
                    },
                    "otrosDocumentos": [{
                        "codDocAsociado": int(self.otros_documentos_asociados),
                        "descDocumento": self.cod_asociado,
                        "detalleDocumento": self.detalle_documento
                    }],

                    "cuerpoDocumento": items,
                    "resumen": prin,
                    "apendice": None if not self.partner_id.email else [{
                        "campo": self.partner_id.email,
                        "etiqueta": self.detalle_documento,
                        "valor": self.partner_id.name
                    }] 
                }
        })
        url=obtener_url_hr['url']
        self.enviar_solicitud(url,payload)


    # Comprobante de liquidacion
    def firmar_documentos_cl(self):
        tz = pytz.timezone('America/El_Salvador')
        hora_actual = datetime.now(tz).strftime('%H:%M:%S')
        url = 'http://167.99.8.116:8113/firmardocumento/?content-Type=application/JSON&nit=06142809011497'

        num_documento_options = {
            '36': self.partner_id.document_nit_compute,
            '13': self.partner_id.document_dui_compute,
            '03': self.partner_id.document_pasaporte,
            '02': self.partner_id.document_carnet_residente, #databases = [
           # {'name': 'odoo-cero', 'username': 'admin', 'password': 'c830ed936be3a33a1522cb780bee012f35e7efb3'},
           # {'name': 'odoo-uno', 'username': 'admin', 'password': '90684b18fcee451fe471ccc82824f8e7114b6d65'},
           # 
            '37': self.tipo_identificacion_receptor_otro,
        }
        items = []
        for i, invoice_line in enumerate(self.invoice_line_ids):
            taxes = []
            for tax in invoice_line.tax_ids:
                tax_dict = tax.code_dte_sv

                taxes.append(tax_dict)

            taxes_resume = []
            for tax in invoice_line.tax_ids:
                tax_dict_res = {
                    "codigo": tax.code_dte_sv,
                    "descripcion": tax.name,
                    "valor": self.amount_tax,
                    # Agrega aquí los demás campos que necesites
                }
                taxes_resume.append(tax_dict_res)

            item = {
                "numItem": i + 1,  # Agregar 1 al número de secuencia para empezar desde 1 en lugar de 0
                "tipoItem": int(invoice_line.product_id.type_item_edi),
                "numeroDocumento": None,
                "tipoGeneracion": int(self.tipo_generacion_documento),
                "codigo": None if not invoice_line.product_id.default_code else invoice_line.product_id.default_code,
                "codTributo": None if not invoice_line.product_id.tributo_iva else invoice_line.product_id.tributo_iva,
                "descripcion": invoice_line.name,
                "cantidad": invoice_line.quantity,
                "uniMedida": int(invoice_line.product_id.cat_unidad_medida.clave),
                "precioUni": float(invoice_line.price_unit),
                "montoDescu": round((invoice_line.price_unit) * (invoice_line.quantity) * (invoice_line.discount/100),4),
                "ventaNoSuj": 0,
                "ventaExenta": 0,
                "ventaGravada": float(invoice_line.price_subtotal),
                "tributos": taxes,
            }
            items.append(item)

        payload = json.dumps({
            'nit': self.company_id.document_nit,
            'activo': "True",
            'passwordPri': self.company_id.private_pass_mh,
            'dteJson':
                {
                    "identificacion": {
                        "version": self.journal_id.version,
                        "ambiente": self.company_id.modo_prueba,
                        "tipoDte": self.journal_id.document_type_sv,
                        "numeroControl": self.name,
                        "codigoGeneracion": self.uuid_generation_code,
                        "tipoOperacion": int(self.tipo_transmision),
                        "tipoModelo": int(self.modelo_facturacion),
                        "fecEmi": self.fecha_emision.strftime('%Y-%m-%d'),
                        "horEmi": hora_actual,
                        "tipoMoneda": self.currency_id.name,
                    },
                    "emisor": {
                        "nit": self.company_id.document_nit,
                        "nrc": self.company_id.document_vat,
                        "nombre": self.company_id.name,
                        "codActividad": self.company_id.document_giro_company.code,
                        "descActividad": self.company_id.document_giro_company.name,
                        "nombreComercial": self.company_id.name,
                        "tipoEstablecimiento": self.tipo_establecimiento,
                        "direccion": {
                            "departamento": self.company_id.state_id.code,
                            "municipio": self.company_id.munic_id.code,
                            "complemento": self.company_id.street
                        },
                        "telefono": self.company_id.phone,
                        "correo": self.company_id.email,
                        "codEstableMH": None if not self.company_id.cod_estable_mh else self.company_id.cod_estable_mh,
                        "codEstable": None if not self.company_id.cod_estable else self.company_id.cod_estable,
                        "codPuntoVentaMH": None if not self.company_id.cod_pv_mh else self.company_id.cod_pv_mh,
                        "codPuntoVenta": None if not self.company_id.cod_pv else self.company_id.cod_pv
                    },
                    "receptor": {
                        "nit": self.partner_id.document_nit_compute,
                        "nrc": self.partner_id.document_vat_compute,
                        "nombre": self.partner_id.name,
                        "codActividad": None if not self.partner_id.document_giro_res else self.partner_id.document_giro_res.code,
                        "descActividad": None if not self.partner_id.document_giro_res else self.partner_id.document_giro_res.name,
                        "nombreComercial": self.partner_id.name,
                        "direccion": None if not self.partner_id.munic_id else {
                            "departamento": self.partner_id.state_id.code,
                            "municipio": self.partner_id.munic_id.code,
                            "complemento": self.partner_id.street
                        },
                        "telefono": None if not self.partner_id.phone else self.partner_id.phone,
                        "correo": self.partner_id.email
                    },
                    "cuerpoDocumento": items,
                    "resumen": {
                        "totalNoSuj": 0,
                        "totalExenta": 0,
                        "totalGravada": self.amount_untaxed,
                        "subTotalVentas": self.amount_untaxed,
                        "totalExportacion": self.amount_untaxed,
                        "tributos": taxes_resume,
                        "ivaPerci": 0,
                        "montoTotalOperacion": self.amount_total,
                        "totalLetras": self.amount_to_text,
                        "condicionOperacion": 1 if not self.invoice_payment_term_id else int(
                            self.invoice_payment_term_id.condicion_operacion),
                    },
                    "extension": None,
                    "apendice": [
                        {
                            "campo": "refInterno",
                            "etiqueta": "referenciaInterna",
                            "valor": None if not self.payment_reference else self.payment_reference
                        }
                    ]
                }
        })
        self.enviar_solicitud(url,payload)

    # sujeto excluido
    def firmar_documentos_se(self):
        tz = pytz.timezone('America/El_Salvador')
        hora_actual = datetime.now(tz).strftime('%H:%M:%S')
        url = 'http://167.99.8.116:8113/firmardocumento/?content-Type=application/JSON&nit=06142809011497'

        num_documento_options = {
            '36': self.partner_id.document_nit_compute,
            '13': self.partner_id.document_dui_compute,
            '03': self.partner_id.document_pasaporte,
            '02': self.partner_id.document_carnet_residente,
            '37': self.tipo_identificacion_receptor_otro,
        }
        items = []
        for i, invoice_line in enumerate(self.invoice_line_ids):
            taxn = []
            for tax in invoice_line.tax_ids:
                tax_dict = tax.code_dte_sv

                taxn.append(tax_dict)

            item = {
                "numItem": i + 1,  # Agregar 1 al número de secuencia para empezar desde 1 en lugar de 0
                "tipoItem": int(invoice_line.product_id.type_item_edi),
                "codigo": None if not invoice_line.product_id.default_code else invoice_line.product_id.default_code,
                "descripcion": invoice_line.name,
                "cantidad": invoice_line.quantity,
                "uniMedida": int(invoice_line.product_id.cat_unidad_medida.clave),
                "precioUni": round(float(invoice_line.price_unit),4),
                "montoDescu": round((invoice_line.price_unit) * (invoice_line.quantity) * (invoice_line.discount/100),4),
                "compra": round(float(invoice_line.price_unit * invoice_line.quantity),4)

            }
            items.append(item)

        payload = json.dumps({
            'nit': self.company_id.document_nit,
            'activo': "True",
            'passwordPri': self.company_id.private_pass_mh,
            'dteJson':
                {
                    "identificacion": {
                        "version": self.journal_id.version,
                        "ambiente": self.company_id.modo_prueba,
                        "tipoDte": self.journal_id.document_type_sv,
                        "numeroControl": self.name,
                        "codigoGeneracion": self.uuid_generation_code,
                        "tipoOperacion": int(self.tipo_transmision),
                        "tipoModelo": int(self.modelo_facturacion),
                        "fecEmi": self.fecha_emision.strftime('%Y-%m-%d'),
                        "horEmi": hora_actual,
                        "tipoMoneda": self.currency_id.name,
                        "tipoContingencia": None if self.tipo_contingencia is None else int(
                            self.tipo_contingencia) if self.tipo_contingencia.isdigit() else None,
                        "motivoContin": None if not self.motivo_contig else self.motivo_contig,
                    },
                    "emisor": {
                        "nit": self.company_id.document_nit,
                        "nrc": None if not self.company_id.document_vat else self.company_id.document_vat,
                        "nombre": self.company_id.name,
                        "codActividad": self.company_id.document_giro_company.code,
                        "descActividad": self.company_id.document_giro_company.name,
                        "direccion": {
                            "departamento": self.company_id.state_id.code,
                            "municipio": self.company_id.munic_id.code,
                            "complemento": self.company_id.street
                        },
                        "telefono": self.company_id.phone,
                        "correo": self.company_id.email,
                        "codEstableMH": None if not self.company_id.cod_estable_mh else self.company_id.cod_estable_mh,
                        "codEstable": None if not self.company_id.cod_estable else self.company_id.cod_estable,
                        "codPuntoVentaMH": None if not self.company_id.cod_pv_mh else self.company_id.cod_pv_mh,
                        "codPuntoVenta": None if not self.company_id.cod_pv else self.company_id.cod_pv
                    },
                    "sujetoExcluido": {
                        "tipoDocumento": self.tipo_identificacion_receptor,
                        "numDocumento": num_documento_options.get(self.tipo_identificacion_receptor),
                        "nombre": self.partner_id.name,
                        "codActividad": None if not self.partner_id.document_giro_res else self.partner_id.document_giro_res.code,
                        "descActividad": None if not self.partner_id.document_giro_res else self.partner_id.document_giro_res.name,
                        "direccion": None if not self.partner_id.munic_id else {
                            "departamento": self.partner_id.state_id.code,
                            "municipio": self.partner_id.munic_id.code,
                            "complemento": self.partner_id.street
                        },
                        "telefono": None if not self.partner_id.phone else self.partner_id.phone,
                        "correo": None if not self.partner_id.email else self.partner_id.email
                    },
                    "cuerpoDocumento": items,
                    "resumen": {
                        "totalCompra": round(self.amount_untaxed, 2),
                        "descu": 0,
                        "totalDescu": round(sum((line.price_unit * line.quantity) * (line.discount/100) for line in self.invoice_line_ids),2),
                        "subTotal": self.amount_untaxed,
                        "ivaRete1": round(-self.retencion_fc, 2),
                        # round(self.invoice_line_ids.price_unit* 0.15, 2),
                        "reteRenta": round(self.rete_renta,2),#quitar impuestos
                        "totalPagar": self.amount_total,
                        "totalLetras": self.amount_to_text,
                        "condicionOperacion": 1 if not self.invoice_payment_term_id else int(
                            self.invoice_payment_term_id.condicion_operacion),

                        "pagos": None if not self.forma_pago_id.code else [{
                            "codigo": self.forma_pago_id.code,
                            "montoPago": self.amount_total,
                            "referencia": self.payment_reference,
                            "plazo": None,
                            "periodo": None
                        }],
                        "observaciones": None if not self.observaciones else self.observaciones,

                    },
                    "apendice": None if not [
                        {
                            "campo": "refInterno",
                            "etiqueta": "referenciaInterna",
                            "valor": None if not self.payment_reference else self.payment_reference
                        }
                    ] else [
                        {
                            "campo": "refInterno",
                            "etiqueta": "referenciaInterna",
                            "valor": None if not self.payment_reference else self.payment_reference
                        }
                    ]
                }
        })
        print(payload)
        self.enviar_solicitud(url,payload)

    def limpiar_nc(self):
        values_delete = {
            'estado_firmado': '',
            'documento_firmado': '',
            'estado_dte': 'no_facturado',
            'confirmacion': 'Sello no generado',
            'qr_link': 'QR No Generado',
            'json_total': '',
            'uuid_generation_code': '',
            'counter_firmas': 0
        }
        self.write(values_delete)
        new_uuid = str(uuid.uuid4()).upper()
        self.write({'uuid_generation_code': new_uuid})

    def generate_codigo_uuid(self):
        new_uuid_update = str(uuid.uuid4()).upper()
        self.write({'uuid_generation_code': new_uuid_update})

    def action_generate_dte(self):
        payload = json.dumps({
            "ambiente": self.company_id.modo_prueba,
            "idEnvio": self.last_numbers,  # idEnvio es tipo de dato numero entero
            "version": self.journal_id.version,
            "tipoDte": self.journal_id.document_type_sv,
            "documento": self.documento_firmado,
            "codigoGeneracion": self.uuid_generation_code
        })

        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.company_id.token_code
        }
        url = ''
        if self.company_id.modo_prueba == '00':
            url = "https://apitest.dtes.mh.gob.sv/fesv/recepciondte"
        elif self.company_id.modo_prueba == '01':
            url = "https://api.dtes.mh.gob.sv/fesv/recepciondte"
        if not url:
            return
        try:
            response = requests.post(url, headers=headers, data=payload)
            json_response = response.json()
        except Exception as e:
            print(e)
            raise ValidationError('Ocurrió un error al conectarse al servidor de DGII: Verifica las credenciales de '
                                  'la empresa o genera un nuevo token de autenticación')

        if response.status_code == 200:
            if json_response.get('estado') == 'PROCESADO':
                values = {
                    'estado_dte': 'procesado',
                    'confirmacion': json_response['selloRecibido'],
                    'fecha_factura': fields.Datetime.now(),
                }
                self.write(values)
                self.message_post(
                    body="El DTE se ha emitido correctamente.", message_type="notification")
                self.json_mh = json.dumps({"respuestaHacienda": json_response})
                # Convierte los JSON a diccionarios
                dict_mh = json.loads(self.json_mh)
                dict_data = json.loads(self.json_data)

                # Une los diccionarios
                dict_total = {}
                dict_total.update(dict_mh)
                dict_total.update(dict_data)

                # Convierte el diccionario unido a un objeto JSON
                self.json_total = json.dumps(
                    dict_total, ensure_ascii=False).encode('utf-8')
                print(self.json_total)

            else:
                raise ValidationError(json_response.get(
                    'body', {}).get('mensaje', 'Error desconocido'))
        else:
            error_response = json.loads(response.content)
            error_message = 'Error al validar información del DTE: \n' + \
                            f"Estado: {error_response.get('estado')}\n" + \
                            f"Clasificación del mensaje: {error_response.get('clasificaMsg')}\n" + \
                            f"Descripción del mensaje: {error_response.get('descripcionMsg')}\n" + \
                            f"Observaciones del mensaje: {error_response.get('observaciones')}\n"
            raise ValidationError(error_message)

    def generate_json(self):
        for rec in self:
            if not rec.json_total:
                raise ValidationError("No hay un JSON para generar.")
            else:
                filename = f"{rec.partner_id.name}_{rec.name}.json"
                path = os.path.join(os.path.expanduser("~"), "Downloads", filename)

                # Crear el archivo JSON
                with open(path, "w", encoding="utf-8") as f:
                    f.write(rec.json_total)

                rec.message_post(body="El archivo JSON se ha generado correctamente.", message_type="notification")

    def generate_dte_lote(self):
        for record in self:
            if record.estado_dte == 'procesado_lote' or record.estado_dte == 'procesado':
                raise UserError("No pueden elegirse facturas procesadas")

            if record.company_id.modo_prueba == '00':
                url = 'https://apitest.dtes.mh.gob.sv/fesv/recepcionlote/'
            elif record.company_id.modo_prueba == '01':
                url = 'https://api.dtes.mh.gob.sv/fesv/recepcionlote/'
            else:
                url = '#'

            items = []
            if record.documento_firmado:
                items.append(record.documento_firmado)

            json_dict = json.dumps({
                "ambiente": record.company_id.modo_prueba,
                "idEnvio": str(uuid.uuid4()).upper(),
                "version": 2,
                "nitEmisor": record.company_id.document_nit,
                "documentos": items
            })

            headers = {
                'Authorization': record.company_id.token_code,
                'User-Agent': 'request',
                'content-type': 'application/JSON'
            }
            # print(json_dict)
            # print(headers)

            if record.estado_dte == 'procesado' or record.estado_dte == 'procesado_lote':
                raise UserError('Las facturas dte no pueden estar previamente procesadas')

            try:
                response = requests.post(url, headers=headers, data=json_dict)
                json_response = response.json()
                print(json_response)
            except Exception as e:
                print(e)
                raise ValidationError(f'Ocurrió un error al conectarse al servicio de firmado')

            if response.status_code == 200:
                if json_response.get('estado') == 'RECIBIDO':
                    record.codigo_lote = json_response['codigoLote']
                    values = {
                        'estado_dte': 'procesado_lote',
                        'confirmacion': json_response['codigoLote']
                    }
                    record.write(values)
                    record.message_post(
                        body="El lote DTE se ha emitido correctamente.", message_type="notification")

    @api.onchange('tipo_generacion_documento', 'move_type')
    def onchange_tipo_generacion_documento(self):
        if self.move_type not in ('out_invoice', 'out_refund'):
            return
        journal_type = ''
        if self.tipo_generacion_documento == '1':
            journal_type = 'sale'
            journals = self.env['account.journal'].search([
                ('type', '=', journal_type),
                ('is_document_electronic', '=', False),
            ])
        elif self.tipo_generacion_documento == '2':
            journal_type = 'sale'
            journals = self.env['account.journal'].search([
                ('type', '=', journal_type),
                ('is_document_electronic', '=', True),
            ])
        else:
            journals = self.env['account.journal'].search([], limit=1)

        journal_ids = [j.id for j in journals]
        self.journal_id = journals and journals[0] or False
        return {'domain': {'journal_id': [('id', 'in', journal_ids)]}}

    def generate_qr_code(self):
        url = 'https://admin.factura.gob.sv/consultaPublica?ambiente={}&codGen={}&fechaEmi={}'.format(
            self.company_id.modo_prueba,
            self.uuid_generation_code,
            self.fecha_emision.strftime('%Y-%m-%d')
        )
        qr = qrcode.QRCode(version=1, box_size=5, border=5)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img_buf = io.BytesIO()
        img.save(img_buf, format='PNG')
        qr_img_data = img_buf.getvalue()
        qr_link = base64.b64encode(qr_img_data).decode('utf-8')
        self.qr_link = qr_link

    @api.depends('company_id.modo_prueba', 'uuid_generation_code', 'fecha_emision')
    def _compute_qr_link(self):
        for record in self:
            record.generate_qr_code()

    @api.depends('name')
    def _compute_last_numbers(self):
        for record in self:
            last_part = record.name.split('-')[-1]
            last_numbers = int(last_part)
            record.last_numbers = last_numbers



    def get_modelo_facturacion_display(self):
        return dict(self._fields['modelo_facturacion'].selection).get(self.modelo_facturacion)

    def get_tipo_transmision_display(self):
        return dict(self._fields['tipo_transmision'].selection).get(self.tipo_transmision)

    # last_numbers = fields.Integer(string='Last Numbers', compute='_compute_last_numbers')

    @api.depends('move_type')
    def _compute_show_original_invoice(self):
        for move in self:
            move.show_original_invoice = move.move_type == 'out_refund'

    show_original_invoice = fields.Boolean(
        compute='_compute_show_original_invoice', store=True)

    def firmar_contingencia(self):
        tz = pytz.timezone('America/El_Salvador')
        hora_actual = datetime.now(tz).strftime('%H:%M:%S')
        url = 'http://167.99.8.116:8113/firmardocumento/?content-Type=application/JSON&nit=06140506171049'

        num_documento_options = {
            '36': self.partner_id.document_nit_compute,
            '13': self.partner_id.document_dui,
            '03': self.partner_id.document_pasaporte,
            '02': self.partner_id.document_carnet_residente,
            '37': self.tipo_identificacion_receptor_otro,
        }

        datos_emisor = {
            "nit": self.company_id.document_nit,
            "nombre": self.company_id.name,
            "nombreResponsable": self.company_id.name,
            "tipoDocResponsable": self.tipo_identificacion_receptor,
            "numeroDocResponsable": num_documento_options.get(self.tipo_identificacion_receptor),
            "tipoEstablecimiento": self.tipo_establecimiento,
            "codEstableMH": None if not self.company_id.cod_estable_mh else self.company_id.cod_estable_mh,
            "codPuntoVenta": None if not self.company_id.cod_pv else self.company_id.cod_pv,
            "telefono": self.company_id.phone,
            "correo": self.company_id.email
        }
        emisor = datos_emisor
        #  items=[]
        #
        # for key, value in datos_emisor.items():
        #     items.append({key: value})

        #  print(items)
        # fact=[]

        # for i, factura in enumerate(self.journal_id):
        #    fac={
        #       "noItem":i + 1

        #  }
        # fact.append(fac)

        num = 0
        num1 = num + 1
        print(f"el numero correlativo es {num1}")

        payload = json.dumps({
            'nit': self.company_id.document_nit,
            'activo': "True",
            'passwordPri': self.company_id.private_pass_mh,
            'dteJson':
                {
                    "identificacion": {
                        "version": 3,
                        "ambiente": self.company_id.modo_prueba,
                        "codigoGeneracion": self.uuid_generation_code,
                        "fTransmision": self.fecha_emision.strftime('%Y-%m-%d'),
                        "hTransmision": hora_actual

                    },

                    "emisor": emisor,

                    "detalleDTE": [{
                        "noItem": num1,
                        "codigoGeneracion": self.uuid_generation_code,
                        "tipoDoc": self.journal_id.document_type_sv

                    }],

                    "motivo": {
                        "fInicio": self.fecha_emision.strftime('%Y-%m-%d'),
                        "fFin": self.invoice_date_due.strftime('%Y-%m-%d'),
                        "hInicio": hora_actual,
                        "hFin": self.hora_final,
                        "tipoContingencia": int(self.tipo_contingencia),
                        "motivoContingencia": None if not self.motivo_contig else self.motivo_contig
                    }

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
            print(e)
            raise ValidationError(
                'Ocurrió un error al conectarse al servicio de firmado')

        if response.status_code == 200:
            if json_response.get('status') == 'OK':
                values = {
                    'estado_contingencia': json_response['status'],
                    'documento_firmado_contingencia': json_response['body']
                }
                self.write(values)
            else:
                raise ValidationError(json_response.get(
                    'body', {}).get('mensaje', 'Error desconocido'))
        else:
            raise ValidationError(
                'Error al conectarse al servidor de DGII: %s' % response.content)

    def contingencia_generador(self):
        payload = json.dumps({
            "nit": self.company_id.document_nit,
            "documento": self.documento_firmado_contingencia,

        })

        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.company_id.token_code
        }
        url = ''
        if self.company_id.modo_prueba == '00':
            url = "https://apitest.dtes.mh.gob.sv/fesv/contingencia"
        elif self.company_id.modo_prueba == '01':
            url = "https://api.dtes.mh.gob.sv/fesv/contingencia"
        if not url:
            return
        try:
            response = requests.post(url, headers=headers, data=payload)
            json_response = response.json()
        except Exception as e:
            print(e)
            raise ValidationError('Ocurrió un error al conectarse al servidor de DGII: Verifica las credenciales de '
                                  'la empresa o genera un nuevo token de autenticación')

        if response.status_code == 200:
            if json_response.get('estado') == 'RECIBIDO':
                values = {
                    'estado_dte': 'procesado_contingencia',
                    'sello_recibido': json_response['selloRecibido'],
                    'fecha_factura': fields.Datetime.now(),
                    'mensaje': json_response['mensaje']
                }
                self.write(values)
            else:
                error_response = json.loads(response.content)
                error_message = 'Error al validar información del DTE: \n' + \
                                f"Estado: {error_response.get('estado')}\n" + \
                                f"Clasificación del mensaje: {error_response.get('mensaje')}\n" + \
                                f"Descripción del mensaje: {error_response.get('observaciones')}"
                raise ValidationError(error_message)
        else:
            raise ValidationError(
                'Error al conectarse al servidor de DGII: %s' % response.content)

    # @api.model
    # def _reverse_move_vals(self, default_values, cancel=True):
    #     values = super(AccountMove, self)._reverse_move_vals(
    #         default_values, cancel)
    #     if self.estado_factura == 'factura_correcta':
    #         values['uuid_relacionado'] = self.folio_fiscal
    #         values['methodo_pago'] = 'PUE'
    #         values['forma_pago_id'] = self.forma_pago_id.id
    #         values['tipo_comprobante'] = 'E'
    #         # values['uso_cfdi_id'] = self.env['catalogo.uso.cfdi'].sudo().search([
    #         #     ('code', '=', 'G02')]).id
    #         values['tipo_relacion'] = '01'
    #         values['fecha_factura'] = None
    #         values['qrcode_image'] = None
    #         values['numero_cetificado'] = None
    #         values['cetificaso_sat'] = None
    #         values['selo_digital_cdfi'] = None
    #         values['folio_fiscal'] = None
    #         values['estado_factura'] = 'factura_no_generada'
    #         values['factura_cfdi'] = False
    #         values['edi_document_ids'] = None
    #     return values

    # @api.returns('self', lambda value: value.id)
    #     # def copy(self, default=None):
    #     #     default = dict(default or {})
    #     #     default['estado_factura'] = 'factura_no_generada'
    #     #     default['folio_fiscal'] = ''
    #     #     default['factura_cfdi'] = False
    #     #     default['fecha_factura'] = None
    #     #     default['qrcode_image'] = None
    #     #     default['numero_cetificado'] = None
    #     #     default['cetificaso_sat'] = None
    #     #     default['selo_digital_cdfi'] = None
    #     #     default['folio_fiscal'] = None
    #     #     default['edi_document_ids'] = None
    #     #     return super(AccountMove, self).copy(default=default)

    @api.depends('name')
    def _get_number_folio(self):
        for record in self:
            if record.name:
                record.number_folio = record.name.replace(
                    'INV', '').replace('/', '')

    @api.depends('amount_total', 'currency_id')
    def _get_amount_to_text(self):
        for record in self:
            record.amount_to_text = amount_to_text_es_MX.get_amount_to_text(record, record.amount_total, 'es_cheque',
                                                                            record.currency_id.name)

    @api.depends('total_exportacion', 'currency_id')
    def _get_amount_to_text_exp(self):
        for record in self:
            record.amount_to_text_exp = amount_to_text_es_MX.get_amount_to_text(record, record.total_exportacion,
                                                                                'es_cheque',
                                                                                record.currency_id.name)\

    @api.depends('retencion_fc', 'currency_id')
    def _get_amount_to_text_ret(self):
        for record in self:
            record.amount_to_text_ret = amount_to_text_es_MX.get_amount_to_text(record, record.retencion_fc,
                                                                                'es_cheque',
                                                                                record.currency_id.name)

    @api.model
    def _get_amount_2_text(self, amount_total):
        return amount_to_text_es_MX.get_amount_to_text(self, amount_total, 'es_cheque', self.currency_id.name)

    # @api.onchange('partner_id')
    # def _get_uso_cfdi(self):
    #     if self.partner_id:
    #         values = {
    #             'uso_cfdi_id': self.partner_id.uso_cfdi_id.id
    #         }
    #         self.update(values)

    @api.onchange('invoice_payment_term_id')
    def _get_metodo_pago(self):
        if self.invoice_payment_term_id:
            if self.invoice_payment_term_id.methodo_pago == 'PPD':
                values = {
                    'methodo_pago': self.invoice_payment_term_id.methodo_pago,
                    'forma_pago_id': self.env['catalogo.forma.pago'].sudo().search([('code', '=', '99')])
                }
            else:
                values = {
                    'methodo_pago': self.invoice_payment_term_id.methodo_pago,
                    'forma_pago_id': False
                }
        else:
            values = {
                'methodo_pago': False,
                'forma_pago_id': False
            }
        self.update(values)

    @api.model
    def to_json(self):
        self.check_cfdi_values()

        if self.partner_id.vat == 'XAXX010101000' or self.partner_id.vat == 'XEXX010101000':
            zipreceptor = self.journal_id.codigo_postal or self.company_id.zip
            if self.factura_global:
                nombre = 'PUBLICO EN GENERAL'
            else:
                nombre = self.partner_id.name.upper()
        else:
            nombre = self.partner_id.name.upper()
            zipreceptor = self.partner_id.zip

        no_decimales = self.currency_id.no_decimales
        no_decimales_prod = self.currency_id.decimal_places
        no_decimales_tc = self.currency_id.no_decimales_tc

        # corregir hora
        timezone = self._context.get('tz')
        if not timezone:
            timezone = self.journal_id.tz or self.env.user.partner_id.tz or 'America/Mexico_City'
        # timezone = tools.ustr(timezone).encode('utf-8')

        local = pytz.timezone(timezone)
        if not self.fecha_factura:
            naive_from = datetime.datetime.now()
        else:
            naive_from = self.fecha_factura
        local_dt_from = naive_from.replace(tzinfo=pytz.UTC).astimezone(local)
        date_from = local_dt_from.strftime("%Y-%m-%dT%H:%M:%S")
        if not self.fecha_factura:
            self.fecha_factura = datetime.datetime.now()

        if self.currency_id.name == 'MXN':
            tipocambio = 1
        else:
            tipocambio = self.set_decimals(1 / self.currency_id.with_context(date=self.invoice_date).rate,
                                           no_decimales_tc)

        request_params = {
            'factura': {
                'serie': self.journal_id.serie_diario or self.company_id.serie_factura,
                'folio': str(re.sub('[^0-9]', '', self.name)),
                'fecha_expedicion': date_from,
                'forma_pago': self.forma_pago_id.code,
                'subtotal': self.amount_untaxed,
                'descuento': 0,
                'moneda': self.currency_id.name,
                'tipocambio': tipocambio,
                'total': self.amount_total,
                'tipocomprobante': self.tipo_comprobante,
                'metodo_pago': self.methodo_pago,
                'LugarExpedicion': self.journal_id.codigo_postal or self.company_id.zip,
                'Confirmacion': self.confirmacion,
                'Exportacion': self.exportacion,
            },
            'emisor': {
                'rfc': self.company_id.document_vat.upper(),
                'nombre': self.company_id.nombre_fiscal.upper(),
                'RegimenFiscal': self.company_id.regimen_fiscal_id.code,
                'FacAtrAdquirente': self.facatradquirente,
            },
            'receptor': {
                'nombre': nombre,
                'rfc': self.partner_id.vat.upper(),
                'ResidenciaFiscal': self.partner_id.residencia_fiscal,
                'NumRegIdTrib': self.partner_id.registro_tributario,
                'UsoCFDI': self.uso_cfdi_id.code,
                'RegimenFiscalReceptor': self.partner_id.regimen_fiscal_id.code,
                'DomicilioFiscalReceptor': zipreceptor,
            },
            'informacion': {
                'cfdi': '4.0',
                'sistema': 'odoo15',
                'version': '1',
                'api_key': self.company_id.proveedor_timbrado,
                'modo_prueba': self.company_id.modo_prueba,
            },
        }

        if self.factura_global:
            request_params.update({
                'InformacionGlobal': {
                    'Periodicidad': self.fg_periodicidad,
                    'Meses': self.fg_meses,
                    'Año': self.fg_ano,
                },
            })

        if self.uuid_relacionado:
            cfdi_relacionado = []
            uuids = self.uuid_relacionado.replace(' ', '').split(',')
            for uuid in uuids:
                cfdi_relacionado.append({
                    'uuid': uuid,
                })
            request_params.update({'CfdisRelacionados': {
                'UUID': cfdi_relacionado, 'TipoRelacion': self.tipo_relacion}})

        amount_total = 0.0
        amount_untaxed = 0.0
        self.subtotal = 0
        total = 0
        self.discount = 0
        tras_tot = 0
        ret_tot = 0
        tax_grouped_tras = {}
        tax_grouped_ret = {}
        tax_local_ret = []
        tax_local_tras = []
        tax_local_ret_tot = 0
        tax_local_tras_tot = 0
        items = {'numerodepartidas': len(self.invoice_line_ids)}
        invoice_lines = []
        for line in self.invoice_line_ids:
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue

            if not line.product_id.clave_producto:
                self.write({'proceso_timbrado': False})
                self.env.cr.commit()
                raise UserError(_('El producto %s no tiene clave del SAT configurado.') % (
                    line.product_id.name))
            if not line.product_id.cat_unidad_medida.clave:
                self.write({'proceso_timbrado': False})
                self.env.cr.commit()
                raise UserError(
                    _('El producto %s no tiene unidad de medida del SAT configurado.') % (line.product_id.name))

            price_wo_discount = line.price_unit * (1 - (line.discount / 100.0))

            taxes_prod = line.tax_ids.compute_all(price_wo_discount, line.currency_id, line.quantity,
                                                  product=line.product_id, partner=line.move_id.partner_id)
            tax_ret = []
            tax_tras = []
            tax_items = {}
            tax_included = 0
            for taxes in taxes_prod['taxes']:
                tax = self.env['account.tax'].browse(taxes['id'])
                if not tax.impuesto:
                    self.write({'proceso_timbrado': False})
                    self.env.cr.commit()
                    raise UserError(
                        _('El impuesto %s no tiene clave del SAT configurado.') % (tax.name))
                if not tax.tipo_factor:
                    self.write({'proceso_timbrado': False})
                    self.env.cr.commit()
                    raise UserError(
                        _('El impuesto %s no tiene tipo de factor del SAT configurado.') % (tax.name))
                if tax.impuesto != '004':
                    key = taxes['id']
                    if tax.price_include or tax.amount_type == 'division':
                        tax_included += taxes['amount']

                    if taxes['amount'] >= 0.0:
                        if tax.tipo_factor == 'Exento':
                            tax_tras.append({'Base': self.set_decimals(taxes['base'], no_decimales_prod),
                                             'Impuesto': tax.impuesto,
                                             'TipoFactor': tax.tipo_factor, })
                        elif tax.tipo_factor == 'Cuota':
                            tax_tras.append({'Base': self.set_decimals(line.quantity, no_decimales_prod),
                                             'Impuesto': tax.impuesto,
                                             'TipoFactor': tax.tipo_factor,
                                             'TasaOCuota': self.set_decimals(tax.amount, 6),
                                             'Importe': self.set_decimals(taxes['amount'], no_decimales_prod), })
                        else:
                            tax_tras.append({'Base': self.set_decimals(taxes['base'], no_decimales_prod),
                                             'Impuesto': tax.impuesto,
                                             'TipoFactor': tax.tipo_factor,
                                             'TasaOCuota': self.set_decimals(tax.amount / 100.0, 6),
                                             'Importe': self.set_decimals(taxes['amount'], no_decimales_prod), })
                        tras_tot += taxes['amount']
                        val = {'tax_id': taxes['id'],
                               'base': taxes['base'] if tax.tipo_factor != 'Cuota' else line.quantity,
                               'amount': taxes['amount'], }
                        if key not in tax_grouped_tras:
                            tax_grouped_tras[key] = val
                        else:
                            tax_grouped_tras[key]['base'] += val[
                                'base'] if tax.tipo_factor != 'Cuota' else line.quantity
                            tax_grouped_tras[key]['amount'] += val['amount']
                    else:
                        tax_ret.append({'Base': self.set_decimals(taxes['base'], no_decimales_prod),
                                        'Impuesto': tax.impuesto,
                                        'TipoFactor': tax.tipo_factor,
                                        'TasaOCuota': self.set_decimals(tax.amount / 100.0 * -1, 6),
                                        'Importe': self.set_decimals(taxes['amount'] * -1, no_decimales_prod), })
                        ret_tot += taxes['amount'] * -1
                        val = {'tax_id': taxes['id'],
                               'base': taxes['base'],
                               'amount': taxes['amount'], }
                        if key not in tax_grouped_ret:
                            tax_grouped_ret[key] = val
                        else:
                            tax_grouped_ret[key]['base'] += val['base']
                            tax_grouped_ret[key]['amount'] += val['amount']
                else:  # impuestos locales
                    if tax.price_include or tax.amount_type == 'division':
                        tax_included += taxes['amount']
                    if taxes['amount'] >= 0.0:
                        tax_local_tras_tot += taxes['amount']
                        tax_local_tras.append({'ImpLocTrasladado': tax.impuesto_local,
                                               'TasadeTraslado': self.set_decimals(tax.amount, 2),
                                               'Importe': self.set_decimals(taxes['amount'], 2), })
                    else:
                        tax_local_ret_tot += taxes['amount']
                        tax_local_ret.append({'ImpLocRetenido': tax.impuesto_local,
                                              'TasadeRetencion': self.set_decimals(tax.amount * -1, 2),
                                              'Importe': self.set_decimals(taxes['amount'] * -1, 2), })

            if tax_tras:
                tax_items.update({'Traslados': tax_tras})
            if tax_ret:
                tax_items.update({'Retenciones': tax_ret})

            total_wo_discount = round(
                line.price_unit * line.quantity - tax_included, no_decimales_prod)
            discount_prod = round(
                total_wo_discount - line.price_subtotal, no_decimales_prod) if line.discount else 0
            precio_unitario = round(
                total_wo_discount / line.quantity, no_decimales_prod)
            self.subtotal += total_wo_discount
            self.discount += discount_prod

            # probar con varios pedimentos
            pedimentos = []
            if line.pedimento:
                pedimento_list = line.pedimento.replace(' ', '').split(',')
                for pedimento in pedimento_list:
                    if len(pedimento) != 15:
                        self.write({'proceso_timbrado': False})
                        self.env.cr.commit()
                        raise UserError(
                            _('La longitud del pedimento debe ser de 15 dígitos.'))
                    pedimentos.append({'NumeroPedimento': pedimento[0:2] + '  ' + pedimento[2:4] + '  ' + pedimento[
                                                                                                          4:8] + '  ' + pedimento[
                                                                                                               8:]})

            product_string = line.product_id.code and line.product_id.code[:100] or ''
            if product_string == '':
                if line.name.find(']') > 0:
                    product_string = line.name[line.name.find(
                        '[') + len('['):line.name.find(']')] or ''
            description = line.name
            if line.name.find(']') > 0:
                description = line.name[line.name.find(']') + 2:]

            if self.tipo_comprobante == 'T':
                invoice_lines.append({'cantidad': self.set_decimals(line.quantity, 6),
                                      'unidad': line.product_id.cat_unidad_medida.descripcion,
                                      'NoIdentificacion': self.clean_text(product_string),
                                      'valorunitario': self.set_decimals(precio_unitario, no_decimales_prod),
                                      'importe': self.set_decimals(total_wo_discount, no_decimales_prod),
                                      'descripcion': self.clean_text(description),
                                      'ClaveProdServ': line.product_id.clave_producto,
                                      'ObjetoImp': line.product_id.objetoimp,
                                      'ClaveUnidad': line.product_id.cat_unidad_medida.clave})
            else:
                invoice_lines.append({'cantidad': self.set_decimals(line.quantity, 6),
                                      'unidad': line.product_id.cat_unidad_medida.descripcion,
                                      'NoIdentificacion': self.clean_text(product_string),
                                      'valorunitario': self.set_decimals(precio_unitario, no_decimales_prod),
                                      'importe': self.set_decimals(total_wo_discount, no_decimales_prod),
                                      'descripcion': self.clean_text(description),
                                      'ClaveProdServ': line.product_id.clave_producto,
                                      'ClaveUnidad': line.product_id.cat_unidad_medida.clave,
                                      'Impuestos': tax_items and tax_items or '',
                                      'Descuento': self.set_decimals(discount_prod, no_decimales_prod),
                                      'ObjetoImp': line.product_id.objetoimp,
                                      'InformacionAduanera': pedimentos and pedimentos or '',
                                      'predial': line.predial and line.predial or '', })

        tras_tot = round(tras_tot, no_decimales)
        ret_tot = round(ret_tot, no_decimales)
        tax_local_tras_tot = round(tax_local_tras_tot, no_decimales)
        tax_local_ret_tot = round(tax_local_ret_tot, no_decimales)
        self.discount = round(self.discount, no_decimales)
        self.subtotal = self.roundTraditional(self.subtotal, no_decimales)
        impuestos = {}
        if tax_grouped_tras or tax_grouped_ret:
            retenciones = []
            traslados = []
            if tax_grouped_tras:
                for line in tax_grouped_tras.values():
                    tax = self.env['account.tax'].browse(line['tax_id'])
                    if tax.tipo_factor == 'Exento':
                        tasa_tr = ''
                    elif tax.tipo_factor == 'Cuota':
                        tasa_tr = self.set_decimals(tax.amount, 6)
                    else:
                        tasa_tr = self.set_decimals(tax.amount / 100.0, 6)
                    traslados.append({'impuesto': tax.impuesto,
                                      'TipoFactor': tax.tipo_factor,
                                      'tasa': tasa_tr,
                                      'importe': self.roundTraditional(line['amount'],
                                                                       no_decimales) if tax.tipo_factor != 'Exento' else '',
                                      'base': self.roundTraditional(line['base'], no_decimales),
                                      'tax_id': line['tax_id'],
                                      })
                impuestos.update(
                    {'translados': traslados, 'TotalImpuestosTrasladados': self.set_decimals(tras_tot, no_decimales)})
            if tax_grouped_ret:
                for line in tax_grouped_ret.values():
                    tax = self.env['account.tax'].browse(line['tax_id'])
                    retenciones.append({'impuesto': tax.impuesto,
                                        'TipoFactor': tax.tipo_factor,
                                        'tasa': self.set_decimals(float(tax.amount) / 100.0 * -1, 6),
                                        'importe': self.roundTraditional(line['amount'] * -1, no_decimales),
                                        'base': self.roundTraditional(line['base'], no_decimales),
                                        'tax_id': line['tax_id'],
                                        })
                impuestos.update(
                    {'retenciones': retenciones, 'TotalImpuestosRetenidos': self.set_decimals(ret_tot, no_decimales)})
            request_params.update({'impuestos': impuestos})
        self.tax_payment = json.dumps(impuestos)

        if tax_local_ret or tax_local_tras:
            if tax_local_tras and not tax_local_ret:
                request_params.update({'implocal10': {'TotaldeTraslados': self.roundTraditional(tax_local_tras_tot, 2),
                                                      'TotaldeRetenciones': self.roundTraditional(tax_local_ret_tot, 2),
                                                      'TrasladosLocales': tax_local_tras, }})
            if tax_local_ret and not tax_local_tras:
                request_params.update({'implocal10': {'TotaldeTraslados': self.roundTraditional(tax_local_tras_tot, 2),
                                                      'TotaldeRetenciones': self.roundTraditional(
                                                          tax_local_ret_tot * -1,
                                                          2),
                                                      'RetencionesLocales': tax_local_ret, }})
            if tax_local_ret and tax_local_tras:
                request_params.update({'implocal10': {'TotaldeTraslados': self.roundTraditional(tax_local_tras_tot, 2),
                                                      'TotaldeRetenciones': self.roundTraditional(
                                                          tax_local_ret_tot * -1,
                                                          2),
                                                      'TrasladosLocales': tax_local_tras,
                                                      'RetencionesLocales': tax_local_ret, }})

        if self.tipo_comprobante == 'T':
            request_params['factura'].update(
                {'descuento': '', 'subtotal': '0.00', 'total': '0.00'})
            self.total_factura = 0
        else:
            self.total_factura = round(
                self.subtotal + tras_tot - ret_tot - self.discount + tax_local_ret_tot + tax_local_tras_tot, 2)
            request_params['factura'].update({'descuento': self.roundTraditional(self.discount, no_decimales),
                                              'subtotal': self.roundTraditional(self.subtotal, no_decimales),
                                              'total': self.roundTraditional(self.total_factura, no_decimales)})

        request_params.update({'conceptos': invoice_lines})

        return request_params

    def set_decimals(self, amount, precision):
        if amount is None or amount is False:
            return None
        return '%.*f' % (precision, amount)

    def roundTraditional(self, val, digits):
        if val != 0:
            return round(val + 10 ** (-len(str(val)) - 1), digits)
        else:
            return 0

    def clean_text(self, text):
        clean_text = text.replace('\n', ' ').replace('\\', ' ').replace(
            '-', ' ').replace('/', ' ').replace('|', ' ')
        clean_text = clean_text.replace(',', ' ').replace(
            ';', ' ').replace('>', ' ').replace('<', ' ')
        return clean_text[:1000]

    def check_cfdi_values(self):
        if not self.company_id.document_vat:
            self.write({'proceso_timbrado': False})
            self.env.cr.commit()
            raise UserError(_('El emisor no tiene RFC configurado.'))
        if not self.company_id.name:
            self.write({'proceso_timbrado': False})
            self.env.cr.commit()
            raise UserError(_('El emisor no tiene nombre configurado.'))
        if not self.partner_id.vat:
            self.write({'proceso_timbrado': False})
            self.env.cr.commit()
            raise UserError(_('El receptor no tiene RFC configurado.'))
        if not self.partner_id.name:
            self.write({'proceso_timbrado': False})
            self.env.cr.commit()
            raise UserError(_('El receptor no tiene nombre configurado.'))
        if not self.uso_cfdi_id:
            self.write({'proceso_timbrado': False})
            self.env.cr.commit()
            raise UserError(_('La factura no tiene uso de cfdi configurado.'))
        if not self.tipo_comprobante:
            self.write({'proceso_timbrado': False})
            self.env.cr.commit()
            raise UserError(
                _('El emisor no tiene tipo de comprobante configurado.'))
        if self.tipo_comprobante != 'T' and not self.methodo_pago:
            self.write({'proceso_timbrado': False})
            self.env.cr.commit()
            raise UserError(
                _('La factura no tiene método de pago configurado.'))
        if self.tipo_comprobante != 'T' and not self.forma_pago_id:
            self.write({'proceso_timbrado': False})
            self.env.cr.commit()
            raise UserError(
                _('La factura no tiene forma de pago configurado.'))
        if not self.company_id.regimen_fiscal_id:
            self.write({'proceso_timbrado': False})
            self.env.cr.commit()
            raise UserError(_('El emisor no régimen fiscal configurado.'))
        if not self.journal_id.codigo_postal and not self.company_id.zip:
            self.write({'proceso_timbrado': False})
            self.env.cr.commit()
            raise UserError(_('El emisor no tiene código postal configurado.'))

    def _set_data_from_xml(self, xml_invoice):
        if not xml_invoice:
            return None
        NSMAP = {
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'cfdi': 'http://www.sat.gob.mx/cfd/4',
            'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
        }

        xml_data = etree.fromstring(xml_invoice)
        Complemento = xml_data.find('cfdi:Complemento', NSMAP)
        TimbreFiscalDigital = Complemento.find(
            'tfd:TimbreFiscalDigital', NSMAP)

        self.total_factura = xml_data.attrib['Total']
        self.tipocambio = xml_data.attrib['TipoCambio']
        self.moneda = xml_data.attrib['Moneda']
        self.numero_cetificado = xml_data.attrib['NoCertificado']
        self.cetificaso_sat = TimbreFiscalDigital.attrib['NoCertificadoSAT']
        self.fecha_certificacion = TimbreFiscalDigital.attrib['FechaTimbrado']
        self.selo_digital_cdfi = TimbreFiscalDigital.attrib['SelloCFD']
        self.selo_sat = TimbreFiscalDigital.attrib['SelloSAT']
        self.folio_fiscal = TimbreFiscalDigital.attrib['UUID']
        version = TimbreFiscalDigital.attrib['Version']
        self.cadena_origenal = '||%s|%s|%s|%s|%s||' % (version, self.folio_fiscal, self.fecha_certificacion,
                                                       self.selo_digital_cdfi, self.cetificaso_sat)

        options = {'width': 275 * mm, 'height': 275 * mm}
        amount_str = str(self.amount_total).split('.')
        qr_value = 'https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx?&id=%s&re=%s&rr=%s&tt=%s.%s&fe=%s' % (
            self.folio_fiscal,
            self.company_id.document_vat,
            self.partner_id.vat,
            amount_str[0].zfill(10),
            amount_str[1].ljust(6, '0'),
            self.selo_digital_cdfi[-8:],
        )
        self.qr_value = qr_value
        ret_val = createBarcodeDrawing('QR', value=qr_value, **options)
        self.qrcode_image = base64.encodebytes(ret_val.asString('jpg'))

    def print_l10n_sv_edi(self):
        self.ensure_one()
        # return self.env['report'].get_action(self, 'custom_invoice.l10n_sv_edi_report') #modulename.custom_report_coupon
        filename = 'CFDI_' + self.name.replace('/', '_') + '.pdf'
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_document?model=account.move&field=pdf_l10n_sv_edi&id=%s&filename=%s' % (
                self.id, filename),
            'target': 'self',
        }

    def action_cfdi_generate(self):
        # after validate, send invoice data to external system via http post
        for invoice in self:
            if invoice.proceso_timbrado:
                return True
            else:
                invoice.write({'proceso_timbrado': True})
                self.env.cr.commit()
            if invoice.estado_factura == 'factura_correcta':
                if invoice.folio_fiscal:
                    invoice.write({'factura_cfdi': True})
                    return True
                else:
                    invoice.write({'proceso_timbrado': False})
                    self.env.cr.commit()
                    raise UserError(
                        _('Error para timbrar factura, Factura ya generada.'))
            if invoice.estado_factura == 'factura_cancelada':
                invoice.write({'proceso_timbrado': False})
                self.env.cr.commit()
                raise UserError(
                    _('Error para timbrar factura, Factura ya generada y cancelada.'))

            values = invoice.to_json()
            if invoice.company_id.proveedor_timbrado == 'multifactura':
                url = '%s' % ('http://facturacion.itadmin.com.mx/api/invoice')
            elif invoice.company_id.proveedor_timbrado == 'multifactura2':
                url = '%s' % ('http://facturacion2.itadmin.com.mx/api/invoice')
            elif invoice.company_id.proveedor_timbrado == 'multifactura3':
                url = '%s' % ('http://facturacion3.itadmin.com.mx/api/invoice')
            elif invoice.company_id.proveedor_timbrado == 'gecoerp':
                if self.company_id.modo_prueba:
                    url = '%s' % (
                        'https://itadmin.gecoerp.com/invoice/?handler=OdooHandler33')
                else:
                    url = '%s' % (
                        'https://itadmin.gecoerp.com/invoice/?handler=OdooHandler33')
            else:
                invoice.write({'proceso_timbrado': False})
                self.env.cr.commit()
                raise UserError(
                    _('Error, falta seleccionar el servidor de timbrado en la configuración de la compañía.'))

            try:
                response = requests.post(url,
                                         auth=None, verify=False, data=json.dumps(values),
                                         headers={"Content-type": "application/json"})
            except Exception as e:
                error = str(e)
                invoice.write({'proceso_timbrado': False})
                self.env.cr.commit()
                if "Name or service not known" in error or "Failed to establish a new connection" in error:
                    raise UserError(_("No se pudo conectar con el servidor."))
                else:
                    raise UserError(_(error))

            if "Whoops, looks like something went wrong." in response.text:
                invoice.write({'proceso_timbrado': False})
                self.env.cr.commit()
                raise UserError(_(
                    "Error en el proceso de timbrado, espere un minuto y vuelva a intentar timbrar nuevamente. \nSi el error aparece varias veces reportarlo con la persona de sistemas."))
            else:
                json_response = response.json()
            estado_factura = json_response['estado_factura']
            if estado_factura == 'problemas_factura':
                invoice.write({'proceso_timbrado': False})
                self.env.cr.commit()
                raise UserError(_(json_response['problemas_message']))
            # Receive and stroe XML invoice
            if json_response.get('factura_xml'):
                invoice._set_data_from_xml(
                    base64.b64decode(json_response['factura_xml']))
                file_name = invoice.name.replace('/', '_') + '.xml'
                self.env['ir.attachment'].sudo().create(
                    {
                        'name': file_name,
                        'datas': json_response['factura_xml'],
                        # 'datas_fname': file_name,
                        'res_model': self._name,
                        'res_id': invoice.id,
                        'type': 'binary'
                    })

            invoice.write({'estado_factura': estado_factura,
                           'factura_cfdi': True,
                           'proceso_timbrado': False})
            invoice.message_post(body="CFDI emitido")
        return True

    # def generate_dte_sv(self):
    #     for invoice in self:
    #         if invoice.company_id.token_label:
    #             try:
    #

    def action_cfdi_cancel(self):
        for invoice in self:
            if invoice.factura_cfdi:
                if invoice.estado_factura == 'factura_cancelada':
                    pass
                    # raise UserError(_('La factura ya fue cancelada, no puede volver a cancelarse.'))
                if not invoice.company_id.contrasena:
                    raise UserError(
                        _('El campo de contraseña de los certificados está vacío.'))
                domain = [
                    ('res_id', '=', invoice.id),
                    ('res_model', '=', invoice._name),
                    ('name', '=', invoice.name.replace('/', '_') + '.xml')]
                xml_file = self.env['ir.attachment'].search(domain)
                if not xml_file:
                    raise UserError(
                        _('No se encontró el archivo XML para enviar a cancelar.'))
                values = {
                    'rfc': invoice.company_id.vat,
                    'api_key': invoice.company_id.proveedor_timbrado,
                    'uuid': invoice.folio_fiscal,
                    'folio': invoice.name.replace('INV', '').replace('/', ''),
                    'serie_factura': invoice.journal_id.serie_diario or invoice.company_id.serie_factura,
                    'modo_prueba': invoice.company_id.modo_prueba,
                    'certificados': {
                        #    'archivo_cer': archivo_cer.decode("utf-8"),
                        #    'archivo_key': archivo_key.decode("utf-8"),
                        'contrasena': invoice.company_id.contrasena,
                    },
                    'xml': xml_file[0].datas.decode("utf-8"),
                    'motivo': self.env.context.get('motivo_cancelacion', '02'),
                    'foliosustitucion': self.env.context.get('foliosustitucion', ''),
                }
                if self.company_id.proveedor_timbrado == 'multifactura':
                    url = '%s' % (
                        'http://facturacion.itadmin.com.mx/api/refund')
                elif invoice.company_id.proveedor_timbrado == 'multifactura2':
                    url = '%s' % (
                        'http://facturacion2.itadmin.com.mx/api/refund')
                elif invoice.company_id.proveedor_timbrado == 'multifactura3':
                    url = '%s' % (
                        'http://facturacion3.itadmin.com.mx/api/refund')
                elif self.company_id.proveedor_timbrado == 'gecoerp':
                    if self.company_id.modo_prueba:
                        url = '%s' % (
                            'https://itadmin.gecoerp.com/refund/?handler=OdooHandler33')
                    else:
                        url = '%s' % (
                            'https://itadmin.gecoerp.com/refund/?handler=OdooHandler33')
                else:
                    raise UserError(
                        _('Error, falta seleccionar el servidor de timbrado en la configuración de la compañía.'))

                try:
                    response = requests.post(url,
                                             auth=None, verify=False, data=json.dumps(values),
                                             headers={"Content-type": "application/json"})
                except Exception as e:
                    error = str(e)
                    if "Name or service not known" in error or "Failed to establish a new connection" in error:
                        raise UserError(
                            _("No se pudo conectar con el servidor."))
                    else:
                        raise UserError(_(error))

                if "Whoops, looks like something went wrong." in response.text:
                    raise UserError(_(
                        "Error en el proceso de timbrado, espere un minuto y vuelva a intentar timbrar nuevamente. \nSi el error aparece varias veces reportarlo con la persona de sistemas."))

                json_response = response.json()

                log_msg = ''
                if json_response['estado_factura'] == 'problemas_factura':
                    raise UserError(_(json_response['problemas_message']))
                elif json_response['estado_factura'] == 'solicitud_cancelar':
                    log_msg = "Se solicitó cancelación de CFDI"
                elif json_response.get('factura_xml', False):
                    file_name = 'CANCEL_' + \
                                invoice.name.replace('/', '_') + '.xml'
                    self.env['ir.attachment'].sudo().create(
                        {
                            'name': file_name,
                            'datas': json_response['factura_xml'],
                            # 'datas_fname': file_name,
                            'res_model': self._name,
                            'res_id': invoice.id,
                            'type': 'binary'
                        })
                    log_msg = "CFDI Cancelado"
                invoice.write(
                    {'estado_factura': json_response['estado_factura']})
                invoice.message_post(body=log_msg)

    def force_invoice_send(self):
        for inv in self:
            email_act = inv.action_invoice_sent()
            if email_act and email_act.get('context'):
                email_ctx = email_act['context']
                email_ctx.update(default_email_from=inv.company_id.email)
                inv.with_context(email_ctx).message_post_with_template(
                    email_ctx.get('default_template_id'))
        return True

    @api.model
    def check_cancel_status_by_cron(self):
        domain = [('move_type', '=', 'out_invoice'),
                  ('estado_factura', '=', 'solicitud_cancelar')]
        invoices = self.search(domain, order='id')
        for invoice in invoices:
            _logger.info('Solicitando estado de factura %s',
                         invoice.folio_fiscal)
            domain = [
                ('res_id', '=', invoice.id),
                ('res_model', '=', invoice._name),
                ('name', '=', invoice.name.replace('/', '_') + '.xml')]
            xml_file = self.env['ir.attachment'].search(domain, limit=1)
            if not xml_file:
                _logger.info('No se encontró XML de la factura %s',
                             invoice.folio_fiscal)
                continue
            values = {
                'rfc': invoice.company_id.vat,
                'api_key': invoice.company_id.proveedor_timbrado,
                'modo_prueba': invoice.company_id.modo_prueba,
                'uuid': invoice.folio_fiscal,
                'xml': xml_file.datas.decode("utf-8"),
            }

            if invoice.company_id.proveedor_timbrado == 'multifactura':
                url = '%s' % (
                    'http://facturacion.itadmin.com.mx/api/consulta-cacelar')
            elif invoice.company_id.proveedor_timbrado == 'multifactura2':
                url = '%s' % (
                    'http://facturacion2.itadmin.com.mx/api/consulta-cacelar')
            elif invoice.company_id.proveedor_timbrado == 'multifactura3':
                url = '%s' % (
                    'http://facturacion3.itadmin.com.mx/api/consulta-cacelar')
            elif invoice.company_id.proveedor_timbrado == 'gecoerp':
                url = '%s' % (
                    'http://facturacion.itadmin.com.mx/api/consulta-cacelar')
            else:
                raise UserError(
                    _('Error, falta seleccionar el servidor de timbrado en la configuración de la compañía.'))

            try:
                response = requests.post(url,
                                         auth=None, verify=False, data=json.dumps(values),
                                         headers={"Content-type": "application/json"})

                if "Whoops, looks like something went wrong." in response.text:
                    _logger.info(
                        "Error con el servidor de facturación, favor de reportar el error a su persona de soporte.")
                    return

                json_response = response.json()
                # _logger.info('something ... %s', response.text)
            except Exception as e:
                _logger.info('log de la exception ... %s', response.text)
                json_response = {}
            if not json_response:
                return
            estado_factura = json_response['estado_consulta']
            if estado_factura == 'problemas_consulta':
                _logger.info('Error en la consulta %s',
                             json_response['problemas_message'])
            elif estado_factura == 'consulta_correcta':
                if json_response['factura_xml'] == 'Cancelado':
                    _logger.info('Factura cancelada')
                    _logger.info('EsCancelable: %s',
                                 json_response['escancelable'])
                    _logger.info('EstatusCancelacion: %s',
                                 json_response['estatuscancelacion'])
                    invoice.action_cfdi_cancel()
                elif json_response['factura_xml'] == 'Vigente':
                    _logger.info('Factura vigente')
                    _logger.info('EsCancelable: %s',
                                 json_response['escancelable'])
                    _logger.info('EstatusCancelacion: %s',
                                 json_response['estatuscancelacion'])
                    if json_response['estatuscancelacion'] == 'Solicitud rechazada':
                        invoice.estado_factura = 'solicitud_rechazada'
            else:
                _logger.info('Error... %s', response.text)
        return True

    def action_cfdi_rechazada(self):
        for invoice in self:
            if invoice.factura_cfdi:
                if invoice.estado_factura == 'solicitud_rechazada' or invoice.estado_factura == 'solicitud_cancelar':
                    invoice.estado_factura = 'factura_correcta'
                    # raise UserError(_('La factura ya fue cancelada, no puede volver a cancelarse.'))

    def liberar_cfdi(self):
        for invoice in self:
            values = {
                'command': 'liberar_cfdi',
                'rfc': invoice.company_id.vat,
                'folio': str(re.sub('[^0-9]', '', invoice.name)),
                'serie_factura': invoice.journal_id.serie_diario or invoice.company_id.serie_factura,
                'archivo_cer': invoice.company_id.archivo_cer.decode("utf-8"),
                'archivo_key': invoice.company_id.archivo_key.decode("utf-8"),
                'contrasena': invoice.company_id.contrasena,
            }
            url = ''
            if invoice.company_id.proveedor_timbrado == 'multifactura':
                url = '%s' % ('http://facturacion.itadmin.com.mx/api/command')
            elif invoice.company_id.proveedor_timbrado == 'multifactura2':
                url = '%s' % ('http://facturacion2.itadmin.com.mx/api/command')
            elif invoice.company_id.proveedor_timbrado == 'multifactura3':
                url = '%s' % ('http://facturacion3.itadmin.com.mx/api/command')
            if not url:
                return
            try:
                response = requests.post(url, auth=None, verify=False, data=json.dumps(values),
                                         headers={"Content-type": "application/json"})

                if "Whoops, looks like something went wrong." in response.text:
                    raise UserError(_(
                        "Error con el servidor de facturación, favor de reportar el error a su persona de soporte."))

                json_response = response.json()
            except Exception as e:
                print(e)
                json_response = {}

            if not json_response:
                return
            # _logger.info('something ... %s', response.text)

            respuesta = json_response['respuesta']
            message_id = self.env['mymodule.message.wizard'].create(
                {'message': respuesta})
            return {
                'name': 'Respuesta',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mymodule.message.wizard',
                'res_id': message_id.id,
                'target': 'new'
            }
            
  
   
   
    class MailTemplate(models.Model):
        "Templates for sending email"
        _inherit = 'mail.template'

        def generate_email(self, res_ids, fields=None):
            results = super(MailTemplate, self).generate_email(
                res_ids, fields=fields)

            if isinstance(res_ids, (int)):
                res_ids = [res_ids]

            for lang, (template, template_res_ids) in self._classify_per_lang(res_ids).items():
                if template.report_template and template.report_template.report_name == 'account.report_invoice_with_payments' or template.report_template.report_name == 'account.report_invoice':
                    for res_id in template_res_ids:
                        invoice = self.env[template.model].browse(res_id)
                        if not invoice.factura_cfdi:
                            continue
                        if invoice.estado_factura == 'factura_correcta' or invoice.estado_factura == 'solicitud_cancelar':
                            domain = [
                                ('res_id', '=', invoice.id),
                                ('res_model', '=', invoice._name),
                                ('name', '=', invoice.name.replace('/', '_') + '.xml')]
                            xml_file = self.env['ir.attachment'].search(
                                domain, limit=1)
                            attachments = results[res_id]['attachments'] or []
                            if xml_file:
                                attachments.append(
                                    ('CFDI_' + invoice.name.replace('/', '_') + '.xml', xml_file.datas))
                        else:
                            domain = [
                                ('res_id', '=', invoice.id),
                                ('res_model', '=', invoice._name),
                                ('name', '=', 'CANCEL_' + invoice.name.replace('/', '_') + '.xml')]
                            xml_file = self.env['ir.attachment'].search(
                                domain, limit=1)
                            attachments = []
                            if xml_file:
                                attachments.append(
                                    ('CFDI_CANCEL_' + invoice.name.replace('/', '_') + '.xml', xml_file.datas))
                        results[res_id]['attachments'] = attachments
            return results

    class AccountPaymentTerm(models.Model):
        "Terminos de pago"
        _inherit = "account.payment.term"

        methodo_pago = fields.Selection(
            selection=[('PUE', _('Pago en una sola exhibición')),
                       ('PPD', _('Pago en parcialidades o diferido')), ],
            string=_('Método de pago'),
        )

        forma_pago_id = fields.Many2one(
            'catalogo.forma.pago', string='Forma de pago')

        forma_pago_id = fields.Many2one(
            'catalogo.forma.pago', string='Forma de pago')
        # CAT-016
        condicion_operacion = fields.Selection(
            selection=[
                ('1', 'Contado'),
                ('2', 'A crédito'),
                ('3', 'Otro'),
            ],
            string='Condición de la Operacion', default='1', required=True
        )

        # CAT-018
        plazo = fields.Selection(
            selection=[
                ('01', 'Días'),
                ('02', 'Meses'),
                ('03', 'Años'),
            ],
            string='Plazo'
        )
        plazo_dias = fields.Integer(string='Días')
        plazo_meses = fields.Integer(string='Meses')
        plazo_anyos = fields.Integer(string='Años')
    
  
    
    class AccountMoveLine(models.Model):
        _inherit = "account.move.line"

    class AccountMoveLine(models.Model):
        _inherit = "account.move.line"

        pedimento = fields.Char('Pedimento')
        predial = fields.Char('No. Predial')

        @api.depends('product_id.type_item_edi')
        def _compute_type_item_edi(self):
            for line in self:
                line.type_item_edi_id = line.product_id.type_item_edi

        @api.depends('product_id.type_item_edi')
        def _compute_type_item_edi(self):
            for line in self:
                line.type_item_edi_id = line.product_id.type_item_edi

        type_item_edi_id = fields.Selection(string='Tipo de item',
                                            selection=[
                                                ('1', 'Bienes'),
                                                ('2', 'Servicios'),
                                                ('3',
                                                 'Ambos (Bienes y Servicios, incluye los dos inherente a los productos o servicios)'),
                                                ('4', 'Otros tributos por ítem')
                                            ],
                                            compute='_compute_type_item_edi',
                                            store=True, readonly=False, precompute=True,
                                            required=True,
                                            )

    class MyModuleMessageWizard(models.TransientModel):
        _name = 'mymodule.message.wizard'
        _description = "Show Message"

        message = fields.Text('Message', required=True)

        #    @api.multi
        def action_close(self):
            return {'type': 'ir.actions.act_window_close'}

        #    @api.multi
        def action_close(self):
            return {'type': 'ir.actions.act_window_close'}


from odoo import models, fields, api
import base64

class AccountMove(models.Model):
    _inherit = 'account.move'

    # def action_invoice_sent(self):
    #     res = super().action_invoice_sent()
    #
    #     for record in self:
    #         # Generar el archivo JSON
    #         if record.json_total:
    #             json_filename = f"{record.partner_id.name}_{record.name}.json"
    #             json_path = os.path.join(tempfile.gettempdir(), json_filename)
    #
    #             # Crear el archivo JSON
    #             with open(json_path, "w", encoding="utf-8") as f:
    #                 f.write(record.json_total)
    #
    #             # Adjuntar el archivo JSON al formulario de envío
    #             json_attachment = self.env['ir.attachment'].create({
    #                 'name': json_filename,
    #                 'datas': base64.b64encode(open(json_path, 'rb').read()),
    #                 'res_model': 'account.move',
    #                 'res_id': record.id,
    #                 'type': 'binary'
    #             })
    #
    #             # Agregar el adjunto del archivo JSON al contexto del formulario de envío
    #             res['context'].update({
    #                 'default_attachment_ids': [(json_attachment.id)],
    #             })
    #
    #     return res

    def _get_mail_template_dte(self):
        """
        :return: the correct mail template based on the current move type
        """
        return (
            'l10n_sv_edi.email_template_invoice_dte_sv'
            if all(move.move_type == 'out_refund' for move in self)
            else 'l10n_sv_edi.email_template_invoice_dte_sv'
        )

    def action_invoice_sent(self):
        res = super().action_invoice_sent()
        if self.json_total:
            # Generar el archivo JSON
            filename = f"{self.partner_id.name}_{self.name}.json"
            path = tempfile.gettempdir() + '/' + filename

            with open(path, "w", encoding="utf-8") as f:
                f.write(self.json_total)

            # Leer el archivo JSON y codificarlo en base64
            with open(path, 'rb') as file:
                json_data = file.read()
                encoded_data = base64.b64encode(json_data)

            # Adjuntar el archivo JSON al formulario de envío
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'datas': encoded_data,
                'res_model': 'account.move',
                'res_id': self.id,
                'type': 'binary'
            })

            # Obtener el ID del adjunto para utilizarlo en el template de correo
            attachment_id = attachment.id

            # Actualizar los adjuntos del template de correo
            template = self.env.ref(self._get_mail_template_dte(), raise_if_not_found=False)
            if template:
                # Eliminar los adjuntos anteriores
                template.attachment_ids = [(3, attachment.id) for attachment in template.attachment_ids]

                # Agregar el nuevo adjunto
                template.attachment_ids = [(4, attachment_id)]

            # Agregar el adjunto al formulario de envío
            compose_form = self.env.ref('account.account_invoice_send_wizard_form', raise_if_not_found=False)
            if compose_form:
                compose_form = compose_form.with_context(
                    active_ids=[self.id],
                    active_model='account.move',
                    attachment_ids=[attachment.id],
                    default_template_id=template and template.id or False,
                )
                res['context'] = compose_form._context

            self.message_post(
                body="El archivo JSON se ha generado correctamente.",
                message_type="notification"
            )

        return res






# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
from reportlab.lib.styles import getSampleStyleSheet

from io import BytesIO
from reportlab.lib.pagesizes import letter,landscape
from reportlab.lib import colors
#from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph,Spacer
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image,Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

import base64

class PlanesSaas(models.Model):
    _name = 'plan.saas'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Planes de pago'
    
    name = fields.Char(string="Nombre ")
    
    currency_id = fields.Many2one('res.currency', string='Currency') #default=lambda self: self.env.company.currency_id)

    precio= fields.Monetary(string="Precio",  currency_field="currency_id" ,store=True)
   # precio_formart=fields.Char(string="Precio")
    descripcion = fields.Text(string="Descripcion",widget='text_preview')
    
    start_date = fields.Date(string='Inicio', default=fields.Date.today)
    
    
    duration = fields.Integer(string='Duracion(Días)', default=1, readonly=True)
    
    end_date = fields.Date(string='Fin',
                           compute='_compute_end_date',
                           inverse='_inverse_end_date', store=True)
    
    modulos=fields.One2many('ln10_sv_saas.category', 'categoria_ids', 'Modulos')
    
    
   # planes_id = fields.One2many('rocket_instancias.res.instancias',
     #                          inverse_name="planes_id.planes_ids", string="Planes de pago")
     
    total = fields.Monetary(string="Total", readonly=True, compute="_compute_total",currency_field="currency_id",store=True)
     
   # pdf_report = fields.Binary(string="Informe PDF", readonly=True)
   # pdf_report_filename = fields.Char(string="Nombre de archivo PDF", readonly=True)
     
    @api.depends('start_date','duration')
    def _compute_end_date(self):
        for record in self:
            if not (record.start_date and record.duration):
                record.end_date = record.start_date
            else:
                duration  = timedelta(days=record.duration)
                record.end_date = record.start_date + duration
                
    def _inverse_end_date(self):
        for record in self:
            if record.start_date and record.end_date:
                record.duration = (record.end_date - record.start_date).days + 1
            else:
                continue
            
    @api.depends('precio')
    def _compute_total(self):
        for record in self:
            if record.precio < 0.0:
                raise UserError("El precio no puede ser negativo")
            
            record.total = record.precio
            
    #@api.model
    #def create(self, values):
    #    if 'precio' in values:
    #        if values['precio'] < 0.0:
     #           raise UserError("El precio no puede ser negativo")
      #      
       #     values['total'] = values['precio']
#
 #       return super(rocket_planes, self).create(values)
   # @api.depends('precio')
    #def _compute_precio(self):
     #   for record in self:
     #       record.precio_formart = "$ %.2f" % (record.precio or 0.0)
     
     
    
    
    
   
    def generate_pdf_report(self):
        # Obtener todos los registros de la clase rocket_planes
        planes = self.env['plan.saas'].search([])

        # Comprobar si existen registros para generar el informe
        if not planes:
            raise UserError("No hay registros para generar el informe PDF.")

        # Obtener los datos de la compañía
        company = self.env.company
        company_name = company.name
        company_street = company.street
        company_city = company.city
        company_state = company.state_id.name if company.state_id else ''
        company_zip = company.zip
        company_country = company.country_id.name if company.country_id else ''
        company_email = company.email
        company_phone = company.phone
        company_logo = company.logo

        # Crear el objeto BytesIO para almacenar el PDF generado
        pdf_buffer = BytesIO()

        # Crear el documento PDF en modo retrato (vertical)
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )

        # Lista para almacenar los elementos del informe
        elements = []

        # Agregar el logo de la compañía al documento si existe
        if company_logo:
            logo_image = Image(BytesIO(base64.b64decode(company_logo)))
            logo_image.drawHeight = 100  # Ajustar el tamaño de la imagen según tus preferencias
            logo_image.drawWidth = 100   # Ajustar el tamaño de la imagen según tus preferencias

            # Crear un objeto Drawing para el enmascaramiento circular
           # logo_drawing = Drawing(100, 100)
           # logo_drawing.add(logo_image)

            # Aplicar el enmascaramiento circular al logo
            #logo_drawing.translate(10, 10)
            #logo_drawing._addClipPath('clip-circle', [(50, 50, 50)])

            # Agregar el logo enmascarado al documento
            elements.append(logo_image)


        # Crear el estilo para los datos de la compañía
        style_company = ParagraphStyle(
            'company',
            fontSize=10,
            textColor=colors.black,
            spaceAfter=6,
        )

        # Agregar los datos de la compañía al documento
        elements.append(Paragraph(company_name, style_company))
        elements.append(Paragraph(company_street, style_company))
        elements.append(Paragraph(f"{company_city}, {company_state} {company_zip}", style_company))
        elements.append(Paragraph(company_country, style_company))
        elements.append(Paragraph(f"Email: {company_email}", style_company))
        elements.append(Paragraph(f"Teléfono: {company_phone}", style_company))
        elements.append(Spacer(1, 12))  # Espacio entre los datos de la compañía y la tabla

        # Lista para almacenar los datos del informe (tabla)
        report_data = []

        # Seleccionar los campos que deseas incluir en la tabla del informe
        fields_to_include = ['name', 'precio', 'descripcion', 'start_date', 'duration', 'end_date']

        # Agregar los nombres de los campos seleccionados como encabezados de la tabla
        headers = [self.fields_get()[field]['string'] for field in fields_to_include]
        report_data.append(headers)

        # Recopilar los datos de los registros y agregarlos a la tabla
        for plan in planes:
            row_data = []
            for field in fields_to_include:
                field_type = self.fields_get()[field]['type']
                if field_type == 'many2one':
                    value = plan[field].name if plan[field] else ''
                else:
                    value = plan[field]
                row_data.append(value)
            report_data.append(row_data)

        # Crear la tabla para el informe
        table = Table(report_data)

        # Estilo de la tabla
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.black),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ])

        # Aplicar el estilo a la tabla
        table.setStyle(style)

        # Agregar los datos de la tabla al documento
        elements.append(table)

        # Generar el PDF
        doc.build(elements)

        # Obtener los bytes del PDF generado
        pdf_bytes = pdf_buffer.getvalue()

        # Cerrar el objeto BytesIO
        pdf_buffer.close()

        # Codificar el archivo PDF en base64
        pdf_base64 = base64.b64encode(pdf_bytes)

        # Obtener el valor del campo 'name' del primer registro (puedes ajustar esto según tus necesidades)
       # report_name = planes[0].name if planes[0].name else 'InformePDF'

        # Crear un registro para el archivo PDF
        pdf_file = self.env['ir.attachment'].create({
            'name':self._name + '.pdf',
            'type': 'binary',
            'datas': pdf_base64,
            'res_model': self._name,
            'res_id': 0,
        })

        # Redirigir a la descarga del archivo PDF
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % pdf_file.id,
            'target': 'self',
        }
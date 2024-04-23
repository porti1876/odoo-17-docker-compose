# -*- coding: utf-8 -*-
from odoo import fields, models, tools, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @tools.ormcache()
    def _get_default_cat_medida_id(self):
        default_unidad_medida = self.env['catalogo.unidad.medida'].search([('descripcion', '=', 'Unidad')], limit=1)
        return default_unidad_medida

    cat_unidad_medida = fields.Many2one('catalogo.unidad.medida', string='Unidad de medida DTE',
                                        default=_get_default_cat_medida_id, required=True)
    clave_producto = fields.Char(string='Clave producto')
    objetoimp = fields.Selection(
        selection=[('01', 'No objeto de impuesto'),
                   ('02', 'Sí objeto de impuesto'),
                   ('03', 'Sí objeto del impuesto y no obligado al desglose'),
                   ('04', 'Si objeto del impuesto y no causa impuesto'), ],
        string=_('Impuestos'), default='02',
    )
    type_item_edi = fields.Selection(string="Tipo de item", help="Tipo de item relacionado a facturas electrónicas",
                                     selection=[
                                         ('1', 'Bienes'),
                                         ('2', 'Servicios'),
                                         ('3',
                                          'Ambos (Bienes y Servicios, incluye los dos inherente a los productos o servicios)'),
                                         ('4', 'Otros tributos por ítem')
                                     ], default='1'
                                     )
    
    anho=fields.Integer(string="Vida útil", default=0, help= "años de vida util, solo aplica para un producto de tipo de bien o bienes usados")
    
    valor_residual = fields.Float(string="Valor residual", help='calcular: precio unitario(deprecion anual / años de vida util)')

    tributo_iva = fields.Selection(
        selection=[('A8', 'Impuesto especial al combustible'),
                   ('57', 'Impuesto industria de cemento'),
                   ('90', 'Impuesto especial a la primera matricula'),
                   ('D4', 'Otros impuestos casos especiales'),
                   ('D5', 'Otras tasas casos especiales'),
                   ('A6', 'Impuesto ad- valorem, armas de fuego, municiones explosivas y artículos similares'), ],
        string=_('Tributo sujeto a cálculo de IVA')
    )

    
   
   
   # @api.onchange('list_price', 'anho')
   # def onchange_valor_residual(self):
   # 
   #     depreciacion_anual = (self.list_price - self.valor_residual) / self.anho
   #     
   #     if self.list_price and self.anho:
   #         if self.anho ==0:
   #             depreciacion_anual=0
   #         else:
   #             self.valor_residual = self.list_price - (depreciacion_anual / self.anhol)
   #     else:
   #        self.valor_residual = 0
    
    
   
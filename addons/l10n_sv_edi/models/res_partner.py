# -*- coding: utf-8 -*-


from odoo import fields, models, _, api
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    residencia_fiscal = fields.Char(string=_('Residencia Fiscal'))
    registro_tributario = fields.Char(string=_('Registro tributario'))
    # uso_cfdi_id  =  fields.Many2one('catalogo.uso.cfdi', string='Uso CFDI (cliente)')
    recinto_fiscal_id  =  fields.Many2one('catalogo.recinto.fiscal', string='Recinto Fiscal')
    regimen_fiscal_id  =  fields.Many2one('res.regimen', string='Régimen Fiscal')
    
    tipo_persona=fields.Selection(selection=[('01', 'Persona Natural'), ('02','Persona juridica')],
                                 string="Tipo de persona", readonly=True)
    
    country_dte_id = fields.Many2one('res.country.edi', string='País Factura DTE')
    
    
    domicilio_fiscal = fields.Selection(selection=[('01','Domiciliado'),
                                                   ('02','No Domiciliado')],
                                   string="Domicilio Fiscal")

    codigo_pais = fields.Many2one('res.country.edi', string='Código de pais')
    
    # move_ids=fields.Many2one('account.move',string="counter")
    
    #counter_firmas=fields.Integer(related='move_ids.counter_firmas', string="Total de firmas")
    
    
    @api.onchange('company_type')
    def onchange_field(self):
       if self.company_type == 'person':
           self.tipo_persona = '01'
       elif self.company_type == 'company':
           self.tipo_persona = '02'
           
    # @api.model
    # def _res_partner_regimen(self):
    #     for record in self:
    #         if record.is_company == True:
    #             record.regimen_fiscal_id.ref = ''
    
   
              
    # RELACIONAR CAMPOS 
   # tipo = fields.Many2one('res.partner',string="tipo")
   # recuperar_type = fields.Char("Type", related='tipo.type') 
    
    #
    # @api.constrains('vat', 'country_id')
    # def check_vat(self):
    #     # The context key 'no_vat_validation' allows you to store/set a VAT number without doing validations.
    #     # This is for API pushes from external platforms where you have no control over VAT numbers.
    #     if self.env.context.get('no_vat_validation'):
    #         return
    #
    #     for partner in self:
    #         country = self.env['res.country'].search([('code', '=', 'MX')])
    #         if partner.vat and self._run_vat_test(partner.vat, country, partner.is_company) is False:
    #             partner_label = _("partner [%s]", partner.name)
    #             msg = partner._build_vat_error_message(country and country.code.lower() or None, partner.vat, partner_label)
    #             raise ValidationError(msg)
    
  #  contacto = fields.Many2one('res.partner',string="contactos")
  #  recuperar_contacto = fields.Char("Contactos", related='contacto.contact')       
  
    #@api.onchange('es_empresa')
    #def onchange_tipo(self):
     #   if self.persona_juridica == self.es_empresa:
      #      self.persona_juridica = True
       #     if self.persona_juridica != self.es_empresa:
        #        self.persona_juridica = False
       # elif self.persona_natural != self.es_empresa:
       #     self.persona_natural = True
        #if self.persona_natural != self.es_empresa:
        #        self.persona_juridica = False
       
        
           
    #@api.constrains('vat', 'country_id')
    #def check_vat(self):
        # The context key 'no_vat_validation' allows you to store/set a VAT number without doing validations.
        # This is for API pushes from external platforms where you have no control over VAT numbers.
     #   if self.env.context.get('no_vat_validation'):
      #      return

       # for partner in self:
        #    country = self.env['res.country'].search([('code', '=', 'MX')])
         #   if partner.vat and self._run_vat_test(partner.vat, country, partner.is_company) is False:
          #      partner_label = _("partner [%s]", partner.name)
           #     msg = partner._build_vat_error_message(country and country.code.lower() or None, partner.vat, partner_label)
            #    raise ValidationError(msg)

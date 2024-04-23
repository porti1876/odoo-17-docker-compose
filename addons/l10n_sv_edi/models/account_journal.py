# -*- coding: utf-8 -*-

from odoo import fields, models, _
import pytz

# put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
_tzs = [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]


def _tz_get(self):
    return _tzs


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    forma_pago_id = fields.Many2one('catalogo.forma.pago', string='Forma de pago')
    codigo_postal = fields.Char("Código Postal")
    tz = fields.Selection(_tz_get, string='Zona horaria', default=lambda self: self._context.get('tz'))
    serie_diario = fields.Char("Serie")
    document_type_sv = fields.Selection(string="Tipo de documento", selection=[
        ('01', 'Factura'),
        ('03', 'Comprobante de crédito fiscal'),
        ('04', 'Nota de remisión'),
        ('05', 'Nota de crédito'),
        ('06', 'Nota de débito'),
        ('07', 'Comprobante de retención'),
        ('08', 'Comprobante de liquidación'),
        ('09', 'Documento contable de liquidación'),
        ('11', 'Factura de exportación'),
        ('14', 'Factura de sujeto excluído'),
        ('15', 'Comprobante de donación')
    ])
    is_document_electronic = fields.Boolean(string="Es un diario de DTE", default=False)
    version = fields.Integer(string="Versión del documento DTE")
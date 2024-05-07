from odoo import models, fields, api

class AccountGroup(models.Model):
    _inherit = 'account.group'

    is_general_ledger_account_group = fields.Boolean(string='¿Es cuenta de mayor?', default=True)






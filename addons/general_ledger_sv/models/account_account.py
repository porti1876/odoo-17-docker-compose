from odoo import models, fields, api


class AccountAccountGl(models.Model):
    _inherit = 'account.account'

    parent_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Cuenta Padre",
        domain="[('code', 'like', code)]"
    )

    parent_accounts = fields.Many2many(
        comodel_name='account.account',
        relation='account_account_parent_rel',
        column1='child_id',
        column2='parent_id',
        string="Cuentas hijas",
    )

    is_result_account = fields.Boolean(string="¿Es cuenta de resultado?",
                                       help="Para efectos de libro mayor, "
                                            "especificar si la cuenta se calculará el saldo inicial desde el año fiscal")

    @api.depends('parent_account_id')
    def _compute_parent_accounts(self):
        for account in self:
            account.parent_accounts = [(6, 0, account.parent_account_id.ids)]

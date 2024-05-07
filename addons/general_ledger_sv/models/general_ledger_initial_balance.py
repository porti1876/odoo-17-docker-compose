from datetime import datetime

from odoo import models, fields, api

class AccountInitialBalance(models.Model):
    _name = 'general.ledger.initial.balance'
    _description = 'Initial Balance per Account'

    ledger_id = fields.Many2one(
        'general.ledger.sv',
        string='Libro mayor relacionado',
        ondelete='cascade'
    )
    account_id = fields.Many2one(
        'account.account',
        string='Cuenta contable',
        required=True
    )
    initial_balance = fields.Monetary(
        compute='_compute_initial_balance',
        string='Balance Inicial',
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='ledger_id.company_id.currency_id',
        readonly=True,
        help="Currency used for the monetary fields in this model."
    )
    is_result_account = fields.Boolean(
        related='account_id.is_result_account',
        store=True,
        readonly=True
    )

    @api.depends('ledger_id.date_from', 'account_id', 'is_result_account')
    def _compute_initial_balance(self):
        company = self.env.user.company_id
        fiscal_year_start = datetime(int(company.fiscalyear_last_day) + 1,
                                     int(company.fiscalyear_last_month), 1)
        for record in self:
            if record.ledger_id.date_from:
                date_from = fiscal_year_start if record.is_result_account else record.ledger_id.date_from
                domain = [
                    ('account_id', '=', record.account_id.id),
                    ('date', '<', date_from),
                    ('move_id.state', '=', 'posted'),
                    ('company_id', '=', record.ledger_id.company_id.id)
                ]
                lines = self.env['account.move.line'].search(domain)
                record.initial_balance = sum(line.balance for line in lines)
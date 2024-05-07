from odoo import models, fields, api
from psycopg2 import sql



from datetime import datetime
from dateutil.relativedelta import relativedelta


class AccountMoveLine(models.AbstractModel):
    _inherit = 'account.move.line'

    account_group_id = fields.Many2one(related="account_id.group_id", string="Grupo de la cuenta", store=True)

    initial_balance = fields.Float(
        compute='_compute_initial_balance',
        string='Balance Inicial',
        store=False,
    )

    @api.depends('date', 'move_id.state', 'account_id', 'company_id')
    def _compute_initial_balance(self):
        for line in self:
            date_from = line._get_related_date_from()

            # Asegúrate de que solo calculas esto para líneas con fecha anterior a date_from
            if line.date < date_from:
                domain = [
                    ('account_id', '=', line.account_id.id),
                    ('date', '<', date_from),
                    ('move_id.state', '=', 'posted'),
                    ('company_id', '=', line.company_id.id),
                ]
                # Sumar todos los balances de las líneas anteriores a date_from
                previous_lines = self.search(domain)
                line.initial_balance = sum(previous_lines.mapped('balance'))
            else:
                line.initial_balance = 0

    def _get_related_date_from(self):
        return self.env.context.get('ledger_date_from', fields.Date.today())


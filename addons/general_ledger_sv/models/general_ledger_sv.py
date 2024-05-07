from collections import defaultdict

from odoo import fields, models, api
from odoo.exceptions import ValidationError, UserError


class GeneralLedger(models.Model):
    _name = 'general.ledger.sv'
    _description = 'Libro Mayor de El Salvador'
    _rec_name = 'name'

    name = fields.Char(string="Nombre de libro mayor", required=True)
    date_from = fields.Date(string="Fecha de inicio", required=True,
                            default=lambda self: fields.Date.context_today(self))
    date_to = fields.Date(string="Fecha final", required=True, default=lambda self: fields.Date.context_today(self))
    company_id = fields.Many2one('res.company', string="Compañia", default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Moneda")
    journal_ids = fields.Many2many(
        'account.journal',
        string="Diarios",
        required=True,
    )
    account_group_ids = fields.Many2many('account.group', string="Grupos de cuenta",
                                         help="Funciona como cuentas de mayor",
                                         domain=[('is_general_ledger_account_group', '=', True)])
    account_ids = fields.Many2many('account.account', string="Cuentas contables")
    show_initial_balance = fields.Boolean(string="Mostrar Saldo Inicial", default=True)
    show_final_balance = fields.Boolean(string="Mostrar Saldo Final", default=True)
    state = fields.Selection(string="Estado",
                             selection=[('draft', 'Borrador'), ('confirmed', 'Confirmado'),
                                        ('done', 'Validado')], default='draft')
    is_account_group_ids = fields.Boolean("¿Utilizar grupos de cuenta como cuentas de mayor?")
    move_line_ids = fields.One2many(
        'account.move.line',
        compute='_compute_move_lines',
        string='Movimientos Contables',
    )
    account_balances = fields.One2many(
        'general.ledger.initial.balance',
        'ledger_id',
        string='Saldos Iniciales',
        store=True
    )
    is_journals_selection = fields.Boolean(string="¿Definir por diarios?", default=False)

    # Usar metodo 'default_get' en lugar de usar default en el campo ya que se inicializa en el form es mas optimo con ORM
    @api.model
    def default_get(self, fields_list):
        res = super(GeneralLedger, self).default_get(fields_list)
        journal_ids = self.env['account.journal'].search([]).ids
        res['journal_ids'] = [(6, 0, journal_ids)]
        return res


    @api.depends('date_from', 'date_to', 'journal_ids', 'is_account_group_ids')
    def _compute_move_lines(self):
        for record in self:
            if record.date_from and record.date_to:
                domain = [
                    ('date', '>=', record.date_from),
                    ('date', '<=', record.date_to),
                    ('move_id.state', '=', 'posted'),
                    ('company_id', '=', record.company_id.id),
                    ('journal_id', 'in', record.journal_ids.ids),
                    ('display_type', 'not in', ['line_section', 'line_note']) # No aplica notas y secciones
                ]
                # Ordenar por account_group_id si is_account_group_ids es True, de lo contrario por group_id
                order = 'account_group_id, account_id, date, id' if record.is_account_group_ids else 'account_id, date, id'
                record.move_line_ids = self.env['account.move.line'].search(domain, order=order)
            else:
                record.move_line_ids = self.env['account.move.line']

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for record in self:
            if record.date_to < record.date_from:
                raise ValidationError("La fecha de finalización debe ser igual o posterior a la fecha de inicio.")

    def confirm_ledger(self):
        for ledger in self:
            if ledger.state != 'draft':
                raise UserError("Solo se pueden confirmar registros en estado de borrador.")
            ledger.state = 'confirmed'

    def print_report(self):
        """
        Genera la acción para imprimir el reporte
        """
        self.ensure_one()
        self.calculate_initial_balances()
        report_template = 'general_ledger_sv.action_report_general_ledger_sv_ex_upt'
        return self.env.ref(report_template).report_action(self)

    def approve_general_ledger(self):
        for record in self:
            # Asegúrate de que el estado actual permita la transición a 'done'
            if record.state not in ['done']:
                record.write({'state': 'done'})

    def calculate_initial_balances(self):
        AccountInitialBalance = self.env['general.ledger.initial.balance']
        Account = self.env['account.account']
        AccountMoveLine = self.env['account.move.line']

        for ledger in self:
            # Obtener todas las cuentas con movimientos o con saldo inicial distinto de cero
            accounts_domain = [
                ('move_id.state', '=', 'posted'),
                ('company_id', '=', ledger.company_id.id),
                '|', '|',
                ('date', '<', ledger.date_from),
                ('debit', '>', 0),
                ('credit', '>', 0)
            ]
            all_account_ids = AccountMoveLine.search(accounts_domain).mapped('account_id')

            # Filtrar cuentas para incluir solo las que tengan movimientos antes de la fecha especificada
            relevant_accounts = all_account_ids.filtered(lambda a: AccountMoveLine.search([
                ('account_id', '=', a.id),
                ('date', '<', ledger.date_from),
                ('move_id.state', '=', 'posted')
            ]))

            # Ordenar las cuentas por código
            relevant_accounts_sorted = relevant_accounts.sorted(key=lambda r: r.code)

            # Eliminar balances que no corresponden a las cuentas identificadas
            ledger.account_balances.filtered(lambda r: r.account_id not in relevant_accounts_sorted).unlink()

            # Crear o actualizar balances para las cuentas identificadas
            for account in relevant_accounts_sorted:
                balance = AccountInitialBalance.search([
                    ('ledger_id', '=', ledger.id),
                    ('account_id', '=', account.id),
                ], limit=1)

                if balance:
                    # Actualizar el saldo inicial si ya existe
                    balance._compute_initial_balance()
                else:
                    # Crear un nuevo registro si la cuenta es nueva
                    AccountInitialBalance.create({
                        'ledger_id': ledger.id,
                        'account_id': account.id,
                        # Si la cuenta no tiene saldo inicial y no está en move_line_ids, el saldo inicial es cero
                        'initial_balance': 0 if account not in ledger.move_line_ids.mapped('account_id') else None,
                    })

            # Recalcular saldos para todos los balances existentes
            ledger.account_balances._compute_initial_balance()

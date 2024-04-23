from odoo import fields, models, api, _


class AccountMoveContacts(models.Model):
    _inherit = 'account.move.line'

    move_type_ids = fields.Selection(
        string="(Gravadas/Exentas/No Sujetas)",
        selection=[('nosujetas','Ventas no sujetas'), ('gravadas', 'Gravadas'), ('exentas', 'Exentas')],
        default='gravadas'
    )


    # user_move_type_ids = fields.Selection(
    #     string="(Gravadas/Exentas)",
    #     selection=[('gravadas', 'Gravadas'), ('exentas', 'Exentas')],
    #     default='gravadas'
    # )
    #
    # @api.depends('partner_id', 'user_move_type_ids')
    # def _compute_move_type_ids(self):
    #     for move in self:
    #         if move.partner_id.country_id.code != 'SV':
    #             move.move_type_ids = 'exentas'
    #         else:
    #             move.move_type_ids = move.user_move_type_ids

    # @api.depends('move_id.invoice_line_ids.price_subtotal', 'move_id.invoice_line_ids.move_type_ids')
    # def _compute_compras_exentas(self):
    #     for move_line in self:
    #         move = move_line.move_id
    #         exentas_lines = move.invoice_line_ids.filtered(lambda line: line.move_type_ids == 'exentas')
    #         partner_country = move.partner_id.country_id
    #         if partner_country == move.env.ref('base.sv'):
    #             move.compras_exentas_internas = sum(exentas_lines.mapped('price_subtotal'))
    #         elif partner_country in move.env.ref('base.pa') + move.env.ref('base.cr') + move.env.ref(
    #                 'base.gt') + move.env.ref('base.hn') + move.env.ref('base.ni'):
    #             move.compras_exentas_internacional = sum(exentas_lines.mapped('price_subtotal'))
    #         else:
    #             move.compras_exentas_importacion = sum(exentas_lines.mapped('price_subtotal'))

    # @api.depends('move_id.invoice_line_ids.price_subtotal', 'move_id.invoice_line_ids.move_type_ids')
    # def _compute_compras_gravadas_internas(self):
    #     for move_line in self:
    #         move = move_line.move_id
    #         gravadas_lines: account.move.line = move.invoice_line_ids.filtered(lambda line: line.move_type_ids == 'gravadas')
    #         partner_country = move.partner_id.country_id
    #         if partner_country == move.env.ref('base.sv'):
    #             move.compras_gravadas_internas = sum(gravadas_lines.mapped('price_subtotal'))
    #         elif partner_country in move.env.ref('base.pa') + move.env.ref('base.cr') + move.env.ref(
    #                 'base.gt') + move.env.ref('base.hn') + move.env.ref('base.ni'):
    #             move.compras_gravadas_importacion = sum(gravadas_lines.mapped('price_subtotal'))
    #         else:
    #             move.compras_gravadas_internacionales = sum(gravadas_lines.mapped('price_subtotal'))




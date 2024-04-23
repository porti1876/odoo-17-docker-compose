# -*- coding: utf-8 -*-
# from odoo import http


# class Ln10SvSaas(http.Controller):
#     @http.route('/ln10_sv_saas/ln10_sv_saas', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ln10_sv_saas/ln10_sv_saas/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ln10_sv_saas.listing', {
#             'root': '/ln10_sv_saas/ln10_sv_saas',
#             'objects': http.request.env['ln10_sv_saas.ln10_sv_saas'].search([]),
#         })

#     @http.route('/ln10_sv_saas/ln10_sv_saas/objects/<model("ln10_sv_saas.ln10_sv_saas"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ln10_sv_saas.object', {
#             'object': obj
#         })

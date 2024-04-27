# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Formato DTE Custom',
    'version': '16.0.0.2',
    'category': 'Tools',
    'summary': 'Módulo para generar formato de las facturas electronica en formato pdf',
    'description': """
    Permite configurar el formato de reporte de PDF de factura electronica de acuerdo a necesidades de cliente
    """,
    'license': 'OPL-1',
    'author': 'Kevin Portillo',
    'website': 'https://portipy.vercel.app/',
    'depends': ['base', 'account', 'sale', 'stock', 'sale_management', 'l10n_sv_rk'],
    'data': [
        "res_company.xml",
        "invoice_report/fency_report_invoice.xml",
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}

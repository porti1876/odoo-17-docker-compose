# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Formato DTE Custom',
    'version': '16.0.0.2',
    'category': 'Tools',
    'summary': 'Módulo para generar formato de las facturas electronica en formato pdf',
    'description': """
		Customize report, customize pdf report, customize template report, Customize Sales Order report,Customize Purchase Order report, Customize invoice report, Customize delivery Order report, Accounting Reports, Easy reports, Flexible report,Fancy Report template
    """,
    'license': 'OPL-1',
    'author': 'Rocketters',
    'website': 'https://www.browseinfo.in',
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

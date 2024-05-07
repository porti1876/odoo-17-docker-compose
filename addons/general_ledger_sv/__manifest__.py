# -*- coding: utf-8 -*-
{
    'name': "Libro Mayor SV",

    'summary': """
    Libro mayor de El Salvador
    """,

    'description': """
        Libro mayor de El Salvador
    """,

    'author': "Kevin Portillo",
    'website': 'https://github.com/porti1876',
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'account',
    'version': '16.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/account_group.xml',
        'views/general_ledger_sv_view.xml',
        'report/general_ledger_report.xml',
        'views/account_account.xml'
    ],


}


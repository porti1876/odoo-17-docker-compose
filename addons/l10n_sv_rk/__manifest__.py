# -*- coding: utf-8 -*-
{
    'name': "Localization SV Rocketters",

    'summary': """
       """,

    'description': """
    Modulo para automatizar contabilidad de El Salvador .
    """,

    'author': "Kevin Portillo",
    'website': "https://portipy.vercel.app/",

    'category': 'Accounting/Localizations/Account Charts',
    'version': '1',
    'license': 'LGPL-3',
    'summary': 'En este modulo se puede automatizar el apartado de reportes y facturas agregando nuevos campos relevantes.',

    # any module necessary for this one to work correctly
    'depends': ['account', 'base', 'contacts', 'hr', 'sale','stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/res.country.state.csv',
        # 'data/account_tax_group.xml',
        # 'data/account_tax.xml',
        # "views/account_move_view.xml",
        'views/res_municipality.xml',
        'views/hr_employee_view.xml',
        'views/res_partner_sv.xml',
        'views/res_giro.xml',
        # 'views/account_incoterms_view.xml',
        'views/res_company_view.xml',
       # 'views/catalogo_fiscal.xml',
        'views/res_regimen_view.xml',
        'data/res.municipality.csv',
        'data/res.giro.csv',
        # 'data/catalogo.incoterms.csv',
        'data/res.regimen.csv',
        #'views/res_parnet_cdfi.xml',
        # 'data/l10n_sv_chart_data.xml',
        #  'data/l10n_sv_chart_post_data.xml',
        # 'data/account_data.xml',
        # 'data/account_tax_data.xml',
        # 'data/account_fiscal_position.xml',
        # 'data/account_chart_template_data.xml',
        # 'data/sequence_data.xml',
        # 'data/account.account.template.csv',

    ],
    # only loaded in demonstration mode
}

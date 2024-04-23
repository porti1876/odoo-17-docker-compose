{
    'name': 'Modulo de factura electrónica El Salvador',
    'version': '16.01',
    'description': ''' Factura Electronica módulo de ventas, compras y contabilidad para El Salvador (DGII & Ministerio de Hacienda)
    ''',
    'category': 'Accounting', 'Sale'
                              'author': 'Rocketters',
    'website': 'https://rocketters.com/',
    'depends': [
        'sale', 'account', 'l10n_sv_rk', 'base','contacts'
    ],
    'data': [

        'security/ir.model.access.csv',

        # Views de wizards
        'wizard/import_account_payment_view.xml',
        'wizard/reason_cancelation_sat_view.xml',
        
        # Información Data De Catalogos

        'data/catalogo.recinto.fiscal.csv',
        'data/catalogo.unidad.medida.csv',
        'data/catalogo.forma.pago.csv',
        # 'data/catalogo.uso.cfdi.csv',
        'data/tribute.edi.csv',
        'data/sequence_data.xml',
        'data/journal_data.xml',
        'data/catalogo.incoterms.csv',
        'data/ir_sequence.xml',
        'data/account_tax_group.xml',
        'data/account_tax.xml',
        'data/res.country.edi.csv',
        'data/account_tax_group.xml',
        'data/mail_template_data_dte.xml',
        'data/cron.xml',


        # Views
        'views/res_country_edi_view.xml',
        'views/account_incoterms_view.xml',
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        'views/product_view.xml',
        'views/account_invoice_view.xml',
        'views/account_move_view.xml',
        'views/account_tax_view.xml',
        'views/tribute_edi_view.xml',
        'views/account_payment_term_view.xml',
        'views/account_journal_view.xml',



    ],
    'images': ['static/description/rocket_img'],
    'application': False,
    'installable': True,
    'price': 0.00,
    'currency': 'USD',
    'license': 'LGPL-3',

}

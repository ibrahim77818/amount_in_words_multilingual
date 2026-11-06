# -*- coding: utf-8 -*-
{
    'name': 'Amount in Words (English & Arabic)',
    'version': '16.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Total in words on Sales Orders and Customer Invoices, in the '
               'customer\'s language, with grammatically correct Arabic',
    'description': """
Amount in Words - Multilingual
==============================
* "Total (In Words)" on Sale Orders and Customer Invoices / Credit Notes.
* Language resolved from the customer's profile (English, Arabic, or any
  other installed language through Odoo's native engine).
* Native Arabic engine: gender agreement, dual, plural and accusative
  counted-noun forms, construct state (مائتا / ألفا).
* Per-currency singular/plural/dual wording, editable on the currency form,
  pre-filled for 26 common currencies (SAR, AED, KWD, USD, EUR ...).
* Recomputes live as lines, discounts, taxes and cash rounding change.
* Printed on the standard Quotation / Order and Invoice PDF reports with RTL
  alignment.
""",
    'author': 'Ibrahim Yahia',
    'website': 'https://www.linkedin.com/in/ibrahim-yahia',
    'license': 'LGPL-3',
    'depends': ['sale', 'account'],
    'data': [
        'views/res_currency_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'report/report_templates.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}

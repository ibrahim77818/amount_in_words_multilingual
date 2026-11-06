# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Not required=True on purpose: a DB-level NOT NULL would break company
    # creation in upstream modules' at_install tests (partial registry).
    # An empty value behaves as "Customer's Language".
    amount_words_lang_mode = fields.Selection(
        [('partner', "Customer's Language"),
         ('en', 'Always English'),
         ('ar', 'Always Arabic')],
        string='Amount in Words Language', default='partner')
    amount_words_wrap = fields.Boolean(
        'Wrap with "Only" / "فقط ... لا غير"', default=True,
        help='Adds "... Only" in English and "فقط ... لا غير" in Arabic so the amount '
             'cannot be altered after printing.')
    amount_words_on_sale_report = fields.Boolean('Print on Quotations / Orders', default=True)
    amount_words_on_invoice_report = fields.Boolean('Print on Customer Invoices', default=True)

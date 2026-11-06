# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'amount.words.mixin']

    # Odoo 17 ships its own ``amount_total_words`` on account.move (printed by
    # the "Total amount of invoice in letters" setting and by l10n_gcc_invoice).
    # We keep the same field name and replace its computation, so every place
    # that prints it gets the multilingual, grammatically correct text.
    amount_total_words = fields.Char(
        string='Total (In Words)', compute='_compute_amount_total_words',
        help="Document total spelled out in the customer's language.")

    @api.depends(
        # totals
        'amount_untaxed', 'amount_tax', 'amount_total',
        # every journal item (product, tax, cash-rounding and epd lines)
        'line_ids.balance', 'line_ids.amount_currency', 'line_ids.display_type',
        # line-level pricing
        'invoice_line_ids.quantity', 'invoice_line_ids.price_unit',
        'invoice_line_ids.discount', 'invoice_line_ids.tax_ids',
        'invoice_line_ids.price_subtotal', 'invoice_line_ids.price_total',
        # the totals widget / printed totals (incl. cash rounding), live in the form
        'tax_totals',
        # cash rounding, document type, currency, language
        'invoice_cash_rounding_id', 'move_type',
        'currency_id', 'partner_id', 'partner_id.lang', 'company_id',
        'company_id.amount_words_lang_mode', 'company_id.amount_words_wrap',
    )
    def _compute_amount_total_words(self):
        self._amount_words_compute()

    def _amount_words_get_amount(self):
        self.ensure_one()
        if not self.is_invoice(include_receipts=True):
            return None
        # ``tax_totals`` is what the totals widget and the PDF display: it is
        # recomputed live from the invoice lines in the form (before journal
        # items are synchronised). In Odoo 17 its ``amount_total`` already
        # includes the cash-rounding difference (both strategies).
        totals = self.tax_totals
        if totals and totals.get('amount_total') is not None:
            return totals['amount_total']
        return self.amount_total

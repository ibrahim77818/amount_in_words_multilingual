# -*- coding: utf-8 -*-
from odoo import api, models


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'amount.words.mixin']

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
        return super()._compute_amount_total_words()

    def _amount_words_get_amount(self):
        self.ensure_one()
        if not self.is_invoice(include_receipts=True):
            return None
        # ``tax_totals`` is what the totals widget and the PDF display: it is
        # recomputed live from the invoice lines in the form (before journal
        # items are synchronised) and carries the cash-rounded grand total.
        totals = self.tax_totals
        if totals and totals.get('amount_total') is not None:
            return totals.get('amount_total_rounded', totals['amount_total'])
        return self.amount_total

# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AmountWordsMixin(models.AbstractModel):
    """Shared "Total (In Words)" behaviour for priced documents.

    Inheriting models implement :meth:`_amount_words_get_amount` and declare
    the full ``@api.depends`` list on their own ``_compute_amount_total_words``
    override, so the text refreshes whenever any pricing element changes.
    """
    _name = 'amount.words.mixin'
    _description = 'Amount in Words Mixin'

    amount_total_words = fields.Char(
        string='Total (In Words)', compute='_compute_amount_total_words',
        help="Document total spelled out in the customer's language.")
    amount_total_words_lang = fields.Char(
        string='Amount in Words Language', compute='_compute_amount_total_words')
    amount_total_words_rtl = fields.Boolean(
        string='Amount in Words is RTL', compute='_compute_amount_total_words')

    # --- hooks -----------------------------------------------------------
    def _amount_words_get_amount(self):
        """Return the amount to spell, or None when not applicable."""
        self.ensure_one()
        return self.amount_total

    def _amount_words_get_lang(self):
        self.ensure_one()
        company = self.company_id or self.env.company
        mode = company.amount_words_lang_mode or 'partner'
        if mode == 'en':
            return 'en_US'
        if mode == 'ar':
            installed = dict(self.env['res.lang'].get_installed())
            return next((code for code in ('ar_001', 'ar_SA') if code in installed), 'ar_001')
        return self.partner_id.lang or self.env.lang or 'en_US'

    # --- compute ---------------------------------------------------------
    def _compute_amount_total_words(self):
        Currency = self.env['res.currency']
        for record in self:
            amount = record._amount_words_get_amount()
            currency = record.currency_id or (record.company_id or self.env.company).currency_id
            if amount is None or not currency:
                record.amount_total_words = False
                record.amount_total_words_lang = False
                record.amount_total_words_rtl = False
                continue
            lang = record._amount_words_get_lang()
            company = record.company_id or self.env.company
            record.amount_total_words = currency.amount_to_words_multilingual(
                abs(amount), lang=lang, wrap=company.amount_words_wrap)
            record.amount_total_words_lang = lang
            record.amount_total_words_rtl = Currency._amount_words_is_rtl(lang)


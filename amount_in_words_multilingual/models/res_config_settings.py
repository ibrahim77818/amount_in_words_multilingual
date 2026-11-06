# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    amount_words_lang_mode = fields.Selection(
        related='company_id.amount_words_lang_mode', readonly=False)
    amount_words_wrap = fields.Boolean(related='company_id.amount_words_wrap', readonly=False)
    amount_words_on_sale_report = fields.Boolean(
        related='company_id.amount_words_on_sale_report', readonly=False)
    amount_words_on_invoice_report = fields.Boolean(
        related='company_id.amount_words_on_invoice_report', readonly=False)

# -*- coding: utf-8 -*-
from odoo import api, models


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'amount.words.mixin']

    @api.depends(
        # totals (themselves recomputed from the lines)
        'amount_untaxed', 'amount_tax', 'amount_total',
        # line-level pricing: quantity, unit price, discount, taxes
        # (Odoo 19 renamed sale.order.line.tax_id to tax_ids)
        'order_line.product_uom_qty', 'order_line.price_unit', 'order_line.discount',
        'order_line.tax_ids', 'order_line.price_subtotal', 'order_line.price_tax',
        'order_line.price_total',
        # global discount lines / currency / language
        'order_line.display_type',
        'currency_id', 'partner_id', 'partner_id.lang', 'company_id',
        'company_id.amount_words_lang_mode', 'company_id.amount_words_wrap',
    )
    def _compute_amount_total_words(self):
        self._amount_words_compute()

# -*- coding: utf-8 -*-
"""Total (In Words) on Sale Orders and Customer Invoices: language resolution,
taxes, discounts, cash rounding, live recomputation and PDF (QWeb) output."""
from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install', 'amount_in_words')
class TestAmountWordsDocuments(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        # Odoo 18: AccountTestInvoicingCommon.setUpClass() takes no
        # chart_template_ref any more (use @setup_chart_template instead).
        super().setUpClass()
        cls.env['res.lang']._activate_lang('ar_001')
        cls.company = cls.company_data['company']
        cls.company.write({
            'amount_words_lang_mode': 'partner',
            'amount_words_wrap': True,
            'amount_words_on_sale_report': True,
            'amount_words_on_invoice_report': True,
        })

        Currency = cls.env['res.currency'].with_context(active_test=False)
        cls.sar = Currency.search([('name', '=', 'SAR')])
        cls.kwd = Currency.search([('name', '=', 'KWD')])
        cls.usd = Currency.search([('name', '=', 'USD')])
        (cls.sar | cls.kwd | cls.usd).active = True

        cls.partner_en = cls.env['res.partner'].create({'name': 'Acme Ltd', 'lang': 'en_US'})
        cls.partner_ar = cls.env['res.partner'].create({'name': 'شركة الاختبار', 'lang': 'ar_001'})

        cls.tax_15 = cls.env['account.tax'].create({
            'name': 'VAT 15% (words test)', 'amount': 15.0, 'amount_type': 'percent',
            'type_tax_use': 'sale', 'company_id': cls.company.id,
        })
        cls.tax_15_incl = cls.env['account.tax'].create({
            'name': 'VAT 15% incl. (words test)', 'amount': 15.0, 'amount_type': 'percent',
            'type_tax_use': 'sale', 'price_include_override': 'tax_included', 'company_id': cls.company.id,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Consulting Hour', 'lst_price': 1000.0, 'type': 'service',
            'taxes_id': [Command.set(cls.tax_15.ids)],
        })
        cls.discount_product = cls.env['product.product'].create({
            'name': 'Global Discount', 'type': 'service', 'taxes_id': [Command.clear()],
        })
        cls.pricelist_sar = cls.env['product.pricelist'].create({
            'name': 'SAR Pricelist', 'currency_id': cls.sar.id, 'company_id': cls.company.id,
        })

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _create_so(self, partner, lines, pricelist=None):
        return self.env['sale.order'].create({
            'partner_id': partner.id,
            'pricelist_id': (pricelist or self.pricelist_sar).id,
            'company_id': self.company.id,
            'order_line': [Command.create({
                'product_id': (vals.get('product') or self.product).id,
                'product_uom_qty': vals.get('qty', 1.0),
                'price_unit': vals['price'],
                'discount': vals.get('discount', 0.0),
                'tax_id': [Command.set(vals.get('taxes', self.tax_15).ids)],
            }) for vals in lines],
        })

    def _create_invoice(self, partner, lines, currency=None, move_type='out_invoice', **extra):
        return self.env['account.move'].create({
            'move_type': move_type,
            'partner_id': partner.id,
            'invoice_date': '2026-01-15',
            'currency_id': (currency or self.sar).id,
            'invoice_line_ids': [Command.create({
                'product_id': (vals.get('product') or self.product).id,
                'quantity': vals.get('qty', 1.0),
                'price_unit': vals['price'],
                'discount': vals.get('discount', 0.0),
                'tax_ids': [Command.set(vals.get('taxes', self.tax_15).ids)],
            }) for vals in lines],
            **extra,
        })

    # ------------------------------------------------------------------
    # Sale orders
    # ------------------------------------------------------------------
    def test_so_language_follows_customer(self):
        so_en = self._create_so(self.partner_en, [{'price': 1000.0}])
        so_ar = self._create_so(self.partner_ar, [{'price': 1000.0}])
        self.assertEqual(so_en.currency_id, self.sar)
        self.assertAlmostEqual(so_en.amount_total, 1150.0)
        self.assertEqual(so_en.amount_total_words, 'One Thousand One Hundred and Fifty Saudi Riyals Only')
        self.assertFalse(so_en.amount_total_words_rtl)
        self.assertEqual(so_ar.amount_total_words, 'فقط ألف ومائة وخمسون ريالاً سعودياً لا غير')
        self.assertTrue(so_ar.amount_total_words_rtl)

    def test_so_line_discount_and_fractions(self):
        # 3 x 99.99 = 299.97, -10% = 269.973 -> 269.97 ; VAT 40.50 ; total 310.47
        so = self._create_so(self.partner_ar, [{'price': 99.99, 'qty': 3, 'discount': 10.0}])
        self.assertAlmostEqual(so.amount_total, 310.47)
        self.assertEqual(
            so.amount_total_words,
            'فقط ثلاثمائة وعشرة ريالات سعودية وسبع وأربعون هللة لا غير')

    def test_so_tax_included_price(self):
        so = self._create_so(self.partner_en, [{'price': 1150.0, 'taxes': self.tax_15_incl}])
        self.assertAlmostEqual(so.amount_untaxed, 1000.0)
        self.assertAlmostEqual(so.amount_total, 1150.0)
        self.assertEqual(so.amount_total_words, 'One Thousand One Hundred and Fifty Saudi Riyals Only')

    def test_so_global_discount_line(self):
        so = self._create_so(self.partner_en, [
            {'price': 1000.0},
            {'price': -100.0, 'product': self.discount_product, 'taxes': self.env['account.tax']},
        ])
        self.assertAlmostEqual(so.amount_total, 1050.0)
        self.assertEqual(so.amount_total_words, 'One Thousand and Fifty Saudi Riyals Only')

    def test_so_recomputes_on_every_pricing_change(self):
        so = self._create_so(self.partner_en, [{'price': 1000.0}])
        line = so.order_line
        line.discount = 10.0                    # 900 + 135
        self.assertEqual(so.amount_total_words, 'One Thousand and Thirty-Five Saudi Riyals Only')
        line.product_uom_qty = 2                # 1800 + 270
        self.assertEqual(so.amount_total_words, 'Two Thousand and Seventy Saudi Riyals Only')
        line.tax_id = [Command.clear()]         # 1800
        self.assertEqual(so.amount_total_words, 'One Thousand Eight Hundred Saudi Riyals Only')
        line.price_unit = 1                     # 2 x 1 x 90% = 1.80
        self.assertEqual(so.amount_total_words, 'One Saudi Riyal and Eighty Halalas Only')
        self.partner_en.lang = 'ar_001'         # language switch on the customer
        self.assertEqual(so.amount_total_words, 'فقط ريال سعودي واحد وثمانون هللة لا غير')

    def test_so_form_onchange_updates_words_live(self):
        self.env.user.groups_id += self.env.ref('sale.group_discount_per_so_line') \
            + self.env.ref('product.group_product_pricelist')
        with Form(self.env['sale.order']) as so_form:
            so_form.partner_id = self.partner_ar
            so_form.pricelist_id = self.pricelist_sar
            with so_form.order_line.new() as line:
                line.product_id = self.product
                line.price_unit = 100.0
                line.tax_id.clear()
                line.tax_id.add(self.tax_15)
            self.assertEqual(so_form.amount_total_words, 'فقط مائة وخمسة عشر ريالاً سعودياً لا غير')
            with so_form.order_line.edit(0) as line:
                line.discount = 50.0
            # 50 + 7.50
            self.assertEqual(so_form.amount_total_words,
                             'فقط سبعة وخمسون ريالاً سعودياً وخمسون هللة لا غير')

    def test_company_language_mode_and_wrap(self):
        so = self._create_so(self.partner_en, [{'price': 1000.0}])
        self.company.amount_words_lang_mode = 'ar'
        self.assertEqual(so.amount_total_words, 'فقط ألف ومائة وخمسون ريالاً سعودياً لا غير')
        self.company.amount_words_lang_mode = 'en'
        so_ar = self._create_so(self.partner_ar, [{'price': 1000.0}])
        self.assertEqual(so_ar.amount_total_words, 'One Thousand One Hundred and Fifty Saudi Riyals Only')
        self.company.amount_words_wrap = False
        self.assertEqual(so_ar.amount_total_words, 'One Thousand One Hundred and Fifty Saudi Riyals')

    # ------------------------------------------------------------------
    # Invoices
    # ------------------------------------------------------------------
    def test_invoice_language_and_taxes(self):
        inv_en = self._create_invoice(self.partner_en, [{'price': 1000.0}])
        inv_ar = self._create_invoice(self.partner_ar, [{'price': 1000.0}])
        self.assertAlmostEqual(inv_en.amount_total, 1150.0)
        self.assertEqual(inv_en.amount_total_words, 'One Thousand One Hundred and Fifty Saudi Riyals Only')
        self.assertEqual(inv_ar.amount_total_words, 'فقط ألف ومائة وخمسون ريالاً سعودياً لا غير')
        inv_ar.action_post()
        self.assertEqual(inv_ar.amount_total_words, 'فقط ألف ومائة وخمسون ريالاً سعودياً لا غير')

    def test_invoice_discount_tax_included_mix(self):
        # line 1: 2 x 500 -20% = 800 (+120 VAT) ; line 2: 230 incl. VAT ; total 1150
        inv = self._create_invoice(self.partner_en, [
            {'price': 500.0, 'qty': 2, 'discount': 20.0},
            {'price': 230.0, 'taxes': self.tax_15_incl},
        ])
        self.assertAlmostEqual(inv.amount_total, 1150.0)
        self.assertEqual(inv.amount_total_words, 'One Thousand One Hundred and Fifty Saudi Riyals Only')

    def test_invoice_cash_rounding_add_line(self):
        rounding = self.env['account.cash.rounding'].create({
            'name': '0.05 HALF-UP', 'rounding': 0.05, 'strategy': 'add_invoice_line',
            'profit_account_id': self.company_data['default_account_revenue'].id,
            'loss_account_id': self.company_data['default_account_expense'].id,
            'rounding_method': 'HALF-UP',
        })
        inv = self._create_invoice(self.partner_ar, [{'price': 10.03, 'taxes': self.env['account.tax']}],
                                   invoice_cash_rounding_id=rounding.id)
        self.assertAlmostEqual(inv.amount_total, 10.05)
        self.assertEqual(inv.amount_total_words, 'فقط عشرة ريالات سعودية وخمس هللات لا غير')

    def test_invoice_cash_rounding_biggest_tax(self):
        rounding = self.env['account.cash.rounding'].create({
            'name': '1.00 UP biggest tax', 'rounding': 1.0, 'strategy': 'biggest_tax',
            'rounding_method': 'UP',
        })
        # 99 + 14.85 VAT = 113.85 -> 114.00
        inv = self._create_invoice(self.partner_en, [{'price': 99.0}], invoice_cash_rounding_id=rounding.id)
        self.assertAlmostEqual(inv.amount_total, 114.0)
        self.assertEqual(inv.amount_total_words, 'One Hundred and Fourteen Saudi Riyals Only')

    def test_invoice_three_decimal_currency(self):
        self.env.ref('product.decimal_price').digits = 3
        inv = self._create_invoice(self.partner_ar, [{'price': 12.505, 'taxes': self.env['account.tax']}],
                                   currency=self.kwd)
        self.assertAlmostEqual(inv.amount_total, 12.505, places=3)
        self.assertEqual(inv.amount_total_words, 'فقط اثنا عشر ديناراً كويتياً وخمسمائة وخمسة فلوس لا غير')

    def test_invoice_usd_and_credit_note(self):
        refund = self._create_invoice(self.partner_en, [{'price': 20.0}], currency=self.usd, move_type='out_refund')
        self.assertAlmostEqual(refund.amount_total, 23.0)
        self.assertEqual(refund.amount_total_words, 'Twenty-Three US Dollars Only')

    def test_invoice_form_onchange_updates_words_live(self):
        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.partner_id = self.partner_en
        move_form.currency_id = self.sar
        with move_form.invoice_line_ids.new() as line:
            line.product_id = self.product
            line.price_unit = 200.0
            line.tax_ids.clear()
            line.tax_ids.add(self.tax_15)
        self.assertEqual(move_form.amount_total_words, 'Two Hundred and Thirty Saudi Riyals Only')
        with move_form.invoice_line_ids.edit(0) as line:
            line.discount = 25.0
        self.assertEqual(move_form.amount_total_words, 'One Hundred and Seventy-Two Saudi Riyals and Fifty Halalas Only')
        move = move_form.save()
        self.assertEqual(move.amount_total_words, 'One Hundred and Seventy-Two Saudi Riyals and Fifty Halalas Only')

    def test_journal_entry_has_no_words(self):
        entry = self.env['account.move'].create({
            'move_type': 'entry',
            'line_ids': [
                Command.create({'account_id': self.company_data['default_account_revenue'].id, 'debit': 10.0}),
                Command.create({'account_id': self.company_data['default_account_expense'].id, 'credit': 10.0}),
            ],
        })
        self.assertFalse(entry.amount_total_words)

    # ------------------------------------------------------------------
    # QWeb reports
    # ------------------------------------------------------------------
    def _render(self, report_ref, records):
        html, _fmt = self.env['ir.actions.report']._render_qweb_html(report_ref, records.ids)
        return html.decode() if isinstance(html, bytes) else html

    def test_sale_report_contains_words(self):
        so_en = self._create_so(self.partner_en, [{'price': 1000.0}])
        html = self._render('sale.action_report_saleorder', so_en)
        self.assertIn('One Thousand One Hundred and Fifty Saudi Riyals Only', html)
        self.assertIn('Total (In Words):', html)
        self.assertRegex(html, r'<div[^>]*name="amount_total_words"[^>]*dir="ltr"[^>]*text-align: left')

        so_ar = self._create_so(self.partner_ar, [{'price': 1000.0}])
        html = self._render('sale.action_report_saleorder', so_ar)
        self.assertIn('فقط ألف ومائة وخمسون ريالاً سعودياً لا غير', html)
        self.assertRegex(html, r'<div[^>]*name="amount_total_words"[^>]*dir="rtl"[^>]*text-align: right')

    def test_invoice_report_contains_words(self):
        inv = self._create_invoice(self.partner_ar, [{'price': 1000.0}])
        inv.action_post()
        html = self._render('account.account_invoices', inv)
        self.assertIn('فقط ألف ومائة وخمسون ريالاً سعودياً لا غير', html)
        self.assertRegex(html, r'<div[^>]*name="amount_total_words"[^>]*dir="rtl"')

    def test_report_toggles(self):
        so = self._create_so(self.partner_en, [{'price': 1000.0}])
        inv = self._create_invoice(self.partner_en, [{'price': 1000.0}])
        inv.action_post()
        self.company.write({'amount_words_on_sale_report': False, 'amount_words_on_invoice_report': False})
        self.assertNotIn('Total (In Words)', self._render('sale.action_report_saleorder', so))
        self.assertNotIn('Total (In Words)', self._render('account.account_invoices', inv))

    def test_arabic_report_label_translation(self):
        self.env['ir.module.module']._load_module_terms(['amount_in_words_multilingual'], ['ar_001'], overwrite=True)
        so_ar = self._create_so(self.partner_ar, [{'price': 1000.0}])
        html = self._render('sale.action_report_saleorder', so_ar)
        self.assertIn('الإجمالي كتابةً:', html)
        self.assertNotIn('Total (In Words):', html)

    # ------------------------------------------------------------------
    # Odoo 17+: standard "Total amount of invoice in letters" setting
    # ------------------------------------------------------------------
    def test_core_v17_field_uses_multilingual_engine(self):
        inv = self._create_invoice(self.partner_ar, [{'price': 1000.0}])
        self.assertEqual(inv._fields['amount_total_words'].string, 'Total (In Words)')
        self.assertEqual(inv.amount_total_words, 'فقط ألف ومائة وخمسون ريالاً سعودياً لا غير')

    def test_core_v17_letters_setting_not_printed_twice(self):
        inv = self._create_invoice(self.partner_en, [{'price': 1000.0}])
        inv.action_post()
        words = 'One Thousand One Hundred and Fifty Saudi Riyals Only'
        self.company.display_invoice_amount_total_words = True
        # both enabled: our block only
        html = self._render('account.account_invoices', inv)
        self.assertEqual(html.count(words), 1)
        self.assertNotIn('Total amount in words', html)
        # ours disabled: Odoo's own line prints, with our wording
        self.company.amount_words_on_invoice_report = False
        html = self._render('account.account_invoices', inv)
        self.assertEqual(html.count(words), 1)
        self.assertIn('Total amount in words', html)

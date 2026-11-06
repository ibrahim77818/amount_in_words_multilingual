# -*- coding: utf-8 -*-
"""Number-to-words engine and per-currency wording (no documents involved)."""
from odoo.tests import TransactionCase, tagged

from ..tools.amount_to_words import (
    CURRENCY_WORDS,
    amount_to_words_ar,
    amount_to_words_en,
    number_to_words_ar,
    number_to_words_en,
    split_amount,
)

SAR_AR = CURRENCY_WORDS['SAR']['ar']


def sar_ar(amount, wrap=True):
    return amount_to_words_ar(amount, 2, SAR_AR[0], SAR_AR[1], SAR_AR[2], SAR_AR[3], wrap=wrap)


@tagged('post_install', '-at_install', 'amount_in_words')
class TestAmountWordsEngine(TransactionCase):

    # ------------------------------------------------------------------
    # Rounding / splitting
    # ------------------------------------------------------------------
    def test_split_amount_half_up_without_float_noise(self):
        self.assertEqual(split_amount(1234.565, 2), (False, 1234, 57))
        self.assertEqual(split_amount(0.005, 2), (False, 0, 1))
        self.assertEqual(split_amount(2.675, 2), (False, 2, 68))  # 2.67499999... in binary
        self.assertEqual(split_amount(12.5054, 3), (False, 12, 505))
        self.assertEqual(split_amount(1499.6, 0), (False, 1500, 0))
        self.assertEqual(split_amount(-10.10, 2), (True, 10, 10))
        self.assertEqual(split_amount(99.999, 2), (False, 100, 0))

    # ------------------------------------------------------------------
    # English
    # ------------------------------------------------------------------
    def test_english_numbers(self):
        cases = {
            0: 'Zero',
            7: 'Seven',
            15: 'Fifteen',
            40: 'Forty',
            99: 'Ninety-Nine',
            100: 'One Hundred',
            105: 'One Hundred and Five',
            1005: 'One Thousand and Five',
            1250: 'One Thousand Two Hundred and Fifty',
            1000000: 'One Million',
            2000000001: 'Two Billion and One',
            1234567: 'One Million Two Hundred and Thirty-Four Thousand Five Hundred and Sixty-Seven',
        }
        for number, expected in cases.items():
            with self.subTest(number=number):
                self.assertEqual(number_to_words_en(number), expected)

    def test_english_amounts_singular_plural(self):
        usd = CURRENCY_WORDS['USD']['en']
        self.assertEqual(amount_to_words_en(1, 2, *usd), 'One US Dollar Only')
        self.assertEqual(amount_to_words_en(1.01, 2, *usd), 'One US Dollar and One Cent Only')
        self.assertEqual(amount_to_words_en(0.25, 2, *usd), 'Twenty-Five Cents Only')
        self.assertEqual(amount_to_words_en(0, 2, *usd), 'Zero US Dollars Only')
        self.assertEqual(amount_to_words_en(1150, 2, *usd, wrap=False), 'One Thousand One Hundred and Fifty US Dollars')
        self.assertEqual(amount_to_words_en(-3, 2, *usd), 'Minus Three US Dollars Only')

    # ------------------------------------------------------------------
    # Arabic grammar
    # ------------------------------------------------------------------
    def test_arabic_counted_noun_forms(self):
        cases = {
            1: 'فقط ريال سعودي واحد لا غير',
            2: 'فقط ريالان سعوديان لا غير',
            3: 'فقط ثلاثة ريالات سعودية لا غير',
            10: 'فقط عشرة ريالات سعودية لا غير',
            11: 'فقط أحد عشر ريالاً سعودياً لا غير',
            12: 'فقط اثنا عشر ريالاً سعودياً لا غير',
            19: 'فقط تسعة عشر ريالاً سعودياً لا غير',
            21: 'فقط واحد وعشرون ريالاً سعودياً لا غير',
            100: 'فقط مائة ريال سعودي لا غير',
            105: 'فقط مائة وخمسة ريالات سعودية لا غير',
            150: 'فقط مائة وخمسون ريالاً سعودياً لا غير',
            1000: 'فقط ألف ريال سعودي لا غير',
        }
        for amount, expected in cases.items():
            with self.subTest(amount=amount):
                self.assertEqual(sar_ar(amount), expected)

    def test_arabic_scales_and_construct_state(self):
        cases = {
            200: 'مائتا ريال سعودي',
            1200: 'ألف ومائتا ريال سعودي',
            2000: 'ألفا ريال سعودي',
            3000: 'ثلاثة آلاف ريال سعودي',
            11000: 'أحد عشر ألف ريال سعودي',
            15500: 'خمسة عشر ألفاً وخمسمائة ريال سعودي',
            101000: 'مائة ألف وألف ريال سعودي',
            200000: 'مائتا ألف ريال سعودي',
            250000: 'مائتان وخمسون ألف ريال سعودي',
            2000000: 'مليونا ريال سعودي',
            3000000: 'ثلاثة ملايين ريال سعودي',
            1000000000: 'مليار ريال سعودي',
        }
        for amount, expected in cases.items():
            with self.subTest(amount=amount):
                self.assertEqual(sar_ar(amount, wrap=False), expected)

    def test_arabic_feminine_subunit_agreement(self):
        # هللة is feminine: numbers take the opposite form from riyal
        self.assertEqual(sar_ar(0.01, wrap=False), 'هللة واحدة')
        self.assertEqual(sar_ar(0.02, wrap=False), 'هللتان')
        self.assertEqual(sar_ar(0.03, wrap=False), 'ثلاث هللات')
        self.assertEqual(sar_ar(0.11, wrap=False), 'إحدى عشرة هللة')
        self.assertEqual(sar_ar(0.12, wrap=False), 'اثنتا عشرة هللة')
        self.assertEqual(sar_ar(0.13, wrap=False), 'ثلاث عشرة هللة')
        self.assertEqual(sar_ar(0.21, wrap=False), 'إحدى وعشرون هللة')
        self.assertEqual(sar_ar(0.89, wrap=False), 'تسع وثمانون هللة')
        self.assertEqual(number_to_words_ar(18, feminine=True), 'ثماني عشرة')

    def test_arabic_full_amount(self):
        self.assertEqual(
            sar_ar(1235.50),
            'فقط ألف ومائتان وخمسة وثلاثون ريالاً سعودياً وخمسون هللة لا غير')
        self.assertEqual(
            sar_ar(1234567.89),
            'فقط مليون ومائتان وأربعة وثلاثون ألفاً وخمسمائة وسبعة وستون ريالاً سعودياً '
            'وتسع وثمانون هللة لا غير')
        self.assertEqual(sar_ar(0), 'فقط صفر ريال سعودي لا غير')

    # ------------------------------------------------------------------
    # res.currency integration
    # ------------------------------------------------------------------
    def _currency(self, code):
        return self.env['res.currency'].with_context(active_test=False).search([('name', '=', code)], limit=1)

    def test_currency_wording_seeded_on_install(self):
        sar = self._currency('SAR')
        self.assertEqual(sar.words_ar_unit_accusative, 'ريالاً سعودياً')
        self.assertEqual(sar.words_ar_sub_singular, 'هللة')
        self.assertTrue(sar.words_ar_sub_feminine)
        self.assertEqual(sar.words_en_unit_plural, 'Saudi Riyals')

    def test_currency_multi_currency_conversion(self):
        cases = [
            ('SAR', 'en_US', 1150.0, 'One Thousand One Hundred and Fifty Saudi Riyals Only'),
            ('SAR', 'ar_001', 1150.0, 'فقط ألف ومائة وخمسون ريالاً سعودياً لا غير'),
            ('USD', 'ar_001', 3.5, 'فقط ثلاثة دولارات أمريكية وخمسون سنتاً لا غير'),
            ('EUR', 'en_US', 21.01, 'Twenty-One Euros and One Cent Only'),
            ('AED', 'ar_001', 12, 'فقط اثنا عشر درهماً إماراتياً لا غير'),
            ('EGP', 'ar_001', 7.03, 'فقط سبعة جنيهات مصرية وثلاثة قروش لا غير'),
            # 3-decimal currency: subunits are thousandths
            ('KWD', 'ar_001', 12.505, 'فقط اثنا عشر ديناراً كويتياً وخمسمائة وخمسة فلوس لا غير'),
            ('KWD', 'en_US', 1.5, 'One Kuwaiti Dinar and Five Hundred Fils Only'),
            # feminine main unit
            ('TRY', 'ar_001', 3, 'فقط ثلاث ليرات تركية لا غير'),
        ]
        for code, lang, amount, expected in cases:
            with self.subTest(code=code, lang=lang, amount=amount):
                self.assertEqual(self._currency(code).amount_to_words_multilingual(amount, lang=lang), expected)

    def test_currency_without_subunit_decimals(self):
        jpy = self._currency('JPY')
        jpy.decimal_places = 0
        self.assertEqual(jpy.amount_to_words_multilingual(1500.4, lang='en_US'),
                         'One Thousand Five Hundred Japanese Yen Only')
        self.assertEqual(jpy.amount_to_words_multilingual(1500.4, lang='ar_001'),
                         'فقط ألف وخمسمائة ين ياباني لا غير')

    def test_currency_user_override_and_reset(self):
        sar = self._currency('SAR')
        sar.write({'words_en_unit_singular': 'Riyal', 'words_en_unit_plural': 'Riyals'})
        self.assertEqual(sar.amount_to_words_multilingual(5, lang='en_US'), 'Five Riyals Only')
        sar.action_amount_words_reset()
        self.assertEqual(sar.amount_to_words_multilingual(5, lang='en_US'), 'Five Saudi Riyals Only')

    def test_unknown_currency_fallback_labels(self):
        currency = self.env['res.currency'].create({
            'name': 'XTS', 'symbol': 'T', 'rounding': 0.01,
            'currency_unit_label': 'Token', 'currency_subunit_label': 'Bit',
        })
        self.assertFalse(currency.words_en_unit_singular, "no built-in vocabulary for XTS")
        self.assertEqual(currency.amount_to_words_multilingual(2.5, lang='en_US'),
                         'Two Token and Fifty Bit Only')
        self.assertEqual(currency.amount_to_words_multilingual(2, lang='ar_001'), 'فقط Token اثنان لا غير')

    def test_new_currency_with_known_code_is_seeded(self):
        sar = self._currency('SAR')
        sar.write({'name': 'SAX'})  # free the code, then recreate
        sar.flush_recordset()
        new = self.env['res.currency'].create({'name': 'SAR', 'symbol': 'ر.س', 'rounding': 0.01})
        self.assertEqual(new.words_ar_unit_dual, 'ريالان سعوديان')

    def test_other_language_uses_odoo_engine(self):
        self.env['res.lang']._activate_lang('fr_FR')
        words = self._currency('EUR').amount_to_words_multilingual(10, lang='fr_FR')
        self.assertTrue(words)
        self.assertNotIn('Only', words, "French must not use the English engine")

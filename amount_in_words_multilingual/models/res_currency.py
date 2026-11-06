# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

from ..tools.amount_to_words import (
    CURRENCY_WORDS,
    amount_to_words_ar,
    amount_to_words_en,
)

_logger = logging.getLogger(__name__)

_EN_FIELDS = ('words_en_unit_singular', 'words_en_unit_plural',
              'words_en_sub_singular', 'words_en_sub_plural')
_AR_UNIT_FIELDS = ('words_ar_unit_singular', 'words_ar_unit_dual',
                   'words_ar_unit_plural', 'words_ar_unit_accusative')
_AR_SUB_FIELDS = ('words_ar_sub_singular', 'words_ar_sub_dual',
                  'words_ar_sub_plural', 'words_ar_sub_accusative')


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    # ---- English wording -------------------------------------------------
    words_en_unit_singular = fields.Char('Unit (Singular)', help="e.g. Saudi Riyal")
    words_en_unit_plural = fields.Char('Unit (Plural)', help="e.g. Saudi Riyals")
    words_en_sub_singular = fields.Char('Subunit (Singular)', help="e.g. Halala")
    words_en_sub_plural = fields.Char('Subunit (Plural)', help="e.g. Halalas")

    # ---- Arabic wording --------------------------------------------------
    words_ar_unit_singular = fields.Char(
        'Arabic Unit (Singular)', help="Used for 1, round hundreds/thousands: ريال سعودي")
    words_ar_unit_dual = fields.Char('Arabic Unit (Dual)', help="Used for 2: ريالان سعوديان")
    words_ar_unit_plural = fields.Char('Arabic Unit (Plural)', help="Used for 3 to 10: ريالات سعودية")
    words_ar_unit_accusative = fields.Char(
        'Arabic Unit (Accusative)', help="Used for 11 to 99: ريالاً سعودياً")
    words_ar_unit_feminine = fields.Boolean(
        'Arabic Unit is Feminine',
        help="Feminine nouns (e.g. ليرة) change the number words: ثلاث ليرات instead of ثلاثة.")
    words_ar_sub_singular = fields.Char('Arabic Subunit (Singular)', help="e.g. هللة")
    words_ar_sub_dual = fields.Char('Arabic Subunit (Dual)', help="e.g. هللتان")
    words_ar_sub_plural = fields.Char('Arabic Subunit (Plural)', help="e.g. هللات")
    words_ar_sub_accusative = fields.Char('Arabic Subunit (Accusative)', help="e.g. هللة")
    words_ar_sub_feminine = fields.Boolean('Arabic Subunit is Feminine')

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------
    def _amount_words_default_vals(self):
        self.ensure_one()
        data = CURRENCY_WORDS.get(self.name)
        if not data:
            return {}
        unit_forms, unit_fem, sub_forms, sub_fem = data['ar']
        vals = dict(zip(_EN_FIELDS, data['en']))
        vals.update(zip(_AR_UNIT_FIELDS, unit_forms))
        vals.update(zip(_AR_SUB_FIELDS, sub_forms))
        vals.update(words_ar_unit_feminine=unit_fem, words_ar_sub_feminine=sub_fem)
        return vals

    def _amount_words_seed_defaults(self):
        """Fill empty wording fields from the built-in vocabulary (never overwrites)."""
        for currency in self:
            defaults = currency._amount_words_default_vals()
            if not defaults:
                continue
            text_fields = _EN_FIELDS + _AR_UNIT_FIELDS + _AR_SUB_FIELDS
            if any(currency[f] for f in text_fields):
                # Already configured (partly or fully): only fill the blanks,
                # and leave the gender flags as the user set them.
                vals = {f: v for f, v in defaults.items() if f in text_fields and not currency[f]}
            else:
                vals = defaults
            if vals:
                currency.write(vals)

    def action_amount_words_reset(self):
        """Button: reload the built-in wording for this currency."""
        for currency in self:
            vals = currency._amount_words_default_vals()
            if vals:
                currency.write(vals)
        return True

    # ------------------------------------------------------------------
    # Terms resolution
    # ------------------------------------------------------------------
    def _amount_words_has_subunit(self):
        self.ensure_one()
        return (self.decimal_places or 0) > 0

    def _amount_words_en_terms(self):
        self.ensure_one()
        defaults = CURRENCY_WORDS.get(self.name, {}).get('en') or (None,) * 4
        unit_s = self.words_en_unit_singular or defaults[0] or self.currency_unit_label or self.name
        unit_p = self.words_en_unit_plural or defaults[1] or self.currency_unit_label or unit_s
        sub_s = self.words_en_sub_singular or defaults[2] or self.currency_subunit_label or False
        sub_p = self.words_en_sub_plural or defaults[3] or self.currency_subunit_label or sub_s
        return unit_s, unit_p, sub_s, sub_p

    def _amount_words_ar_terms(self):
        self.ensure_one()
        default = CURRENCY_WORDS.get(self.name, {}).get('ar')
        if any(self[f] for f in _AR_UNIT_FIELDS):
            single = self.words_ar_unit_singular or self.words_ar_unit_accusative or self.name
            unit_forms = tuple(self[f] or single for f in _AR_UNIT_FIELDS)
            unit_fem = self.words_ar_unit_feminine
        elif default:
            unit_forms, unit_fem = default[0], default[1]
        else:
            label = self.currency_unit_label or self.name
            unit_forms, unit_fem = (label,) * 4, False
        if any(self[f] for f in _AR_SUB_FIELDS):
            single = self.words_ar_sub_singular or self.words_ar_sub_accusative
            sub_forms = tuple(self[f] or single for f in _AR_SUB_FIELDS)
            sub_fem = self.words_ar_sub_feminine
        elif default:
            sub_forms, sub_fem = default[2], default[3]
        elif self.currency_subunit_label:
            sub_forms, sub_fem = (self.currency_subunit_label,) * 4, False
        else:
            sub_forms, sub_fem = None, False
        return unit_forms, unit_fem, sub_forms, sub_fem

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @api.model
    def _amount_words_lang_family(self, lang):
        """'ar', 'en' or the raw language code for any other language."""
        lang = lang or 'en_US'
        if lang == 'ar' or lang.startswith('ar_'):
            return 'ar'
        if lang == 'en' or lang.startswith('en_'):
            return 'en'
        return lang

    @api.model
    def _amount_words_is_rtl(self, lang):
        if not lang:
            return False
        if self._amount_words_lang_family(lang) == 'ar':
            return True
        lang_rec = self.env['res.lang']._lang_get(lang)
        return bool(lang_rec and lang_rec.direction == 'rtl')

    def amount_to_words_multilingual(self, amount, lang=None, wrap=True):
        """Spell ``amount`` in ``lang``.

        English and Arabic use this module's engine; any other language
        falls back to Odoo's standard ``amount_to_text`` (num2words).
        """
        self.ensure_one()
        lang = lang or self.env.lang or 'en_US'
        family = self._amount_words_lang_family(lang)
        decimals = self.decimal_places if self._amount_words_has_subunit() else 0
        if family == 'ar':
            unit_forms, unit_fem, sub_forms, sub_fem = self._amount_words_ar_terms()
            return amount_to_words_ar(
                amount, decimals, unit_forms, unit_fem,
                sub_forms if decimals else None, sub_fem, wrap=wrap)
        if family != 'en':
            try:
                words = self.with_context(lang=lang).amount_to_text(amount)
                if words:
                    return words
            except Exception:  # noqa: BLE001 - never block a document for words
                _logger.warning("amount_to_text failed for lang %s, falling back to English",
                                lang, exc_info=True)
        unit_s, unit_p, sub_s, sub_p = self._amount_words_en_terms()
        return amount_to_words_en(amount, decimals, unit_s, unit_p,
                                  sub_s if decimals else None, sub_p, wrap=wrap)

    @api.model_create_multi
    def create(self, vals_list):
        currencies = super().create(vals_list)
        currencies._amount_words_seed_defaults()
        return currencies

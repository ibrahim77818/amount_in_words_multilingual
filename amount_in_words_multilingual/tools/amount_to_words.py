# -*- coding: utf-8 -*-
# Part of amount_in_words_multilingual. See LICENSE file for full copyright and licensing details.
"""Pure-Python number-to-words engine (English and Arabic).

This module deliberately has no Odoo imports so it can be unit-tested and
reused anywhere. Odoo-specific glue lives in ``models/res_currency.py``.

Arabic grammar implemented
--------------------------
* Gender agreement of numbers 1-19 (and the units of 21-99) with the counted
  noun: masculine nouns (ريال، دينار، فلس) take ثلاثة/عشرة/أحد عشر, feminine
  nouns (هللة، ليرة، بيسة) take ثلاث/عشر/إحدى عشرة.
* Counted-noun (تمييز) form chosen from the number:
    1            -> singular + "واحد/واحدة"        (ريال سعودي واحد)
    2            -> dual                             (ريالان سعوديان)
    3..10        -> plural (genitive)                (خمسة ريالات سعودية)
    11..99       -> singular accusative               (خمسون ريالاً سعودياً)
    x00 / x000   -> singular genitive                 (مائة ريال سعودي)
  For numbers above 100 the last two digits decide (e.g. 105 -> plural,
  150 -> accusative). Numbers ending in 01/02 use the singular genitive
  (مائة وواحد ريال سعودي), the convention used on Gulf commercial documents.
* Scale words follow the same rules: ألف / ألفان / ثلاثة آلاف / أحد عشر ألفاً /
  مائة ألف, and the dual hundred in construct state before a scale word
  (مائتا ألف).
"""
from decimal import Decimal, ROUND_HALF_UP

# --------------------------------------------------------------------------
# Amount splitting
# --------------------------------------------------------------------------


def split_amount(amount, decimal_places=2):
    """Return ``(negative, integer_part, fraction_in_subunits)``.

    Rounds HALF-UP to ``decimal_places`` the same way Odoo's ``float_round``
    does, avoiding binary float artefacts (1234.565 -> 1234.57).
    """
    decimal_places = max(int(decimal_places or 0), 0)
    if isinstance(amount, Decimal):
        value = amount
    else:
        # repr-with-extra-digits removes binary noise before quantizing
        value = Decimal('%.*f' % (decimal_places + 6, float(amount or 0.0)))
    quantum = Decimal(1).scaleb(-decimal_places)
    value = value.quantize(quantum, rounding=ROUND_HALF_UP)
    negative = value < 0
    value = abs(value)
    integer_part = int(value)
    fraction = int(((value - integer_part) * (10 ** decimal_places)).to_integral_value(ROUND_HALF_UP))
    return negative, integer_part, fraction


# --------------------------------------------------------------------------
# English
# --------------------------------------------------------------------------

_EN_ONES = ['Zero', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight',
            'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen',
            'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
_EN_TENS = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
_EN_SCALES = ['', 'Thousand', 'Million', 'Billion', 'Trillion', 'Quadrillion']


def _en_below_1000(n, use_and):
    words = []
    hundreds, rest = divmod(n, 100)
    if hundreds:
        words.append('%s Hundred' % _EN_ONES[hundreds])
    if rest:
        if hundreds and use_and:
            words.append('and')
        if rest < 20:
            words.append(_EN_ONES[rest])
        else:
            tens, units = divmod(rest, 10)
            words.append(_EN_TENS[tens] + ('-' + _EN_ONES[units] if units else ''))
    return ' '.join(words)


def number_to_words_en(n, use_and=True):
    """Integer -> English words, e.g. 1235 -> 'One Thousand Two Hundred and Thirty-Five'."""
    n = int(n)
    if n < 0:
        return 'Minus ' + number_to_words_en(-n, use_and)
    if n == 0:
        return _EN_ONES[0]
    groups = []
    while n:
        n, g = divmod(n, 1000)
        groups.append(g)
    if len(groups) > len(_EN_SCALES):
        raise ValueError('Number too large to convert to words')
    parts = []
    for idx in range(len(groups) - 1, -1, -1):
        g = groups[idx]
        if not g:
            continue
        text = _en_below_1000(g, use_and)
        if idx:
            text += ' ' + _EN_SCALES[idx]
        elif use_and and parts and g < 100:
            # "One Thousand and Five"
            text = 'and ' + text
        parts.append(text)
    return ' '.join(parts)


def amount_to_words_en(amount, decimal_places, unit_singular, unit_plural,
                       sub_singular=None, sub_plural=None, wrap=True):
    negative, integer_part, fraction = split_amount(amount, decimal_places)
    unit_plural = unit_plural or unit_singular
    sub_plural = sub_plural or sub_singular
    parts = []
    if integer_part or not fraction or not sub_singular:
        parts.append('%s %s' % (number_to_words_en(integer_part),
                                unit_singular if integer_part == 1 else unit_plural))
    if fraction and sub_singular:
        parts.append('%s %s' % (number_to_words_en(fraction),
                                sub_singular if fraction == 1 else sub_plural))
    elif fraction:
        # No subunit name configured: express the fraction numerically
        parts[-1] += ' and %0*d/%d' % (decimal_places, fraction, 10 ** decimal_places)
    text = ' and '.join(parts)
    if negative:
        text = 'Minus ' + text
    return text + ' Only' if wrap else text


# --------------------------------------------------------------------------
# Arabic
# --------------------------------------------------------------------------

_AR_ZERO = 'صفر'
_AR_AND = ' و'

# Index = number (1..10). "m" = form used with a masculine counted noun.
_AR_ONES_M = ['', 'واحد', 'اثنان', 'ثلاثة', 'أربعة', 'خمسة', 'ستة', 'سبعة', 'ثمانية', 'تسعة', 'عشرة']
_AR_ONES_F = ['', 'واحدة', 'اثنتان', 'ثلاث', 'أربع', 'خمس', 'ست', 'سبع', 'ثماني', 'تسع', 'عشر']
_AR_TEENS_M = {11: 'أحد عشر', 12: 'اثنا عشر'}
_AR_TEENS_F = {11: 'إحدى عشرة', 12: 'اثنتا عشرة'}
# Units inside compound numbers 21..99 ("واحد وعشرون" / "إحدى وعشرون")
_AR_COMPOUND_UNIT_F1 = 'إحدى'
_AR_TENS = ['', 'عشرة', 'عشرون', 'ثلاثون', 'أربعون', 'خمسون', 'ستون', 'سبعون', 'ثمانون', 'تسعون']
_AR_HUNDREDS = ['', 'مائة', 'مائتان', 'ثلاثمائة', 'أربعمائة', 'خمسمائة', 'ستمائة',
                'سبعمائة', 'ثمانمائة', 'تسعمائة']
_AR_HUNDRED_TWO_CONSTRUCT = 'مائتا'

# (singular, dual, plural, accusative singular) — all masculine nouns
_AR_SCALES = [
    None,
    ('ألف', 'ألفان', 'آلاف', 'ألفاً'),
    ('مليون', 'مليونان', 'ملايين', 'مليوناً'),
    ('مليار', 'ملياران', 'مليارات', 'ملياراً'),
    ('تريليون', 'تريليونان', 'تريليونات', 'تريليوناً'),
    ('كوادريليون', 'كوادريليونان', 'كوادريليونات', 'كوادريليوناً'),
]


def _ar_below_100(n, feminine):
    if n == 0:
        return ''
    if n <= 10:
        return (_AR_ONES_F if feminine else _AR_ONES_M)[n]
    if n < 20:
        if n in (11, 12):
            return (_AR_TEENS_F if feminine else _AR_TEENS_M)[n]
        # 13..19: unit has reverse agreement, "ten" agrees with the noun
        unit = (_AR_ONES_F if feminine else _AR_ONES_M)[n - 10]
        return '%s %s' % (unit, 'عشرة' if feminine else 'عشر')
    tens, units = divmod(n, 10)
    if not units:
        return _AR_TENS[tens]
    if units == 1 and feminine:
        unit = _AR_COMPOUND_UNIT_F1
    else:
        unit = (_AR_ONES_F if feminine else _AR_ONES_M)[units]
    return unit + _AR_AND + _AR_TENS[tens]


def _ar_below_1000(n, feminine, construct=False):
    hundreds, rest = divmod(n, 100)
    parts = []
    if hundreds:
        if hundreds == 2 and not rest and construct:
            parts.append(_AR_HUNDRED_TWO_CONSTRUCT)
        else:
            parts.append(_AR_HUNDREDS[hundreds])
    if rest:
        parts.append(_ar_below_100(rest, feminine))
    return _AR_AND.join(parts)


def ar_counted_form(n, forms):
    """Pick the counted-noun form for integer ``n``.

    ``forms`` = (singular, dual, plural, accusative). Returns ``(kind, noun)``
    where kind is one of 'one', 'two', 'plural', 'accusative', 'singular'.
    """
    singular, dual, plural, accusative = forms
    if n == 1:
        return 'one', singular
    if n == 2:
        return 'two', dual
    rest = n % 100
    if 3 <= rest <= 10:
        return 'plural', plural
    if 11 <= rest <= 99:
        return 'accusative', accusative
    return 'singular', singular  # 0, x00, x01, x02


def _ar_scale_group(g, forms):
    """Words for a 3-digit group ``g`` (>0) followed by a scale word."""
    if g == 1:
        return forms[0]
    if g == 2:
        return forms[1]
    rest = g % 100
    if g > 100 and rest in (1, 2):
        # 101000 -> "مائة ألف وألف" ; 102000 -> "مائة ألف وألفان"
        head = _ar_below_1000(g - rest, feminine=False, construct=True)
        return '%s %s%s%s' % (head, forms[0], _AR_AND, forms[rest - 1])
    _kind, noun = ar_counted_form(g, forms)
    return '%s %s' % (_ar_below_1000(g, feminine=False, construct=True), noun)


def number_to_words_ar(n, feminine=False):
    """Integer -> Arabic words, numbers agreeing with a (fem.) counted noun."""
    n = int(n)
    if n < 0:
        return 'سالب ' + number_to_words_ar(-n, feminine)
    if n == 0:
        return _AR_ZERO
    groups = []
    while n:
        n, g = divmod(n, 1000)
        groups.append(g)
    if len(groups) > len(_AR_SCALES):
        raise ValueError('Number too large to convert to words')
    parts = []
    for idx in range(len(groups) - 1, -1, -1):
        g = groups[idx]
        if not g:
            continue
        if idx:
            parts.append(_ar_scale_group(g, _AR_SCALES[idx]))
        else:
            parts.append(_ar_below_1000(g, feminine))
    return _AR_AND.join(parts)


_AR_DUALS_TO_CONSTRUCT = {_AR_HUNDREDS[2]: _AR_HUNDRED_TWO_CONSTRUCT}
_AR_ACCUSATIVE_TO_CONSTRUCT = {}
for _forms in _AR_SCALES[1:]:
    _AR_DUALS_TO_CONSTRUCT[_forms[1]] = _forms[1][:-1]      # ألفان -> ألفا
    _AR_ACCUSATIVE_TO_CONSTRUCT[_forms[3]] = _forms[0]      # ألفاً -> ألف


def _ar_construct_last_word(words):
    """Put the last word in construct state (إضافة) before the counted noun.

    'مائتان' -> 'مائتا ريال', 'ألفان' -> 'ألفا ريال', 'أحد عشر ألفاً' -> 'أحد عشر ألف ريال'.
    """
    head, _sep, last = words.rpartition(' ')
    prefix = ''
    if last.startswith('و') and last[1:] in _AR_DUALS_TO_CONSTRUCT:
        prefix, last = 'و', last[1:]          # "وألفان" -> "وألفا"
    last = _AR_DUALS_TO_CONSTRUCT.get(last) or _AR_ACCUSATIVE_TO_CONSTRUCT.get(last) or last
    last = prefix + last
    return (head + ' ' + last) if head else last


def _ar_counted(n, forms, feminine):
    """Number + counted noun, e.g. (35, riyal) -> 'خمسة وثلاثون ريالاً سعودياً'."""
    kind, noun = ar_counted_form(n, forms)
    if kind == 'one':
        return '%s %s' % (noun, _AR_ONES_F[1] if feminine else _AR_ONES_M[1])
    if kind == 'two':
        if noun == forms[0]:
            # no distinct dual configured: "<noun> اثنان" keeps the count explicit
            return '%s %s' % (noun, _AR_ONES_F[2] if feminine else _AR_ONES_M[2])
        return noun
    words = number_to_words_ar(n, feminine)
    if kind == 'singular':
        words = _ar_construct_last_word(words)
    return '%s %s' % (words, noun)


def amount_to_words_ar(amount, decimal_places, unit_forms, unit_feminine=False,
                       sub_forms=None, sub_feminine=False, wrap=True):
    """Arabic amount in words.

    ``unit_forms`` / ``sub_forms``: (singular, dual, plural, accusative).
    """
    negative, integer_part, fraction = split_amount(amount, decimal_places)
    parts = []
    if integer_part or not fraction or not sub_forms:
        if integer_part == 0:
            parts.append('%s %s' % (_AR_ZERO, unit_forms[0]))
        else:
            parts.append(_ar_counted(integer_part, unit_forms, unit_feminine))
    if fraction and sub_forms:
        parts.append(_ar_counted(fraction, sub_forms, sub_feminine))
    elif fraction:
        parts[-1] += _AR_AND + '%0*d/%d' % (decimal_places, fraction, 10 ** decimal_places)
    text = _AR_AND.join(parts)
    if negative:
        text = 'سالب ' + text
    return 'فقط %s لا غير' % text if wrap else text


# --------------------------------------------------------------------------
# Built-in currency vocabulary (used to seed / fall back for res.currency)
# --------------------------------------------------------------------------
# code: {
#   'ar': ((sing, dual, plural, acc), feminine, (sub sing, dual, plural, acc), sub_feminine),
#   'en': (singular, plural, sub_singular, sub_plural),
# }

def _ar(s, d, p, a):
    return (s, d, p, a)


_FILS = _ar('فلس', 'فلسان', 'فلوس', 'فلساً')
_QIRSH = _ar('قرش', 'قرشان', 'قروش', 'قرشاً')
_CENT = _ar('سنت', 'سنتان', 'سنتات', 'سنتاً')
_DIRHAM_SUB = _ar('درهم', 'درهمان', 'دراهم', 'درهماً')
_SANTIM = _ar('سنتيم', 'سنتيمان', 'سنتيمات', 'سنتيماً')
_BAISA = _ar('بيسة', 'بيستان', 'بيسات', 'بيسة')

CURRENCY_WORDS = {
    'SAR': {'ar': (_ar('ريال سعودي', 'ريالان سعوديان', 'ريالات سعودية', 'ريالاً سعودياً'), False,
                   _ar('هللة', 'هللتان', 'هللات', 'هللة'), True),
            'en': ('Saudi Riyal', 'Saudi Riyals', 'Halala', 'Halalas')},
    'AED': {'ar': (_ar('درهم إماراتي', 'درهمان إماراتيان', 'دراهم إماراتية', 'درهماً إماراتياً'), False,
                   _FILS, False),
            'en': ('UAE Dirham', 'UAE Dirhams', 'Fils', 'Fils')},
    'KWD': {'ar': (_ar('دينار كويتي', 'ديناران كويتيان', 'دنانير كويتية', 'ديناراً كويتياً'), False,
                   _FILS, False),
            'en': ('Kuwaiti Dinar', 'Kuwaiti Dinars', 'Fils', 'Fils')},
    'BHD': {'ar': (_ar('دينار بحريني', 'ديناران بحرينيان', 'دنانير بحرينية', 'ديناراً بحرينياً'), False,
                   _FILS, False),
            'en': ('Bahraini Dinar', 'Bahraini Dinars', 'Fils', 'Fils')},
    'OMR': {'ar': (_ar('ريال عماني', 'ريالان عمانيان', 'ريالات عمانية', 'ريالاً عمانياً'), False,
                   _BAISA, True),
            'en': ('Omani Rial', 'Omani Rials', 'Baisa', 'Baisas')},
    'QAR': {'ar': (_ar('ريال قطري', 'ريالان قطريان', 'ريالات قطرية', 'ريالاً قطرياً'), False,
                   _DIRHAM_SUB, False),
            'en': ('Qatari Riyal', 'Qatari Riyals', 'Dirham', 'Dirhams')},
    'JOD': {'ar': (_ar('دينار أردني', 'ديناران أردنيان', 'دنانير أردنية', 'ديناراً أردنياً'), False,
                   _FILS, False),
            'en': ('Jordanian Dinar', 'Jordanian Dinars', 'Fils', 'Fils')},
    'IQD': {'ar': (_ar('دينار عراقي', 'ديناران عراقيان', 'دنانير عراقية', 'ديناراً عراقياً'), False,
                   _FILS, False),
            'en': ('Iraqi Dinar', 'Iraqi Dinars', 'Fils', 'Fils')},
    'EGP': {'ar': (_ar('جنيه مصري', 'جنيهان مصريان', 'جنيهات مصرية', 'جنيهاً مصرياً'), False,
                   _QIRSH, False),
            'en': ('Egyptian Pound', 'Egyptian Pounds', 'Piastre', 'Piastres')},
    'SDG': {'ar': (_ar('جنيه سوداني', 'جنيهان سودانيان', 'جنيهات سودانية', 'جنيهاً سودانياً'), False,
                   _QIRSH, False),
            'en': ('Sudanese Pound', 'Sudanese Pounds', 'Piastre', 'Piastres')},
    'LYD': {'ar': (_ar('دينار ليبي', 'ديناران ليبيان', 'دنانير ليبية', 'ديناراً ليبياً'), False,
                   _DIRHAM_SUB, False),
            'en': ('Libyan Dinar', 'Libyan Dinars', 'Dirham', 'Dirhams')},
    'TND': {'ar': (_ar('دينار تونسي', 'ديناران تونسيان', 'دنانير تونسية', 'ديناراً تونسياً'), False,
                   _ar('مليم', 'مليمان', 'مليمات', 'مليماً'), False),
            'en': ('Tunisian Dinar', 'Tunisian Dinars', 'Millime', 'Millimes')},
    'DZD': {'ar': (_ar('دينار جزائري', 'ديناران جزائريان', 'دنانير جزائرية', 'ديناراً جزائرياً'), False,
                   _SANTIM, False),
            'en': ('Algerian Dinar', 'Algerian Dinars', 'Centime', 'Centimes')},
    'MAD': {'ar': (_ar('درهم مغربي', 'درهمان مغربيان', 'دراهم مغربية', 'درهماً مغربياً'), False,
                   _SANTIM, False),
            'en': ('Moroccan Dirham', 'Moroccan Dirhams', 'Centime', 'Centimes')},
    'YER': {'ar': (_ar('ريال يمني', 'ريالان يمنيان', 'ريالات يمنية', 'ريالاً يمنياً'), False,
                   _FILS, False),
            'en': ('Yemeni Rial', 'Yemeni Rials', 'Fils', 'Fils')},
    'LBP': {'ar': (_ar('ليرة لبنانية', 'ليرتان لبنانيتان', 'ليرات لبنانية', 'ليرة لبنانية'), True,
                   _QIRSH, False),
            'en': ('Lebanese Pound', 'Lebanese Pounds', 'Piastre', 'Piastres')},
    'SYP': {'ar': (_ar('ليرة سورية', 'ليرتان سوريتان', 'ليرات سورية', 'ليرة سورية'), True,
                   _QIRSH, False),
            'en': ('Syrian Pound', 'Syrian Pounds', 'Piastre', 'Piastres')},
    'TRY': {'ar': (_ar('ليرة تركية', 'ليرتان تركيتان', 'ليرات تركية', 'ليرة تركية'), True,
                   _QIRSH, False),
            'en': ('Turkish Lira', 'Turkish Liras', 'Kurus', 'Kurus')},
    'USD': {'ar': (_ar('دولار أمريكي', 'دولاران أمريكيان', 'دولارات أمريكية', 'دولاراً أمريكياً'), False,
                   _CENT, False),
            'en': ('US Dollar', 'US Dollars', 'Cent', 'Cents')},
    'EUR': {'ar': (_ar('يورو', 'يوروان', 'يوروات', 'يورو'), False, _CENT, False),
            'en': ('Euro', 'Euros', 'Cent', 'Cents')},
    'GBP': {'ar': (_ar('جنيه إسترليني', 'جنيهان إسترلينيان', 'جنيهات إسترلينية', 'جنيهاً إسترلينياً'), False,
                   _ar('بنس', 'بنسان', 'بنسات', 'بنساً'), False),
            'en': ('Pound Sterling', 'Pounds Sterling', 'Penny', 'Pence')},
    'INR': {'ar': (_ar('روبية هندية', 'روبيتان هنديتان', 'روبيات هندية', 'روبية هندية'), True,
                   _BAISA, True),
            'en': ('Indian Rupee', 'Indian Rupees', 'Paisa', 'Paise')},
    'PKR': {'ar': (_ar('روبية باكستانية', 'روبيتان باكستانيتان', 'روبيات باكستانية', 'روبية باكستانية'), True,
                   _BAISA, True),
            'en': ('Pakistani Rupee', 'Pakistani Rupees', 'Paisa', 'Paise')},
    'CNY': {'ar': (_ar('يوان صيني', 'يوانان صينيان', 'يوانات صينية', 'يواناً صينياً'), False,
                   _ar('فين', 'فينان', 'فينات', 'فيناً'), False),
            'en': ('Chinese Yuan', 'Chinese Yuan', 'Fen', 'Fen')},
    'JPY': {'ar': (_ar('ين ياباني', 'ينان يابانيان', 'ينات يابانية', 'يناً يابانياً'), False,
                   _ar('سن', 'سنان', 'سنات', 'سناً'), False),
            'en': ('Japanese Yen', 'Japanese Yen', 'Sen', 'Sen')},
    'CHF': {'ar': (_ar('فرنك سويسري', 'فرنكان سويسريان', 'فرنكات سويسرية', 'فرنكاً سويسرياً'), False,
                   _SANTIM, False),
            'en': ('Swiss Franc', 'Swiss Francs', 'Centime', 'Centimes')},
}

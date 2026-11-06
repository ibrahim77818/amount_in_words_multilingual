# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Seed the per-currency wording for every currency we know about.

    Odoo 17 passes an Environment to install hooks (v16 passed cr, registry).
    """
    currencies = env['res.currency'].with_context(active_test=False).search([])
    currencies._amount_words_seed_defaults()

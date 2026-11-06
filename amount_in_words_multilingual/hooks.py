# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    """Seed the per-currency wording for every currency we know about."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    currencies = env['res.currency'].with_context(active_test=False).search([])
    currencies._amount_words_seed_defaults()

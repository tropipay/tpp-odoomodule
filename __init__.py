# -*- coding: utf-8 -*-
#############################################################################
#
#   TropiPay.
#   soporte@tropipay.com
#   
#
#############################################################################


from . import models
from . import controllers

from odoo.addons.payment import setup_provider, reset_payment_provider


def post_init_hook(env):
    # Odoo 17 hooks reciben env
    setup_provider(env, 'tpp')

def uninstall_hook(env):
    # Odoo 17 hooks reciben env
    reset_payment_provider(env, 'tpp')
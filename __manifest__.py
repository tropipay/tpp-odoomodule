# -*- coding: utf-8 -*-
#############################################################################
#
#   TropiPay.
#   soporte@tropipay.com
#   
#
#############################################################################

{
    'name': 'Tropipay Payment Gateway',
    'category': 'Accounting/Payment Acquirers',
    'version': '1.4.0',
    'description': """Tropipay Payment Gateway for Odoo 17""",
    'summary': """Tropipay Payment Gateway for Odoo 17""",
    'author': "TropiPay",
    'company': 'TropiPay',
    'maintainer': 'Tropipay',
    'website': "https://www.tropipay.com",
    'depends': ['payment', 'account', 'website', 'website_sale'],
    'data': [
        'data/payment_method_data.xml',
        'views/payment_template.xml',
        'views/payment_tpp_templates.xml',
        #'views/tpp_payment_template.xml',
        'data/payment_provider_data.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'images': ['static/description/tropipaylogo.png'],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}


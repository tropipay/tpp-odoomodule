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
    'version': '1.4.0.0.0',
    'description': """Tropipay Payment Gateway V1.4""",
    'Summary': """Tropipay Payment Gateway V1.4""",
    'author': "TropiPay",
    'company': 'TropiPay',
    'maintainer': 'Tropipay',
    'website': "https://www.tropipay.com",
    'depends': ['payment', 'account', 'portal'],
    'data': [
        'views/payment_template.xml',
        'views/payment_tpp_templates.xml',
        'data/payment_provider_data.xml',
        'data/account_payment_method_data.xml'
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'images': ['static/description/tropipaylogo.png'],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}

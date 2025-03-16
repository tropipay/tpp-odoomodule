# -*- coding: utf-8 -*-
#############################################################################
#
#   TropiPay.
#   soporte@tropipay.com
#
#
#############################################################################
import code

import requests
import logging

from odoo import fields, models, _, Command

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    def _get_tpp_currency_domain(self):
        return [('id', 'in', [self.env.ref('base.USD').id, self.env.ref('base.EUR').id])]

    code = fields.Selection(
        selection_add=[('tpp', "(tpp) Tropipay")],
        ondelete={'tpp': 'set default'}
    )
    client_id = fields.Char(string='ClientId')
    client_secret = fields.Char(string='ClientSecret')
    tpp_currency_id = fields.Many2one('res.currency', string='Currency',
                                      domain=lambda self: self._get_tpp_currency_domain(),
                                      readonly=False)
    tpp_payment_method = fields.Selection(
        [('TPP', 'TropiPay Wallet'), ('TPP_GIFTCARD', 'TropiPay Gift Card'), ('EXT', 'Credit Card'), ('ALL', 'All')],
        string='Payment Method', default='ALL')

    def _tpp_base_url(self):
        """
        Get the base URL for the TropiPay API depending on the state of the record.

        :return: The TropiPay API base URL. Returns the production URL if the state is 'enabled',
                 otherwise returns the development URL.
        :rtype: str
        """
        self.ensure_one()
        return 'https://www.tropipay.com/api/v2' if self.state == 'enabled' else 'https://tropipay-dev.herokuapp.com/api/v2'

    def _get_tpp_scopes(self):
        """
        Get the API scopes for TropiPay.

        @override: To add other TropiPay API scopes if needed.

        :return: The TropiPay API scope as a string.
        :rtype: str
        """
        self.ensure_one()
        return "ALLOW_EXTERNAL_CHARGE"

    def _get_tpp_access_token(self):
        """ Return the TropiPay access Token according to the provider.

        Note: self.ensure_one()

        :return: TropiPay access token
        :rtype: str
        """
        self.ensure_one()

        client_id = self.client_id
        client_secret = self.client_secret

        _logger.info(f'**Using Tpp client id: {client_id}. State mode: {self.state}')

        base_api_url = self._tpp_base_url() + '/access/token'

        scope = self._get_tpp_scopes()

        response = requests.post(base_api_url, json={
            "grant_type": "client_credentials",
            "client_id": f"{client_id}",
            "client_secret": f"{client_secret}",
            "scope": scope
        })
        _logger.info("TropiPay Login Response: %s", response.json())

        response.raise_for_status()
        data = response.json()

        return data.get('access_token', False)

    def _get_unavailable_tpp_payment_methods(self):
        """
        Get the list of unavailable TropiPay (TPP) payment methods.

        :return: A list of unavailable payment methods.
        :rtype: list[str]
        """
        return ['ALL']

    def _get_tpp_payment_methods(self):
        """
        Get the list of TropiPay (TPP) payment methods based on the selected payment method.

        :return: A list of payment methods. If the selected method is 'ALL', it returns all available
                 payment methods except those marked as unavailable. Otherwise, it returns a list
                 containing the selected payment method.
        :rtype: list[str]
        """
        self.ensure_one()

        available_methods = [method[0] for method in self._fields['tpp_payment_method'].selection]
        unavailable_methods = self._get_unavailable_tpp_payment_methods()

        if self.tpp_payment_method == 'ALL':
            return [method for method in available_methods if method not in unavailable_methods]

        return [self.tpp_payment_method]


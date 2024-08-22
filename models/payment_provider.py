# -*- coding: utf-8 -*-
#############################################################################
#
#   TropiPay.
#   soporte@tropipay.com
#
#
#############################################################################


from odoo import fields, models, api, _


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('tpp', "(tpp) Tropipay")],
        ondelete={'tpp': 'set default'}
    )
    client_id = fields.Char(string='ClientId')
    client_secret = fields.Char(string='ClientSecret')

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res['tpp'] = {'mode': 'unique', 'domain': [('type', '=', 'bank')]}
        return res

    @api.model
    def _get_compatible_providers(self, *args, currency_id=None, **kwargs):
        """Decide whether to show Tropipay as an option or not"""
        providers = super()._get_compatible_providers(
            *args, currency_id=currency_id, **kwargs
        )
        """
        We want to show Tropipay only for companies whose main currency is "EUR".
        In case we select a different currency during an order,
        we just convert the amount life to "EUR" on transaction creation.
        """
        currency = self.main_currency_id
        if currency and currency.name != "EUR":
            providers = providers.filtered(lambda x: x.code != 'tpp')
        return providers

    def _tpp_get_api_url(self):
        """ Return the API URL according to the provider state.
        Note: self.ensure_one()
        :return: The API URL
        :rtype: str
        """
        website_id = self.env['website'].get_current_website()
        for sel in self.filtered(lambda x: x.website_id == website_id):
            sel.ensure_one()
            if sel.state == 'enabled':
                return 'https://www.tropipay.com/api/v2/access/token'
            else:
                return 'https://tropipay-dev.herokuapp.com/api/v2/access/token'

    def _tpp_get_endpoint_url(self):
        """ Return the ENDPOINT URL according to the provider state.
        Note: self.ensure_one()
        :return: The API URL
        :rtype: str
        """
        website_id = self.env['website'].get_current_website()
        for sel in self.filtered(lambda x: x.website_id == website_id):
            sel.ensure_one()

            if sel.state == 'enabled':
                return 'https://www.tropipay.com/api/v2/paymentcards'
            else:
                return 'https://tropipay-dev.herokuapp.com/api/v2/paymentcards'


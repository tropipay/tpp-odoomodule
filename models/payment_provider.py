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
        # Odoo 17: esta información se define por CÓDIGO DE PROVEEDOR.
        # Declaramos la configuración de 'tpp' y dejamos el modo 'multiple'
        # para que la UI "Activar métodos de pago" permita elegir los
        # métodos soportados (p.ej., 'tpp_card').
        res['tpp'] = {'mode': 'multiple', 'domain': []}
        return res

    def _get_supported_payment_method_codes(self):
        """Declare supported payment method codes for Odoo 17 selection.
        Ensure 'card' and custom 'tpp_card' are available when creating a payment method line.
        """
        codes = super()._get_supported_payment_method_codes()
        # In Odoo 17 this is typically a set
        try:
            codes.add('card')
            codes.add('tpp_card')
        except Exception:
            if 'card' not in codes:
                codes.append('card')
            if 'tpp_card' not in codes:
                codes.append('tpp_card')
        return codes

    def _tpp_get_api_url(self):
        """ Return the API URL according to the provider state.
        Note: self.ensure_one()
        :return: The API URL
        :rtype: str
        """
        self.ensure_one()

        if self.state == 'enabled':
            return 'https://www.tropipay.com/api/v2/access/token'
        else:
            return 'https://tropipay-dev.herokuapp.com/api/v2/access/token'

    def _get_redirect_form_view(self, is_validation=False, **kwargs):
        """Odoo 17: devolver la vista de redirección usada en el flujo de pago.
        La firma debe aceptar is_validation y **kwargs.
        """
        self.ensure_one()
        return self.env.ref('tpp-odoomodule.redirect_form')

    def _tpp_get_endpoint_url(self):
        """ Return the ENDPOINT URL according to the provider state.
        Note: self.ensure_one()
        :return: The API URL
        :rtype: str
        """
        self.ensure_one()

        if self.state == 'enabled':
            return 'https://www.tropipay.com/api/v2/paymentcards'
        else:
            return 'https://tropipay-dev.herokuapp.com/api/v2/paymentcards'

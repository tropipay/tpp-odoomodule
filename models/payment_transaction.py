# -*- coding: utf-8 -*-
#############################################################################
#
#   TropiPay.
#   soporte@tropipay.com
#
#
#############################################################################

import hashlib
import logging
from odoo import _, models, fields
from odoo.exceptions import ValidationError
from odoo.tools import float_round

# Import required libraries (make sure it is installed!)
import requests
import json
from datetime import datetime
import random

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'tpp':
            return res
        return self.execute_payment()

    def execute_payment(self):
        """Fetching data and Executing Payment"""
        endpoint_url = self.env['payment.provider'].search([('code', '=', 'tpp')])._tpp_get_endpoint_url()
        _logger.debug("*****ENDPOINT ********************")
        _logger.debug(endpoint_url)
        odoo_base_url = \
            self.env['website'].browse(self.env.context.get('website_id')).domain or \
            self.env['ir.config_parameter'].get_param('web.base.url')
        # TODO: sale_order is never used (!) --> delete ?
        sale_order = self.env['payment.transaction'].search(
            [('id', '=', self.id)]).sale_order_ids

        order_line = self.env['payment.transaction'].search(
            [('id', '=', self.id)]).sale_order_ids.order_line

        # TODO: invoice_items is never used (!) --> delete ?
        invoice_items = [
            {
                'ItemName': rec.product_id.name,
                'Quantity': int(rec.product_uom_qty),
                'UnitPrice': rec.price_unit,
            }
            for rec in order_line
        ]

        sec = self.login()
        token = sec.get('access_token', '')
        headers = {
            "Content-Type": "application/json",
            'Authorization': f'Bearer {token}'
        }
        amount = self.amount
        ahora = datetime.now()
        fecha = ahora.strftime("%Y-%m-%d")
        _logger.debug(
            "Mostrando country:\n%s",
            self.partner_id.country_id.code)
        _logger.debug(f' La fecha que viene{fecha}')
        payload = {
            "reference": self.reference,
            "concept": "Compra en la web",
            "favorite": False,
            "description": "Compra de productos en la tienda en linea",
            # Amount in EUR, in cents.
            "amount": int(float_round(self._convert_to_eur(amount, self.currency_id.name, "EUR"), precision_digits=2) * 100),
            "currency": "EUR",
            "singleUse": True,
            "reasonId": 34,
            "expirationDays": 1,
            "lang": "es",
            "urlSuccess": f"{odoo_base_url}/payment/tpp/_return_url",
            "urlFailed": f"{odoo_base_url}/payment/tpp/failed",
            "urlNotification": f"{odoo_base_url}/payment/tpp/_information_url",
            "serviceDate": fecha,
            "directPayment": True,
            "client": {
                "name": self.partner_id.get_partner_name(),
                "lastName": self.partner_id.get_partner_surname(),
                "address": self.partner_address,
                "phone": self.partner_phone or self.partner_id.mobile,
                "email": self.partner_email,
                "countryIso": self.partner_id.country_id.code,
                "termsAndConditions": "true",
                "city": self.partner_id.city_id.name or self.partner_id.city,
                "postCode": int(self.partner_id.zip_id.name or self.partner_id.zip),
            }
        }
        self.partner_id.check_client_details_tropipay()
        _logger.debug(endpoint_url)
        _logger.debug(payload)
        response = requests.post(endpoint_url, json=payload, headers=headers)
        _logger.debug("Tropipay response:" + str(response.text))
        # If we receive an error we block that payment method but we can choose another one
        if not str(response.status_code).startswith("2"):
            _logger.error("Tropipay error:" + str(response.text))
            raise ValidationError("")

        _logger.debug("La URL corta obtenida es")
        _logger.debug(response)
        _logger.debug(response.json())
        rendering_values = {
            'api_url': response.json()["shortUrl"],
            'payment_url': response.json()["paymentUrl"],
        }
        return rendering_values

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Getting  payment status from tropipay"""
        # Deserialize the JSON string
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'tpp' or len(tx) == 1:
            return tx
        notification_data_dict = json.loads(notification_data)
        _logger.debug("asdfasf: %s", notification_data_dict)

        # Access the payment_status field
        payment_status = notification_data_dict['data']['state']
        _logger.debug("payment_status: %s", payment_status)
        # payment_status = notification_data['state'] #5 cuando el pago se realizo correctamente
        website_id = self.env['website'].get_current_website()
        _logger.debug("mi clientid: %s", self.env['payment.provider'].search([('code', '=', 'tpp'), ('website_id', '=', website_id.id)]).client_id)
        clientid = self.env['payment.provider'].search([('code', '=', 'tpp'), ('website_id', '=', website_id.id)]).client_id
        clientsecret = self.env['payment.provider'].search([('code', '=', 'tpp'), ('website_id', '=', website_id.id)]).client_secret
        bankOrderCode = notification_data_dict['data']['bankOrderCode']
        originalCurrencyAmount = notification_data_dict['data']['originalCurrencyAmount']
        # Concatenar los valores
        data = "{}{}{}{}".format(bankOrderCode, clientid, clientsecret, originalCurrencyAmount)
        _logger.info("data: {}".format(data))
        # Calcular la firma utilizando SHA256
        signature = hashlib.sha256(data.encode()).hexdigest()
        _logger.info("misignature: {}".format(signature))
        _logger.info("Firma remota: {}, Firma local: {}".format(notification_data_dict['data']['signaturev2'], signature))
        reference = notification_data_dict['data']['reference']
        if signature != notification_data_dict['data']['signaturev2']:
            _logger.info("TPP: Signature does not match")
            raise ValidationError(
                "tpp: " + _(
                    "Invalid Signature %s.",
                    reference)
            )
        _logger.info("reference: %s", reference)
        tx = self.search(
            [
                ('reference', '=', reference),
                ('provider_code', '=', 'tpp')])
        if not tx:
            raise ValidationError(
                "tpp: " + _(
                    "No transaction found matching reference %s.",
                    reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        super()._process_notification_data(notification_data)
        if self.provider_code != 'tpp':
            return
        else:
            self._set_done()

    def _handle_notification_data(self, provider_code, notification_data):

        tx = self._get_tx_from_notification_data(provider_code,
                                                 notification_data)
        tx._process_notification_data(notification_data)
        tx._execute_callback()
        return tx

    def _convert_to_eur(self, amount, currency_orig, currency_dest="EUR"):
        currency_orig = self.env['res.currency'].search([('name', '=', currency_orig)], limit=1)
        currency_dest = self.env['res.currency'].search([('name', '=', currency_dest)], limit=1)
        # Minimize probability to have outdated exchange rate, but don't call with every transaction.
        if random.randint(1, 100) == 1:
            self.env['res.config.settings'].search([], limit=1).update_currency_rates_manually()
        res = currency_orig._convert(
            amount, currency_dest, self.company_id, fields.Date.today()
        )
        return res

    def login(self):
        website_id = self.env['website'].get_current_website()
        base_api_url = self.env['payment.provider'].search([('code', '=', 'tpp'), ('website_id', '=', website_id.id)])._tpp_get_api_url()
        client_id = self.env['payment.provider'].search([('code', '=', 'tpp'),('website_id', '=', website_id.id)]).client_id
        client_secret = self.env['payment.provider'].search([('code', '=', 'tpp'),('website_id', '=', website_id.id)]).client_secret
        scope = "ALLOW_EXTERNAL_CHARGE"
        grandtype = "client_credentials"
        response = requests.post(base_api_url, json={
            "grant_type": grandtype,
            "client_id": f"{client_id}",
            "client_secret": f"{client_secret}",
            "scope": scope
        })
        data = response.json()
        _logger.debug("******LOS DATOS PARA VER SI SE AUTENTICO EN TROPIPAY*****")
        _logger.debug(data)
        _logger.debug(base_api_url)
        _logger.debug(client_id)
        _logger.debug(client_secret)
        _logger.debug("******FIN DE LOS DATOS *****")
        return data

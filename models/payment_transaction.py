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
import requests
from datetime import datetime

from odoo import _, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'tpp':
            return res
        return self._execute_payment()

    def _get_tpp_amount(self):
        amount = self.amount
        currency_id = self.currency_id
        to_currency = self.provider_id.tpp_currency_id

        rate = self.currency_id._get_conversion_rate(
            from_currency=currency_id,
            to_currency=to_currency,
            company=self.company_id,
            date=fields.Date.today()
        )
        final_amount = rate * amount

        return payment_utils.to_minor_currency_units(final_amount, to_currency)

    def _execute_payment(self):
        """Fetching Payment Provider redirect URL"""

        try:
            token = self.provider_id._get_tpp_access_token()
            if not token:
                raise ValidationError(_('No TPP access token found.'))
        except Exception as e:
            _logger.error(e)
            raise ValidationError(_('Invalid TPP access token.'))

        headers = {
            "Content-Type": "application/json",
            'Authorization': f'Bearer {token}'
        }

        now_time = datetime.now()
        service_date = now_time.strftime("%Y-%m-%d")

        payload = {
            "reference": self.reference,
            "concept": "Compra en la web",
            "favorite": False,
            "description": "Compra de productos en la tienda en linea",
            "amount": self._get_tpp_amount(),
            "currency": self.currency_id.name,
            "singleUse": True,
            "reasonId": 34,
            "expirationDays": 1,
            "lang": "es",
            "urlSuccess": f"{self.get_base_url()}/payment/status",
            "urlFailed": f"{self.get_base_url()}/payment/status",
            "urlNotification": f"{self.get_base_url()}/payment/tpp/_information_url",
            "serviceDate": service_date,
            "directPayment": True,
            "paymentMethods": self.provider_id._get_tpp_payment_methods(),
        }

        if self.partner_id:
            payload['client'] = {
                "name": self.partner_name,
                "lastName": ' ',
                "address": self.partner_address,
                "phone": self.partner_phone,
                "email": self.partner_email,
                "countryIso": self.partner_id.country_id.code,
                "termsAndConditions": "true",
                "postCode": self.partner_id.zip,
                "city": self.partner_id.city
            }

        _logger.info(payload)
        try:
            endpoint_url = self.provider_id._tpp_base_url() + '/paymentcards'

            response = requests.post(endpoint_url, json=payload, headers=headers)
            response.raise_for_status()

            return {
                'api_url': response.json()["shortUrl"],
                'payment_url': response.json()["paymentUrl"],
            }

        except Exception as e:
            _logger.error(e)
            raise UserError(_("An error occurred while generating the payment link."))

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Getting  payment status from tropipay"""
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'tpp' or len(tx) == 1:
            return tx

        reference = notification_data.get('data', {}).get('reference')

        tx = self.search([('reference', '=', reference), ('provider_code', '=', provider_code)])
        if not tx:
            raise ValidationError(
                "Tropipay: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on TropiPay notification_data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'tpp':
            return

        if not notification_data:
            self._set_canceled(_("The customer left the payment page."))
            return

        data = notification_data.get('data', {})

        self._validate_payment_signature(notification_data=data)

        status = notification_data.get('status')

        if status == 'OK':
            self._set_done()
        else:
            payment_status = int(data.get('state'))

            gateway_message = self._check_tpp_state(payment_status)
            error_reason = data.get('errorReason', '')

            if payment_status == 4:
                self._set_error(state_message=gateway_message + error_reason)
            else:
                _logger.info(
                    "received data with invalid payment status (%s) for transaction with reference %s",
                    gateway_message, self.reference
                )
                self._set_error(
                    "TropiPay: " + _("Received data with invalid payment status: %s", gateway_message)
                )

    def _validate_payment_signature(self, notification_data):
        """
        Check if the signatures and/or data received from the TropiPay service match
        :param notification_data:
        :return:
        """

        bank_order_code = notification_data.get('bankOrderCode', 'N/A')
        original_currency_amount = notification_data.get('originalCurrencyAmount', 0)

        data = "{}{}{}{}".format(bank_order_code, self.provider_id.client_id, self.provider_id.client_secret,
                                 original_currency_amount)
        # Calculate signature using SHA256 , local signature
        signature = hashlib.sha256(data.encode()).hexdigest()

        reference = notification_data.get('reference', '')
        # Get remote signature
        signature_v2 = notification_data.get('signaturev2', '')

        if signature != signature_v2:
            raise ValidationError(
                "TropiPay: " + _(
                    "We're sorry, your payment cannot be processed due to a verification data discrepancy. "
                    "Fraud has been detected, if you believe this is an error, please contact customer service "
                    "using the reference number: %s.",
                    reference)
            )
        _logger.info("reference: %s", reference)

        # Update the provider reference.
        bank_order_code = notification_data.get('bankOrderCode')
        # txn_type = notification_data.get('txn_type')
        if not bank_order_code:
            raise ValidationError(
                "TropiPay: " + _(
                    "Missing value for Bank Order Code (%(bank_order_code)s).",
                    bank_order_code=bank_order_code
                )
            )
        self.provider_reference = bank_order_code

    @staticmethod
    def _check_tpp_state(tpp_id):
        states = {
            1: _("The order has been created and is being processed in the bank."),
            2: _("The order has been charged and the corresponding payment has been made in the bank."),
            3: _("The order has been successfully paid and the payment process has been completed in the bank."),
            4: _("An error occurred during the processing of the order. Please contact customer service to resolve "
                 "the issue. "),
            5: _("The order is in a pending state at a specific stage of the process. Please wait for that stage to be "
                 "completed.")
        }

        return states.get(tpp_id, "The provided ID is not valid.")

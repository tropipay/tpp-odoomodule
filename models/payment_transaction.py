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
import pprint

from werkzeug import urls

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.http import request
# Import required libraries (make sure it is installed!)
import requests
import json
import time
import sys
from datetime import datetime

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
        _logger.info("*****ENDPOINT ********************")
        _logger.info(endpoint_url)
        odoo_base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        sale_order = self.env['payment.transaction'].search(
            [('id', '=', self.id)]).sale_order_ids

        order_line = self.env['payment.transaction'].search(
            [('id', '=', self.id)]).sale_order_ids.order_line

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
        ahora=datetime.now()
        fecha = ahora.strftime("%Y-%m-%d")
        _logger.info("Mostrando country:\n%s",
                     self.partner_id.country_id.code)
        _logger.info(f' La fecha que viene{fecha}')
        # Extraer first_name y last_name de partner_name
        name_parts = self.partner_name.split()
        first_name = name_parts[0] if name_parts else ''
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else '.'

        # TropiPay espera monto en centavos; usar entero
        amount_cents = int(round(amount * 100))
        payload = {
            "reference": self.reference,
            "concept": "Compra en la web",
            "favorite": False,
            "description": "Compra de productos en la tienda en linea",
            "amount": amount_cents,
            "currency": self.currency_id.name,
            "singleUse": True,
            "reasonId": 34,
            "expirationDays": 1,
            "lang": "es",
            "urlSuccess": f"{odoo_base_url}/payment/tpp/_return_url",
            "urlFailed": f"{odoo_base_url}/payment/tpp/failed",
            #urlNotification": "https://webhook.site/bc45e9cd-5bf0-432f-994e-4f86e762788f",
            #"urlNotification": f"{odoo_base_url}/payment/tpp/call-back",
            "urlNotification": f"{odoo_base_url}/payment/tpp/_information_url",
            "serviceDate": fecha,
            "directPayment": True,
            "client": {
                "name": first_name,
                "lastName": last_name,
                "address": self.partner_address,
                "phone": self.partner_phone,
                "email": self.partner_email,
                "countryIso": self.partner_id.country_id.code,
                "termsAndConditions": "true",
                "postCode": self.partner_id.zip,
                "city": self.partner_id.city
            }
        }
        _logger.info(endpoint_url)
        _logger.info(payload)
        try:
            response = requests.post(endpoint_url, json=payload, headers=headers, timeout=30)
        except requests.RequestException as e:
            _logger.exception("Error conectando con TropiPay")
            raise ValidationError(_(f"No se pudo conectar con TropiPay: {e}"))
        if not response.ok:
            _logger.error("Respuesta HTTP no OK de TropiPay: %s - %s", response.status_code, response.text)
            raise ValidationError(_(f"Error de TropiPay ({response.status_code}): {response.text}"))
        try:
            data = response.json()
        except ValueError:
            _logger.error("Respuesta de TropiPay no es JSON: %s", response.text)
            raise ValidationError(_(f"Respuesta inválida de TropiPay"))
        short_url = data.get("shortUrl")
        payment_url = data.get("paymentUrl")
        if not short_url and not payment_url:
            _logger.error("Faltan URLs de pago en respuesta TropiPay: %s", data)
            raise ValidationError(_(f"TropiPay no devolvió URL de pago"))
        rendering_values = {
            'api_url': short_url or payment_url,
            'payment_url': payment_url or short_url,
        }
        return rendering_values


    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Getting  payment status from tropipay"""
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'tpp' or len(tx) == 1:
            return tx
        # En Odoo 17 podemos recibir un dict directamente (type='json')
        if isinstance(notification_data, (bytes, str)):
            try:
                notification_data_dict = json.loads(notification_data)
            except Exception:
                notification_data_dict = {}
        else:
            notification_data_dict = notification_data or {}
        _logger.info("asdfasf: %s", notification_data_dict)

        # Access the payment_status field
        payment_status = (notification_data_dict.get('data') or {}).get('state')
        _logger.info("payment_status: %s", payment_status)
        # payment_status = notification_data['state'] #5 cuando el pago se realizo correctamente
        _logger.info("mi clientid: %s", self.env['payment.provider'].search([('code', '=', 'tpp')]).client_id)
        clientid = self.env['payment.provider'].search([('code', '=', 'tpp')]).client_id
        clientsecret = self.env['payment.provider'].search([('code', '=', 'tpp')]).client_secret
        inner = notification_data_dict.get('data') or {}
        bankOrderCode = inner.get('bankOrderCode')
        originalCurrencyAmount = inner.get('originalCurrencyAmount')
        # Concatenar los valores
        data = "{}{}{}{}".format(bankOrderCode,clientid,clientsecret,originalCurrencyAmount)

        # Calcular la firma utilizando SHA256
        signature = hashlib.sha256(data.encode()).hexdigest() if all([bankOrderCode, clientid, clientsecret, originalCurrencyAmount]) else None
        _logger.info("misignature: {}".format(signature))
        _logger.info("Firma remota: {}, Firma local: {}".format(inner.get('signaturev2'),signature))
        reference = inner.get('reference')
        if not signature or signature != inner.get('signaturev2'):
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
        # Mapear estados de TropiPay
        # Esperado: notification_data dict con clave 'data' y 'state'
        inner = {}
        try:
            if isinstance(notification_data, (bytes, str)):
                inner = (json.loads(notification_data) or {}).get('data') or {}
            else:
                inner = (notification_data or {}).get('data') or {}
        except Exception:
            inner = {}
        state = inner.get('state')
        # Considerar como pagado si state en {5, 'PAID', 'paid'}; cancelar si {3, 'CANCELLED', 'FAILED'}
        paid_states = {5, 'PAID', 'paid', 'APPROVED', 'Approved'}
        failed_states = {3, 'CANCELLED', 'FAILED', 'Canceled', 'Declined'}
        if state in paid_states:
            self._set_done()
        elif state in failed_states:
            self._set_canceled()
        else:
            # Dejar pendiente si no se reconoce
            _logger.info("Estado TropiPay no reconocido, se deja pendiente: %s", state)

    def _handle_notification_data(self, provider_code, notification_data):

        tx = self._get_tx_from_notification_data(provider_code,
                                                 notification_data)
        tx._process_notification_data(notification_data)
        tx._execute_callback()
        return tx


    def login(self):
        base_api_url = self.env['payment.provider'].search([('code', '=', 'tpp')])._tpp_get_api_url()
        client_id = self.env['payment.provider'].search([('code', '=', 'tpp')]).client_id
        client_secret = self.env['payment.provider'].search([('code', '=', 'tpp')]).client_secret
        scope = "ALLOW_EXTERNAL_CHARGE"
        grandtype = "client_credentials"
        response = requests.post(base_api_url, json={
            "grant_type": grandtype,
            "client_id": f"{client_id}",
            "client_secret": f"{client_secret}",
            "scope": scope
        })
        data = response.json()
        _logger.info("******LOS DATOS PARA VER SI SE AUTENTICO EN TROPIPAY*****")
        _logger.info(data)
        _logger.info(base_api_url)
        _logger.info(client_id)
        _logger.info(client_secret)
        _logger.info("******FIN DE LOS DATOS *****")
        return data

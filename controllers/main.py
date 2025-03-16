# -*- coding: utf-8 -*-
#############################################################################
#
#   TropiPay.
#   soporte@tropipay.com
#   
#
#############################################################################


import logging
import pprint
import json
import requests
from odoo import http
from odoo.http import request
import ast

_logger = logging.getLogger(__name__)


class PaymentTppController(http.Controller):
    _information_url = '/payment/tpp/_information_url'

    @http.route(_information_url, type='json', auth='public', methods=['GET', 'POST'], csrf=False)
    def tpp_checkout(self):
        try:
            json_data = json.loads(request.httprequest.data)

            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'tpp', json_data
            )

            tx_sudo._handle_notification_data('tpp', json_data)

            return request.make_json_response({
                'success': True,

            }, status=200)

        except Exception as e:
            return request.make_json_response({
                'success': False,
                'message': str(e),
            }, status=500)

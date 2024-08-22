# -*- coding: utf-8 -*-
#############################################################################
#
#   TropiPay.
#   soporte@tropipay.com
#
#############################################################################


import logging
import json
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaymentTppController(http.Controller):
    _return_url = '/payment/tpp/_return_url'
    _information_url = '/payment/tpp/_information_url'

    @http.route(_return_url, type='http', auth='public',
                methods=['GET'])
    def tpp__checkout(self, **data):
        return request.redirect('/payment/status')

    @http.route(_information_url, type='json', auth='public',
                methods=['GET', 'POST'], csrf=False)
    def tpp__checkout2(self, **data):
        _logger.debug("Cuerpo de la solicitud HTTP: %s", request.httprequest.data)
        data_dict = json.loads(request.httprequest.data)  # convierte la cadena JSON a un diccionario
        status = data_dict['status']  # 'OK'
        if status == 'OK':
            data_dict = data_dict['data']  # {'id': 383663, 'reference': 'S00047'}
            data_id = data_dict['id']  # 383663
            data_reference = data_dict['reference']  # 'S00047'
            _logger.debug(
                "status, id, reference: %s %s %s",
                status,
                data_id,
                data_reference)
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data('tpp', request.httprequest.data)
            tx_sudo._handle_notification_data('tpp', request.httprequest.data)
        # return request.redirect('/payment/status')
        return {'status': 'OK'}, 200

    @http.route('/payment/tpp/failed', type='http', auth='user',
                website=True, )
    def payment_failed(self, redirect=None):
        return request.redirect('/error-al-pagar')

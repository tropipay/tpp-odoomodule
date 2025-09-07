# -*- coding: utf-8 -*-
#############################################################################
#
#   TropiPay.
#   soporte@tropipay.com
#   
#
#############################################################################


import logging
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
    
    
    @http.route(_information_url, type='http', auth='public',
                methods=['GET', 'POST'], csrf=False)
    def tpp__checkout2(self, **data):
        # Webhook externo: parsear JSON desde el cuerpo raw; si falla, usar form/query
        payload = {}
        try:
            raw = request.httprequest.get_data(cache=False, as_text=True) or ''
            if raw:
                import json as _json
                payload = _json.loads(raw)
        except Exception:
            payload = {}
        if not payload:
            # form-urlencoded
            try:
                payload = request.httprequest.form.to_dict() or {}
            except Exception:
                payload = {}
        if not payload and data:
            payload = data
        status = payload.get('status')
        if status == 'OK':
            request.env['payment.transaction'].sudo()._handle_notification_data('tpp', payload)
        return request.make_json_response({'status': 'OK'})

    @http.route('/payment/tpp/failed', type='http', auth='user',
                website=True, )
    def payment_failed(self, redirect=None):
       # return request.render("tpp_payment_gateway.tpp_payment_gateway_failed_form")
        #return request.redirect('/payment/status')error-al-pagar
        return request.redirect('/error-al-pagar')

# Copyright 2024 Alejandra García <alejandra.gracia@qubiq.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models, api, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.partner'

    def split_display_name(self):
        for record in self:
            if record.display_name:
                split_name = record.display_name.split()
                return split_name

    def get_partner_name(self):
        split_name = self.split_display_name()
        name = split_name[0] if len(split_name) > 1 else ''
        return name

    def get_partner_surname(self):
        split_name = self.split_display_name()
        surname = ' '.join(split_name[1:]) if len(split_name) > 1 else ''
        return surname

    @api.constrains('display_name', 'street', 'street2', 'phone', 'mobile', 'email', 'website_id', 'country_id', 'zip', 'city_id')
    def _check_client_details_tropipay(self):
        """Method to check necessary details from the client to make a payment through Tropipay when creating an user through backend."""
        for record in self:
            if not record.website_id:
                continue

            tropipay_payment_provider = self.env['payment.provider'].search([
                ('code', '=', 'tpp'),
                ('website_id', '=', record.website_id.id)
            ], limit=1)

            if tropipay_payment_provider.state in ['test', 'enabled']:
                record.check_client_details_tropipay()

    def check_client_details_tropipay(self):
        """Method to check necessary details from the client to make a payment through Tropipay from website when tropipay is selected."""
        for record in self:
            missing_fields = []
            field_checks = {
                _("Name"): record.get_partner_name(),
                _("Surname"): record.get_partner_surname(),
                _("Address"): record.street or record.street2,
                _("Phone"): record.phone or record.mobile,
                _("Email"): record.email,
                _("Country"): record.country_id.code,
                _("Postcode"): record.zip,
                _("City"): record.city_id.name or record.city,
            }

            missing_fields = [field for field, value in field_checks.items() if not value]

            if missing_fields:
                missing_fields_str = ', '.join(missing_fields)
                if len(missing_fields) == 1:
                    error_message = _(f"The field '{missing_fields[0]}' is required.")
                else:
                    error_message = _(f"The fields '{missing_fields_str}' are required.")
                raise ValidationError(error_message)

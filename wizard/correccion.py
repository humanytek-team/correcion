# -*- coding: utf-8 -*-
###############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2017 Humanytek (<www.humanytek.com>).
#    Rubén Bravo <rubenred18@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import base64
_logger = logging.getLogger(__name__)


class Correccion(models.TransientModel):
    _name = "correccion"

    name = fields.Char('File Name')
    data_file = fields.Binary('File')
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],
                            default='choose')
    impuesto_pagado_id = fields.Many2one('account.account',
        company_dependent=True,
        string="Iva efectivamente pagado")
    impuesto_pendiente_id = fields.Many2one('account.account',
        company_dependent=True,
        string="Iva pendiente de pago")

    @api.multi
    def confirm(self):
        ProductProduct = self.env['product.product']
        AccountMove = self.env['account.move']
        data_file = self.data_file
        data_file_decoded = base64.b64decode(data_file)
        aux = data_file_decoded.split('\n')
        num_line = 0
        list_projects = []
        for line in aux[:-1]:
            if num_line == 0:
                line_aux = line.split(';')
                num_line += 1
                continue
            num_line += 1
            column = line.split(';')
            account_moves = AccountMove.search([('name', '=', column[0])])
            for move in account_moves:
                move.button_cancel()

                aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
                invoice_currency = move.currency_id
                debit, credit, amount_currency, currency_id = aml_obj.with_context(date=move.date).compute_amount_fields(move.amount, move.currency_id, move.company_id.currency_id, invoice_currency)


                aml_dict = self._get_shared_move_line_unidentified(debit, credit, amount_currency, move, False, 0)
                #aml_dict.update(self._get_counterpart_move_line_unidentified())
                aml_dict.update({'currency_id': currency_id})
                aml = aml_obj.create(aml_dict)

                counterpart_aml_dict = self._get_shared_move_line_unidentified(credit, debit, amount_currency, move, False, 1)
                #counterpart_aml_dict.update(self._get_move_line_unidentified())
                counterpart_aml_dict.update({'currency_id': currency_id})
                counterpart_aml = aml_obj.create(counterpart_aml_dict)
            move.post()
            #products = ProductProduct.search([('default_code', '=', column[0])])
            #if products:
                #if products.id not in list_projects:
                    #SaleForecast.search(
                        #[('product_id.id', '=', products.id)]).unlink()
                    #products.write(
                        #{'mps_active': True, 'apply_active': True})
                    #list_projects.append(products.id)
                #try:
                    #cont = 1
                    #for col in column[1:]:
                        #SaleForecast.create({
                                    #'product_id': products.id,
                                    #'date': line_aux[cont].strip(),
                                    #'forecast_qty': col.strip()})
                        #cont += 1
                #except:
                    #error = 'check the line: ' + str(num_line)
                    #raise UserError(_(error))
                #continue
            #else:
                #error = 'the product does not exist! line: ' + str(num_line)
                #raise UserError(_(error))

#
    def _get_shared_move_line_unidentified(self, debit, credit, amount_currency, move, invoice_id=False, number=0):
        AccountTax = self.env['account.tax']
        tax = AccountTax.search([('name', '=','IVA(16%) VENTAS')])
        account = False
        base = 0
        ref = []
        name = ''
        for line in move.line_ids:
            ref = line.name
            ref = ref.split(':')
            if len(ref) == 2:
                name = ref[1]
        if debit == 0:
            base = credit / 1.16
        else:
            base = debit / 1.16
        if number == 0:
            account = self.impuesto_pagado_id.id
        else:
            account = self.impuesto_pendiente_id.id
        return {
            'partner_id': move.line_ids[0].payment_id.partner_id.id,
            'invoice_id': False,
            'move_id': move.id,
            'debit': (debit / 1.16) * 0.16,
            'credit': (credit / 1.16) * 0.16,
            'amount_currency': (amount_currency / 1.16) * 0.16 or False,
            'name': 'IVA (16%) VENTAS - Fact: '+name,
            'account_id': account,
            'tax_id_secondary': tax[0].id,
            'payment_id': move.line_ids[0].payment_id.id,
            'amount_base': base,
        }

    def _get_move_line_unidentified(self, invoice=False):
        name = ''
        if self.partner_type == 'customer':
            if self.payment_type == 'inbound':
                name += _("Customer Payment")
            elif self.payment_type == 'outbound':
                name += _("Customer Refund")
        return {
            'name': name,
            'account_id': self.partner_id.account_tax_receivable_id.id,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
            'payment_id': self.id,
        }

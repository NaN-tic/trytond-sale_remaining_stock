#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'
    remaining_stock = fields.Selection([
            ('create_shipment', 'Create Shipment'),
            ('manual', 'Manual'),
            ], 'Remaining Stock',
        states={
            'readonly': ~Eval('state').in_(['draft', 'quotation']),
            }, help='Allow create new pending shipments to delivery')

    @classmethod
    def default_remaining_stock(cls):
        Configuration = Pool().get('sale.configuration')

        config = Configuration(1)
        return config.remaining_stock or 'create_shipment'

    @fields.depends('party', 'shipment_party', 'payment_term')
    def on_change_party(self):
        super(Sale, self).on_change_party()
        Configuration = Pool().get('sale.configuration')

        config = Configuration(1)
        remaining_stock = config.remaining_stock or 'create_shipment'
        self.remaining_stock = remaining_stock

        if self.party:
            self.remaining_stock = (self.party.remaining_stock
                if self.party.remaining_stock else remaining_stock)

    def create_shipment(self, shipment_type):
        # in case remaining_stock is manual, not create new shipments
        if self.remaining_stock == 'manual':
            if (shipment_type == 'out' and self.shipments):
                return
        return super(Sale, self).create_shipment(shipment_type)

    def get_shipment_state(self):
        # Consider as sent if ANY shipment is done
        if (self.moves and self.remaining_stock == 'manual'):
            if (self.shipments and self.shipment_returns):
                if (any(s for s in self.shipments if s.state in ('done', 'cancelled')) and
                        all(s.state in ('received', 'done', 'cancelled') for s in self.shipment_returns)):
                    return 'sent'
            elif self.shipments:
                if any(s for s in self.shipments if s.state in ('done', 'cancelled')):
                    return 'sent'
        return super(Sale, self).get_shipment_state()


class LineCreditLimit(metaclass=PoolMeta):
    __name__ = 'sale.line'

    @property
    def credit_limit_quantity(self):
        quantity = super().credit_limit_quantity
        # The quantity comes from the invoiced line.
        # In cases where remaining_stock is manual, there are no stock.move exceptions.
        # However, sale_credit_limit requires these moves to deduct the quantity,
        # even though they are not finally invoiced.
        if (quantity is not None
                and self.sale.shipment_state == 'sent'
                and self.sale.remaining_stock == 'manual'):
            quantity = sum(i.quantity for i in self.invoice_lines)
        return quantity

#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval

__all__ = ['Sale']


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'
    remaining_stock = fields.Selection([
            ('create_shipment', 'Create Shipment'),
            ('manual', 'Manual'),
            ], 'Remaining Stock',
        states={
            'readonly': ~Eval('state').in_(['draft', 'quotation']),
            },
        depends=['state'],
        help='Allow create new pending shipments to delivery')

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
                if (any(s for s in self.shipments if s.state == 'done') and
                        all(s.state in ('received', 'done') for s in self.shipment_returns)):
                    return 'sent'
            elif self.shipments:
                if any(s for s in self.shipments if s.state == 'done'):
                    return 'sent'
        return super(Sale, self).get_shipment_state()

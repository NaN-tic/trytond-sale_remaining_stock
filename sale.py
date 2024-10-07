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

    @classmethod
    def process(cls, sales):
        pool = Pool()
        SaleLine = pool.get('sale.line')
        ShipmentOut = pool.get('stock.shipment.out')

        super().process(sales)

        for sale in sales:
            if sale.shipment_state == 'sent' and sale.remaining_stock == 'manual':
                shipments = [s for s in sale.shipments if s.state not in ('cancelled', 'done')]
                ShipmentOut.cancel(shipments)
                for line in sale.lines:
                    moves = []
                    skips = set(line.moves_ignored)
                    skips.update(line.moves_recreated)
                    for move in line.moves:
                        if move.state == 'cancelled' and move not in skips:
                            moves.append(move.id)
                    if not moves:
                        continue
                    SaleLine.write([line], {
                            'moves_ignored': [('add', moves)],
                            })

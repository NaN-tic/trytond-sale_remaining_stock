#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction


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
        transaction = Transaction()
        context = transaction.context

        shipments = self.shipments

        # if remaining_stock == manual, not grouping new shipments in case
        # has done or cancelled shipments
        skip_grouping = (self.remaining_stock == 'manual' and shipments
            and any(s for s in self.shipments if s.state in ('done', 'cancelled')))
        with transaction.set_context(skip_grouping=skip_grouping):
            return super().create_shipment(shipment_type)

    @classmethod
    def _process_shipment(cls, sales):
        pool = Pool()
        SaleLine = pool.get('sale.line')
        ShipmentOut = pool.get('stock.shipment.out')

        super()._process_shipment(sales)

        to_ignore = []
        to_cancel = []
        for sale in sales:
            if not sale.remaining_stock == 'manual':
                continue

            # Cancel shipments and add to moves ignored
            if any(s for s in sale.shipments if s.state in ('done', 'cancelled')):
                remaining_stock = set()
                shipments = [s for s in sale.shipments
                    if s.state not in ('cancelled', 'done')]
                if shipments:
                    # Cancel if all outgoing moves are linked to sales where
                    # remaining_stock == 'manual'
                    for shipment in sale.shipments:
                        for move in shipment.outgoing_moves:
                            if move.origin and isinstance(move.origin, SaleLine):
                                remaining_stock.add(move.origin.sale.remaining_stock)
                    if len(remaining_stock) != 1:
                        continue

                    to_cancel += shipments
                to_ignore.append(sale)

        # cancel customer shipments
        if to_cancel:
            ShipmentOut.cancel(to_cancel)

        if to_ignore:
            to_write = []
            for sale in to_ignore:
                for line in sale.lines:
                    moves = []
                    skips = set(line.moves_ignored)
                    skips.update(line.moves_recreated)
                    for move in line.moves:
                        if move.state == 'cancelled' and move not in skips:
                            moves.append(move.id)
                    if not moves:
                        continue
                    to_write.extend(([line], {
                            'moves_ignored': [('add', moves)],
                            }))
            if to_write:
                SaleLine.write(*to_write)

#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from trytond.model import ModelSQL, fields
from trytond.modules.company.model import (CompanyMultiValueMixin,
    CompanyValueMixin)
from trytond.pool import Pool, PoolMeta

__all__ = ['Party', 'PartyRemainingStock']

remaining_stock = fields.Selection([
        ('create_shipment', 'Create Shipment'),
        ('manual', 'Manual'),
        ], 'Remaining Stock',
        help='Allow create new pending shipments to delivery')

def default_func(field_name):
    @classmethod
    def default(cls, **pattern):
        return getattr(
            cls.multivalue_model(field_name),
            'default_%s' % field_name, lambda: None)()
    return default


class Party(CompanyMultiValueMixin, metaclass=PoolMeta):
    __name__ = 'party.party'
    remaining_stock = fields.MultiValue(remaining_stock)
    remaining_stocks = fields.One2Many(
        'party.remaining.stock', 'party', "Remaining Stocks")

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'remaining_stock':
            return pool.get('party.remaining.stock')
        return super(Party, cls).multivalue_model(field)

    default_remaining_stock = default_func('remaining_stock')


class PartyRemainingStock(ModelSQL, CompanyValueMixin):
    "Party Remaining Stock"
    __name__ = 'party.remaining.stock'
    party = fields.Many2One('party.party', 'Party')
    remaining_stock = remaining_stock

    @classmethod
    def default_remaining_stock(cls):
        return 'create_shipment'

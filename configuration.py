#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from trytond.model import ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.modules.company.model import (
    CompanyMultiValueMixin, CompanyValueMixin)

__all__ = ['Configuration', 'ConfigurationRemainingStock']

remaining_stock = fields.Selection([
        ('create_shipment', 'Create Shipment'),
        ('manual', 'Manual'),
        ], 'Remaining Stock',
        help='Allow create new pending shipments to delivey')

def default_func(field_name):
    @classmethod
    def default(cls, **pattern):
        return getattr(
            cls.multivalue_model(field_name),
            'default_%s' % field_name, lambda: None)()
    return default


class Configuration(CompanyMultiValueMixin, metaclass=PoolMeta):
    __name__ = 'sale.configuration'
    remaining_stock = fields.MultiValue(remaining_stock)

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'remaining_stock':
            return pool.get('sale.configuration.remaining.stock')
        return super(Configuration, cls).multivalue_model(field)

    default_remaining_stock = default_func('remaining_stock')


class ConfigurationRemainingStock(ModelSQL, CompanyValueMixin):
    "Sale Configuration Remaining Stock"
    __name__ = 'sale.configuration.remaining.stock'
    remaining_stock = remaining_stock

    @classmethod
    def default_remaining_stock(cls):
        return 'create_shipment'

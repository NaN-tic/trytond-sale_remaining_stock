# This file is part sale_remaining_stock module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import configuration
from . import party
from . import sale

def register():
    Pool.register(
        configuration.Configuration,
        configuration.ConfigurationRemainingStock,
        party.Party,
        party.PartyRemainingStock,
        sale.Sale,
        module='sale_remaining_stock', type_='model')

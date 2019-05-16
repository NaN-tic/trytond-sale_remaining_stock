# This file is part sale_remaining_stock module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import unittest

import doctest

from trytond.tests.test_tryton import ModuleTestCase
from trytond.tests.test_tryton import suite as test_suite
from trytond.tests.test_tryton import doctest_teardown
from trytond.tests.test_tryton import doctest_checker


class SaleRemainingStockTestCase(ModuleTestCase):
    'Test Sale Remaining Stock module'
    module = 'sale_remaining_stock'


def suite():
    suite = test_suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
            SaleRemainingStockTestCase))
    suite.addTests(doctest.DocFileSuite(
            'scenario_sale_remaining_stock.rst',
            tearDown=doctest_teardown, encoding='utf-8',
            checker=doctest_checker,
            optionflags=doctest.REPORT_ONLY_FIRST_FAILURE))
    return suite

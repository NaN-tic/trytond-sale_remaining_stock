import unittest
from decimal import Decimal

from proteus import Model
from trytond.modules.account.tests.tools import (create_chart,
                                                 create_fiscalyear,
                                                 get_accounts)
from trytond.modules.account_invoice.tests.tools import (
    create_payment_term, set_fiscalyear_invoice_sequences)
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Activate modules
        activate_modules(['sale_shipment_grouping', 'sale_remaining_stock'])

        # Create company
        _ = create_company()
        company = get_company()

        # Create fiscal year
        fiscalyear = set_fiscalyear_invoice_sequences(
            create_fiscalyear(company))
        fiscalyear.click('create_period')

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        revenue = accounts['revenue']
        expense = accounts['expense']

        # Create parties
        Party = Model.get('party.party')
        customer = Party(name='Customer')
        customer.save()
        customer_grouped = Party(name='Customer Grouped',
                                 sale_shipment_grouping_method='standard',
                                 remaining_stock = 'manual',
                                 )
        customer_grouped.save()

        # Create account category
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.save()

        # Create product
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        template = ProductTemplate()
        template.name = 'product'
        template.default_uom = unit
        template.type = 'goods'
        template.salable = True
        template.list_price = Decimal('10')
        template.account_category = account_category
        template.save()
        product, = template.products

        # Create payment term
        payment_term = create_payment_term()
        payment_term.save()

        # Create an inventory
        Inventory = Model.get('stock.inventory')
        Location = Model.get('stock.location')
        storage, = Location.find([
            ('code', '=', 'STO'),
        ])
        inventory = Inventory()
        inventory.location = storage
        inventory_line = inventory.lines.new()
        inventory_line.product = product
        inventory_line.quantity = 100.0
        inventory_line.expected_quantity = 0.0
        inventory.click('confirm')
        self.assertEqual(inventory.state, 'done')

        # Sell some products
        Sale = Model.get('sale.sale')
        sale = Sale()
        sale.party = customer
        sale.payment_term = payment_term
        sale.invoice_method = 'order'
        sale_line = sale.lines.new()
        sale_line.product = product
        sale_line.quantity = 2.0
        sale.click('quote')
        sale.click('confirm')
        self.assertEqual(sale.state, 'processing')

        # Make another sale
        sale, = Sale.duplicate([sale])
        sale.click('quote')
        sale.click('confirm')
        self.assertEqual(sale.state, 'processing')

        # Check the shipments
        ShipmentOut = Model.get('stock.shipment.out')
        shipments = ShipmentOut.find([('customer', '=', customer.id)])
        self.assertEqual(len(shipments), 2)
        for shipment in shipments:
            shipment.click('assign_try')
            shipment.click('pick')
            shipment.click('pack')
            shipment.click('done')

        # Now we'll use the same scenario with the grouped customer and manual
        sale1 = Sale()
        sale1.party = customer_grouped
        self.assertEqual(sale1.remaining_stock, 'manual')
        sale1.payment_term = payment_term
        sale1.invoice_method = 'order'
        sale_line = sale1.lines.new()
        sale_line.product = product
        sale_line.quantity = 1.0
        sale1.click('quote')
        sale1.click('confirm')
        self.assertEqual(sale1.state, 'processing')

        # Make another sale
        sale2 = Sale()
        sale2.party = customer_grouped
        self.assertEqual(sale2.remaining_stock, 'manual')
        sale2.payment_term = payment_term
        sale2.invoice_method = 'order'
        sale_line = sale2.lines.new()
        sale_line.product = product
        sale_line.quantity = 2.0
        sale2.click('quote')
        sale2.click('confirm')
        self.assertEqual(sale2.state, 'processing')

        # Check the shipments
        shipments = ShipmentOut.find([
            ('customer', '=', customer_grouped.id),
            ('state', '=', 'waiting'),
        ])
        self.assertEqual(len(shipments), 1)
        shipment, = shipments
        self.assertEqual(len(shipment.outgoing_moves), 2)
        self.assertEqual(sorted([m.quantity for m in shipment.outgoing_moves]),
                         [1.0, 2.0])
        shipment.click('cancel')

        sale1.reload()
        sale2.reload()
        self.assertEqual(len(sale1.shipments), 1)
        self.assertEqual(sale1.shipment_state, 'sent')
        line1, = sale1.lines
        self.assertEqual(len(line1.moves_ignored), 1)
        self.assertEqual(len(sale2.shipments), 1)
        self.assertEqual(sale2.shipment_state, 'sent')
        line2, = sale2.lines
        self.assertEqual(len(line2.moves_ignored), 1)

        # Now we'll use the same scenario with the grouped customer,
        # but mix grouping shipment from manual and create_shipment (not ignore moves)
        sale1 = Sale()
        sale1.party = customer_grouped
        self.assertEqual(sale1.remaining_stock, 'manual')
        sale1.payment_term = payment_term
        sale1.invoice_method = 'order'
        sale_line = sale1.lines.new()
        sale_line.product = product
        sale_line.quantity = 1.0
        sale1.click('quote')
        sale1.click('confirm')
        self.assertEqual(sale1.state, 'processing')

        # Make another sale
        sale2 = Sale()
        sale2.party = customer_grouped
        self.assertEqual(sale2.remaining_stock, 'manual')
        sale2.remaining_stock = 'create_shipment'
        sale2.payment_term = payment_term
        sale2.invoice_method = 'order'
        sale_line = sale2.lines.new()
        sale_line.product = product
        sale_line.quantity = 2.0
        sale2.click('quote')
        sale2.click('confirm')
        self.assertEqual(sale2.state, 'processing')

        # Check the shipments
        shipments = ShipmentOut.find([
            ('customer', '=', customer_grouped.id),
            ('state', '=', 'waiting'),
        ])
        self.assertEqual(len(shipments), 1)
        shipment, = shipments
        self.assertEqual(len(shipment.outgoing_moves), 2)
        self.assertEqual(sorted([m.quantity for m in shipment.outgoing_moves]),
                         [1.0, 2.0])
        shipment.click('cancel')

        # shipment from sale1 is manual and sent
        # shipment from sale2 is create_shipment and exception
        sale1.reload()
        sale2.reload()
        self.assertEqual(len(sale1.shipments), 1)
        self.assertEqual(sale1.shipment_state, 'sent')
        line1, = sale1.lines
        self.assertEqual(len(line1.moves_ignored), 1)
        self.assertEqual(len(sale2.shipments), 1)
        self.assertEqual(sale2.shipment_state, 'exception')
        line2, = sale2.lines
        self.assertEqual(len(line2.moves_ignored), 0)

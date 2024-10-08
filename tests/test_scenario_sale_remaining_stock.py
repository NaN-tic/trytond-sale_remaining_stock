import unittest
from decimal import Decimal

from proteus import Model
from trytond.modules.account.tests.tools import (create_chart,
                                                 create_fiscalyear, create_tax,
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

        # Install sale_remaining_stock
        activate_modules('sale_remaining_stock')

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

        # Create tax
        tax = create_tax(Decimal('.10'))
        tax.save()

        # Create account categories
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.save()
        account_category_tax, = account_category.duplicate()
        account_category_tax.customer_taxes.append(tax)
        account_category_tax.save()

        # Create parties
        Party = Model.get('party.party')
        supplier = Party(name='Supplier')
        supplier.save()
        customer = Party(name='Customer')
        customer.remaining_stock = 'create_shipment'
        customer.save()
        customer2 = Party(name='Customer2')
        customer2.remaining_stock = 'manual'
        customer2.save()

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
        template.account_category = account_category_tax
        template.save()
        product, = template.products
        template = ProductTemplate()
        template.name = 'service'
        template.default_uom = unit
        template.type = 'service'
        template.salable = True
        template.list_price = Decimal('30')
        template.account_category = account_category_tax
        template.save()

        # Create payment term
        payment_term = create_payment_term()
        payment_term.save()

        # Create an Inventory
        Inventory = Model.get('stock.inventory')
        Location = Model.get('stock.location')
        storage, = Location.find([
            ('code', '=', 'STO'),
        ])
        inventory = Inventory()
        inventory.location = storage
        inventory_line = inventory.lines.new(product=product)
        inventory_line.quantity = 100.0
        inventory_line.expected_quantity = 0.0
        inventory.click('confirm')
        self.assertEqual(inventory.state, 'done')

        # Sale Configuration
        Configuration = Model.get('sale.configuration')
        configuration = Configuration(1)
        configuration.remaining_stock = 'create_shipment'
        configuration.save()

        # Sale create shipments
        Sale = Model.get('sale.sale')
        SaleLine = Model.get('sale.line')
        sale = Sale()
        sale.party = customer
        sale.remaining_stock = 'create_shipment'
        sale.payment_term = payment_term
        sale.invoice_method = 'order'
        sale_line = SaleLine()
        sale.lines.append(sale_line)
        sale_line.product = product
        sale_line.quantity = 2.0
        sale_line = SaleLine()
        sale.lines.append(sale_line)
        sale_line.product = product
        sale_line.quantity = 3.0
        sale.click('quote')
        sale.click('confirm')
        sale.click('process')
        self.assertEqual(sale.state, 'processing')
        self.assertEqual(sale.shipment_state, 'waiting')

        shipment, = sale.shipments
        shipment.click('draft')
        move1, move2 = shipment.outgoing_moves
        move1.quantity = 1.0
        shipment.click('wait')
        shipment.click('assign_try')
        shipment.click('pick')
        shipment.click('pack')
        shipment.click('done')
        sale.reload()
        self.assertEqual(len(sale.shipments), 2)
        line1, line2 = sale.lines
        self.assertEqual(len(line1.moves_ignored), 0)
        self.assertEqual(len(line2.moves_ignored), 0)

        # Sale manual shipments
        sale = Sale()
        sale.party = customer2
        self.assertEqual(sale.remaining_stock, 'manual')
        sale.payment_term = payment_term
        sale.invoice_method = 'order'
        sale_line = SaleLine()
        sale.lines.append(sale_line)
        sale_line.product = product
        sale_line.quantity = 2.0
        sale_line = SaleLine()
        sale.lines.append(sale_line)
        sale_line.product = product
        sale_line.quantity = 3.0
        sale.click('quote')
        sale.click('confirm')
        sale.click('process')
        self.assertEqual(sale.state, 'processing')
        self.assertEqual(sale.shipment_state, 'waiting')

        shipment, = sale.shipments
        shipment.click('draft')
        move1, _ = shipment.outgoing_moves
        move1.quantity = 1.0
        shipment.click('wait')
        shipment.click('assign_try')
        shipment.click('pick')
        shipment.click('pack')
        shipment.click('done')
        sale.reload()
        self.assertEqual(len(sale.shipments), 2)
        self.assertEqual([s.state for s in sale.shipments], ['done', 'cancelled'])
        self.assertEqual(sale.shipment_state, 'sent')
        line1, line2 = sale.lines
        self.assertEqual(len(line1.moves_ignored), 1)
        m1, = line1.moves_ignored
        self.assertEqual(m1.state, 'cancelled')
        self.assertEqual(m1.quantity, 1.0)
        self.assertEqual(len(line2.moves_ignored), 0)

        # Sale manual shipments and cancelled
        sale = Sale()
        sale.party = customer2
        self.assertEqual(sale.remaining_stock, 'manual')
        sale.payment_term = payment_term
        sale.invoice_method = 'order'
        sale_line = SaleLine()
        sale.lines.append(sale_line)
        sale_line.product = product
        sale_line.quantity = 2.0
        sale_line = SaleLine()
        sale.lines.append(sale_line)
        sale_line.product = product
        sale_line.quantity = 3.0
        sale.click('quote')
        sale.click('confirm')
        sale.click('process')
        self.assertEqual(sale.state, 'processing')
        self.assertEqual(sale.shipment_state, 'waiting')

        shipment, = sale.shipments
        shipment.click('cancel')
        sale.reload()

        self.assertEqual(len(sale.shipments), 1)
        self.assertEqual(sale.shipment_state, 'sent')
        line1, line2 = sale.lines
        self.assertEqual(len(line1.moves_ignored), 1)
        self.assertEqual(len(line2.moves_ignored), 1)

        # Sale manual shipments and shipment return
        sale = Sale()
        sale.party = customer2
        sale.payment_term = payment_term
        sale.invoice_method = 'order'
        sale_line = SaleLine()
        sale.lines.append(sale_line)
        sale_line.product = product
        sale_line.quantity = 2.0
        sale_line = SaleLine()
        sale.lines.append(sale_line)
        sale_line.product = product
        sale_line.quantity = -3.0
        sale.click('quote')
        sale.click('confirm')
        sale.click('process')
        self.assertEqual(sale.state, 'processing')
        self.assertEqual(sale.shipment_state, 'waiting')

        shipment, = sale.shipments
        shipment.click('draft')
        move1, = shipment.outgoing_moves
        move1.quantity = 1.0
        shipment.click('wait')
        shipment.click('assign_try')
        shipment.click('pick')
        shipment.click('pack')
        shipment.click('done')

        sale.reload()
        self.assertEqual(len(sale.shipments), 2)
        self.assertEqual([s.state for s in sale.shipments], ['done', 'cancelled'])
        self.assertEqual(sale.shipment_state, 'partially shipped')

        ship_return, = sale.shipment_returns
        ship_return.click('receive')
        ship_return.click('done')

        sale.reload()
        self.assertEqual([s.state for s in sale.shipments], ['done', 'cancelled'])
        self.assertEqual(sale.shipment_state, 'sent')

        line1, _ = sale.lines
        self.assertEqual(len(line1.moves_ignored), 1)
        m1, = line1.moves_ignored
        self.assertEqual(m1.state, 'cancelled')
        self.assertEqual(m1.quantity, 1.0)

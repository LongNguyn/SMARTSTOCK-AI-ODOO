# -*- coding: utf-8 -*-
from odoo.tests import tagged

from .common import SmartStockCommon


@tagged('post_install', '-at_install', 'smartstock')
class TestSaleFlow(SmartStockCommon):

    def test_01_quotation_is_not_confirmed_order(self):
        order = self._create_order()
        self.assertEqual(order.state, 'draft')
        self.assertFalse(order.picking_ids, 'Báo giá chưa được sinh phiếu giao hàng')
        self.assertEqual(self.customer.ss_confirmed_order_count, 0)
        # Tổng tiền do Odoo tính theo thuế cấu hình trên sản phẩm
        self.assertAlmostEqual(order.amount_untaxed, 750000)
        self.assertAlmostEqual(order.amount_total, order.amount_untaxed + order.amount_tax)

    def test_02_confirm_deliver_updates_stock(self):
        self._receive_stock(self.product, 20)
        order = self._create_order(qty=3)
        order.action_confirm()
        self.assertEqual(order.state, 'sale')

        picking = order.picking_ids
        self.assertEqual(len(picking), 1)
        self.assertEqual(picking.picking_type_code, 'outgoing')
        self.assertEqual(order.delivery_status, 'pending')
        self.assertEqual(picking.state, 'assigned', 'Hàng đủ tồn nên phiếu xuất được giữ hàng')

        picking.button_validate()
        self.assertEqual(picking.state, 'done')
        self.assertEqual(order.order_line.qty_delivered, 3)
        self.assertEqual(order.delivery_status, 'full')

        self.product_tmpl.invalidate_recordset()
        self.assertEqual(self.product_tmpl.qty_available, 17)
        # Dịch chuyển kho được ghi nhận đầy đủ (nhập + xuất)
        moves = self.env['stock.move'].search([('product_id', '=', self.product.id), ('state', '=', 'done')])
        self.assertEqual(len(moves), 2)

    def test_03_partial_delivery_creates_backorder(self):
        self._receive_stock(self.product, 20)
        order = self._create_order(qty=5)
        order.action_confirm()
        picking = order.picking_ids
        picking.move_ids.quantity = 2
        res = picking.button_validate()
        # Odoo hỏi có tạo backorder không -> xử lý qua wizard chuẩn
        wizard = self.env['stock.backorder.confirmation'].with_context(res['context']).create({})
        wizard.process()
        self.assertEqual(order.order_line.qty_delivered, 2)
        self.assertEqual(order.delivery_status, 'partial')
        self.assertEqual(len(order.picking_ids), 2)

    def test_04_partner_statistics_count_confirmed_only(self):
        self._create_order()  # báo giá - không tính
        confirmed = self._create_order()
        confirmed.action_confirm()
        cancelled = self._create_order()
        cancelled._action_cancel()

        self.customer.invalidate_recordset()
        self.assertEqual(self.customer.ss_confirmed_order_count, 1)
        self.assertEqual(self.customer.ss_last_order_date, confirmed.date_order)

    def test_05_child_contact_orders_counted_on_company(self):
        contact = self.env['res.partner'].create({'name': 'Anh Nam', 'parent_id': self.customer.id})
        order = self.env['sale.order'].create({
            'partner_id': contact.id,
            'order_line': [(0, 0, {'product_id': self.product.id, 'product_uom_qty': 1})],
        })
        order.action_confirm()
        partners = self.customer | contact
        partners.invalidate_recordset()
        self.assertEqual(self.customer.ss_confirmed_order_count, 1)
        self.assertEqual(contact.ss_confirmed_order_count, 1)

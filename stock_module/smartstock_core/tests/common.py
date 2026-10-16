# -*- coding: utf-8 -*-
from odoo import Command
from odoo.tests.common import TransactionCase, new_test_user


class SmartStockCommon(TransactionCase):
    """Dữ liệu dùng chung cho các test SmartStock (tạo trong transaction, tự rollback)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1)
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.categ = cls.env['product.category'].create({'name': 'SS Test - Đồ uống'})

        cls.product_tmpl = cls.env['product.template'].create({
            'name': 'SS Test - Cà phê hạt 1kg',
            'default_code': 'SS-CF-01',
            'detailed_type': 'product',
            'categ_id': cls.categ.id,
            'list_price': 250000,
            'standard_price': 180000,
            'ss_min_qty': 10,
        })
        cls.product = cls.product_tmpl.product_variant_id

        cls.customer = cls.env['res.partner'].create({
            'name': 'SS Test - Công ty ABC',
            'is_company': True,
            'phone': '0900000000',
            'city': 'Hà Nội',
        })

        cls.user_salesman = new_test_user(
            cls.env, login='ss_salesman', name='SS Nhân viên bán hàng',
            groups='smartstock_core.group_smartstock_salesman')
        cls.user_salesman_2 = new_test_user(
            cls.env, login='ss_salesman2', name='SS Nhân viên bán hàng 2',
            groups='smartstock_core.group_smartstock_salesman')
        cls.user_manager = new_test_user(
            cls.env, login='ss_manager', name='SS Quản lý kinh doanh',
            groups='smartstock_core.group_smartstock_sales_manager')
        cls.user_warehouse = new_test_user(
            cls.env, login='ss_warehouse', name='SS Nhân viên kho',
            groups='smartstock_core.group_smartstock_warehouse')

    @classmethod
    def _receive_stock(cls, product, qty):
        """Nhập kho qua phiếu nhập chuẩn (stock.picking) — không sửa trực tiếp stock.quant."""
        picking_type = cls.warehouse.in_type_id
        picking = cls.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': cls.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': cls.stock_location.id,
            'move_ids': [Command.create({
                'name': product.display_name,
                'product_id': product.id,
                'product_uom_qty': qty,
                'product_uom': product.uom_id.id,
                'location_id': cls.env.ref('stock.stock_location_suppliers').id,
                'location_dest_id': cls.stock_location.id,
            })],
        })
        picking.action_confirm()
        picking.move_ids.quantity = qty
        picking.button_validate()
        return picking

    def _create_order(self, user=None, qty=3, price=250000):
        env = self.env if user is None else self.env(user=user)
        return env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': qty,
                'price_unit': price,
            })],
        })

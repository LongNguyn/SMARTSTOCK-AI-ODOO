# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import SmartStockCommon


@tagged('post_install', '-at_install', 'smartstock')
class TestSecurity(SmartStockCommon):
    """Kiểm thử phân quyền ở tầng ORM (ACL + record rule), không chỉ menu."""

    def test_01_group_hierarchy(self):
        self.assertTrue(self.user_salesman.has_group('sales_team.group_sale_salesman'))
        self.assertFalse(self.user_salesman.has_group('sales_team.group_sale_salesman_all_leads'))
        self.assertTrue(self.user_manager.has_group('sales_team.group_sale_manager'))
        self.assertTrue(self.user_manager.has_group('smartstock_core.group_smartstock_salesman'))
        self.assertTrue(self.user_warehouse.has_group('stock.group_stock_user'))
        self.assertFalse(self.user_warehouse.has_group('sales_team.group_sale_salesman'))
        admin = self.env.ref('base.user_admin')
        self.assertTrue(admin.has_group('smartstock_core.group_smartstock_admin'))
        self.assertTrue(admin.has_group('stock.group_stock_manager'))

    def test_02_salesman_sees_only_own_orders(self):
        order = self._create_order(user=self.user_salesman)
        self.assertEqual(order.user_id, self.user_salesman)

        SaleOrder2 = self.env['sale.order'].with_user(self.user_salesman_2)
        self.assertNotIn(order.id, SaleOrder2.search([]).ids)
        with self.assertRaises(AccessError):
            order.with_user(self.user_salesman_2).read(['name'])

        # Quản lý kinh doanh thấy toàn bộ
        self.assertIn(order.id, self.env['sale.order'].with_user(self.user_manager).search([]).ids)

    def test_03_salesman_can_confirm_own_order(self):
        self._receive_stock(self.product, 10)
        order = self._create_order(user=self.user_salesman)
        order.with_user(self.user_salesman).action_confirm()
        self.assertEqual(order.state, 'sale')

    def test_04_warehouse_cannot_create_sale_order(self):
        with self.assertRaises(AccessError):
            self._create_order(user=self.user_warehouse)

    def test_05_salesman_cannot_edit_product_or_adjust_stock(self):
        with self.assertRaises(AccessError):
            self.product_tmpl.with_user(self.user_salesman).write({'list_price': 1})
        # Nhân viên bán hàng không được điều chỉnh tồn (stock.quant) hay tạo vị trí kho.
        # Lưu ý: sale_stock chuẩn cho phép salesman tạo stock.picking/stock.move vì
        # xác nhận đơn bán sinh phiếu xuất dưới quyền người xác nhận.
        Quant = self.env['stock.quant']
        self.assertFalse(Quant.with_user(self.user_salesman).check_access_rights('write', raise_exception=False))
        self.assertFalse(Quant.with_user(self.user_salesman).check_access_rights('create', raise_exception=False))
        self.assertFalse(self.env['stock.location'].with_user(self.user_salesman)
                         .check_access_rights('create', raise_exception=False))
        self.assertTrue(Quant.with_user(self.user_warehouse).check_access_rights('write', raise_exception=False))
        # Nhân viên kho không có quyền quản lý kho (cấu hình kho, vị trí).
        self.assertFalse(self.env['stock.location'].with_user(self.user_warehouse)
                         .check_access_rights('create', raise_exception=False))

    def test_06_cost_price_hidden_from_salesman_view(self):
        view = self.env.ref('smartstock_core.ss_product_template_tree')
        Template = self.env['product.template']
        arch_sales = Template.with_user(self.user_salesman).get_views([(view.id, 'list')])['views']['list']['arch']
        arch_manager = Template.with_user(self.user_manager).get_views([(view.id, 'list')])['views']['list']['arch']
        self.assertNotIn('name="standard_price"', arch_sales)
        self.assertIn('name="standard_price"', arch_manager)

    def test_07_menu_visibility(self):
        Menu = self.env['ir.ui.menu']
        inventory_menu = self.env.ref('smartstock_core.menu_ss_inventory')
        sales_menu = self.env.ref('smartstock_core.menu_ss_sales')
        config_menu = self.env.ref('smartstock_core.menu_ss_config')

        visible_sales = Menu.with_user(self.user_salesman)._visible_menu_ids()
        self.assertIn(sales_menu.id, visible_sales)
        self.assertNotIn(inventory_menu.id, visible_sales)
        self.assertNotIn(config_menu.id, visible_sales)

        visible_wh = Menu.with_user(self.user_warehouse)._visible_menu_ids()
        self.assertIn(inventory_menu.id, visible_wh)
        self.assertNotIn(sales_menu.id, visible_wh)

    def test_08_partner_stats_respect_record_rules(self):
        self._create_order(user=self.user_salesman).action_confirm()
        partner_as_s2 = self.customer.with_user(self.user_salesman_2)
        self.assertEqual(partner_as_s2.ss_confirmed_order_count, 0)
        partner_as_mgr = self.customer.with_user(self.user_manager)
        self.assertEqual(partner_as_mgr.ss_confirmed_order_count, 1)

# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import SmartStockCommon


@tagged('post_install', '-at_install', 'smartstock')
class TestProductStock(SmartStockCommon):

    def test_01_status_without_stock_is_out(self):
        self.assertEqual(self.product_tmpl.qty_available, 0)
        self.assertEqual(self.product_tmpl.ss_stock_status, 'out')
        self.assertTrue(self.product_tmpl.ss_is_low_stock)

    def test_02_receipt_updates_status(self):
        self._receive_stock(self.product, 4)
        self.product_tmpl.invalidate_recordset()
        self.assertEqual(self.product_tmpl.qty_available, 4)
        self.assertEqual(self.product_tmpl.ss_stock_status, 'low')

        self._receive_stock(self.product, 20)
        self.product_tmpl.invalidate_recordset()
        self.assertEqual(self.product_tmpl.qty_available, 24)
        self.assertEqual(self.product_tmpl.ss_stock_status, 'ok')
        self.assertFalse(self.product_tmpl.ss_is_low_stock)

    def test_03_search_low_stock(self):
        Template = self.env['product.template']
        self.assertIn(self.product_tmpl, Template.search([('ss_is_low_stock', '=', True)]))
        self.assertIn(self.product_tmpl, Template.search([('ss_stock_status', '=', 'out')]))

        self._receive_stock(self.product, 50)
        self.assertNotIn(self.product_tmpl, Template.search([('ss_is_low_stock', '=', True)]))
        self.assertIn(self.product_tmpl, Template.search([('ss_is_low_stock', '=', False)]))
        self.assertIn(self.product_tmpl, Template.search([('ss_stock_status', 'in', ['ok'])]))
        self.assertNotIn(self.product_tmpl, Template.search([('ss_stock_status', '!=', 'ok')]))

    def test_04_service_has_no_stock_status(self):
        service = self.env['product.template'].create({
            'name': 'SS Test - Dịch vụ lắp đặt', 'detailed_type': 'service', 'ss_min_qty': 5,
        })
        self.assertEqual(service.ss_stock_status, 'none')
        self.assertFalse(service.ss_is_low_stock)
        self.assertIn(service, self.env['product.template'].search([('ss_stock_status', '=', 'none')]))

    def test_05_negative_min_qty_rejected(self):
        with self.assertRaises(ValidationError):
            self.product_tmpl.ss_min_qty = -1

    def test_06_min_qty_is_company_dependent(self):
        company_b = self.env['res.company'].create({'name': 'SS Test - Công ty B'})
        tmpl_b = self.product_tmpl.with_company(company_b)
        self.assertEqual(tmpl_b.ss_min_qty, 0)
        tmpl_b.ss_min_qty = 99
        self.assertEqual(self.product_tmpl.with_company(self.company).ss_min_qty, 10)

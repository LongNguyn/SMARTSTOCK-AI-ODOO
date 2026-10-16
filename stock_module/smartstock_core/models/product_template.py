# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

STOCK_STATUS = [
    ('none', 'Không quản lý tồn'),
    ('out', 'Hết hàng'),
    ('low', 'Dưới mức tối thiểu'),
    ('ok', 'Đủ hàng'),
]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # company_dependent: mỗi công ty có ngưỡng riêng (tôn trọng đa công ty).
    ss_min_qty = fields.Float(
        string='Tồn kho tối thiểu',
        company_dependent=True,
        digits='Product Unit of Measure',
        help='Khi tồn kho hiện có (qty_available) thấp hơn ngưỡng này, '
             'sản phẩm được đánh dấu "Dưới mức tối thiểu". Để 0 nếu không theo dõi.',
    )
    ss_stock_status = fields.Selection(
        STOCK_STATUS,
        string='Tình trạng tồn kho',
        compute='_compute_ss_stock_status',
        search='_search_ss_stock_status',
    )
    ss_is_low_stock = fields.Boolean(
        string='Tồn kho thấp',
        compute='_compute_ss_stock_status',
        search='_search_ss_is_low_stock',
        help='Sản phẩm lưu kho có ngưỡng tối thiểu > 0 và tồn hiện có < ngưỡng.',
    )

    @api.constrains('ss_min_qty')
    def _check_ss_min_qty(self):
        for template in self:
            if template.ss_min_qty < 0:
                raise ValidationError(_('Tồn kho tối thiểu không được âm (sản phẩm: %s).', template.display_name))

    # ------------------------------------------------------------------
    # Tính trạng thái tồn kho
    # ------------------------------------------------------------------
    @api.model
    def _ss_get_stock_status(self, product_type, qty, min_qty):
        """Quy tắc duy nhất, dùng chung cho compute, search và module báo cáo/AI."""
        if product_type != 'product':
            return 'none'
        if qty <= 0:
            return 'out'
        if min_qty > 0 and qty < min_qty:
            return 'low'
        return 'ok'

    @api.depends('type', 'qty_available', 'ss_min_qty')
    @api.depends_context('company', 'allowed_company_ids', 'warehouse', 'location')
    def _compute_ss_stock_status(self):
        # qty_available được tính theo lô (một lần read_group cho cả recordset) -> không N+1.
        for template in self:
            status = self._ss_get_stock_status(template.type, template.qty_available, template.ss_min_qty)
            template.ss_stock_status = status
            template.ss_is_low_stock = (
                template.type == 'product'
                and template.ss_min_qty > 0
                and template.qty_available < template.ss_min_qty
            )

    def _ss_storable_templates(self):
        return self.with_context(active_test=False).search([('type', '=', 'product')])

    def _search_ss_stock_status(self, operator, value):
        if operator not in ('=', '!=', 'in', 'not in'):
            raise ValidationError(_('Toán tử tìm kiếm không được hỗ trợ: %s', operator))
        values = {value} if operator in ('=', '!=') else set(value or [])
        storable = self._ss_storable_templates()
        matched = storable.filtered(lambda t: t.ss_stock_status in values).ids
        domain = [('id', 'in', matched)]
        if 'none' in values:
            domain = ['|', ('type', '!=', 'product')] + domain
        if operator in ('!=', 'not in'):
            # '!' trong ký pháp tiền tố phủ định toàn bộ biểu thức đứng sau.
            domain = ['!'] + domain
        return domain

    def _search_ss_is_low_stock(self, operator, value):
        if operator not in ('=', '!='):
            raise ValidationError(_('Toán tử tìm kiếm không được hỗ trợ: %s', operator))
        candidates = self.with_context(active_test=False).search([
            ('type', '=', 'product'),
            ('ss_min_qty', '>', 0),
        ])
        low_ids = candidates.filtered('ss_is_low_stock').ids
        positive = (operator == '=') == bool(value)
        return [('id', 'in' if positive else 'not in', low_ids)]

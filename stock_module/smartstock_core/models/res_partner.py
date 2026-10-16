# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ss_confirmed_order_count = fields.Integer(
        string='Số đơn đã xác nhận',
        compute='_compute_ss_sale_stats',
        help='Số đơn bán ở trạng thái "Đơn bán hàng" (state = sale) mà người dùng hiện tại được phép xem.',
    )
    ss_last_order_date = fields.Datetime(
        string='Ngày đặt hàng gần nhất',
        compute='_compute_ss_sale_stats',
    )

    @api.depends_context('uid', 'allowed_company_ids')
    def _compute_ss_sale_stats(self):
        origin_ids = [p._origin.id for p in self if p._origin.id]
        stats = {}
        if origin_ids and self.env['sale.order'].check_access_rights('read', raise_exception=False):
            # Một truy vấn GROUP BY cho cả danh sách -> không N+1.
            # _read_group áp dụng record rule => nhân viên bán hàng chỉ thấy số liệu đơn của mình.
            groups = self.env['sale.order']._read_group(
                domain=[('partner_id', 'child_of', origin_ids), ('state', '=', 'sale')],
                groupby=['partner_id'],
                aggregates=['__count', 'date_order:max'],
            )
            for partner, count, last_date in groups:
                # Cộng dồn đơn của liên hệ con vào công ty mẹ đang hiển thị.
                for pid in {partner.id, partner.commercial_partner_id.id} & set(origin_ids):
                    old_count, old_date = stats.get(pid, (0, False))
                    stats[pid] = (old_count + count, max(filter(None, [old_date, last_date]), default=False))
        for partner in self:
            count, last_date = stats.get(partner._origin.id, (0, False))
            partner.ss_confirmed_order_count = count
            partner.ss_last_order_date = last_date

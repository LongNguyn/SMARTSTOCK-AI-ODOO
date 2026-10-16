# -*- coding: utf-8 -*-
{
    'name': 'SmartStock Core',
    'version': '17.0.1.0.0',
    'summary': 'SmartStock AI - Nền tảng bán hàng, tồn kho và phân quyền trên Odoo 17',
    'description': """
SmartStock Core
===============
Module nền tảng của đề tài SmartStock AI (giai đoạn 1, không dùng AI):

* Nhóm quyền SmartStock (Quản trị viên, Quản lý kinh doanh, Nhân viên bán hàng, Nhân viên kho)
* Menu tiếng Việt gom các chức năng Sales / Inventory / Contacts chuẩn
* Ngưỡng tồn kho tối thiểu và trạng thái tồn kho trên sản phẩm
* Thống kê đơn bán đã xác nhận trên khách hàng
* Danh sách đơn bán có trạng thái giao hàng / xuất hóa đơn

Module chỉ mở rộng model chuẩn (product.template, res.partner, sale.order),
không tạo model nghiệp vụ mới và không sửa trực tiếp tồn kho.
    """,
    'author': 'SmartStock AI',
    'license': 'LGPL-3',
    'category': 'Sales/Sales',
    'depends': [
        'contacts',
        'sale_management',
        'stock',
        'stock_account',
        'sale_stock',
    ],
    'data': [
        'security/smartstock_security.xml',
        'security/ir.model.access.csv',
        'data/smartstock_data.xml',
        'views/product_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/smartstock_menus.xml',
    ],
    'installable': True,
    'application': True,
}

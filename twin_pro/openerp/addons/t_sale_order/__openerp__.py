{
    'name': 'Sale Order',
    'version': '0.1',
    'author': 'openerpdevelopers',    
    'depends' : ['base','product','account','t_work_order','m_annexture'],
    'description' : """ CRM Quotation track """,
    'category' : 'Sale',
    'data': [
			
			't_sale_order_view.xml',
			
			],
    'auto_install': False,
    'installable': True,
}

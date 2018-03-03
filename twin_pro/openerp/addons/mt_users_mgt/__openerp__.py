{
    'name': 'Users Management System',
    'version': '0.1',
    'author': 'openerpdevelopers',
    'category': 'User_Management',
    'images': ['images/purchase_requisitions.jpeg'],
    'website': 'http://www.openerp.com',
    'description': """
This module allows you to manage your Purchase Requisition.
===========================================================

When a purchase order is created, you now have the opportunity to save the
related requisition. This new object will regroup and will allow you to easily
keep track and order all your purchase orders.
""",
    'depends' : ['base','m_department'],
    'data': [
			
			'groups_data.xml',
			'mt_users_view.xml',
			#~ 'module_access/master_admin.xml',
			#~ 'module_access/transaction_admin.xml',
			'rules/mt_model_rules.xml',
			
			],
			
    'auto_install': False,
    'installable': True,
}


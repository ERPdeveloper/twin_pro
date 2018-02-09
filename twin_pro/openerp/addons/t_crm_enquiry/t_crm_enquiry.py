from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
import time
from datetime import date
import openerp.addons.decimal_precision as dp
from datetime import datetime

class t_crm_enquiry(osv.osv):
	
	_name = "t.crm.enquiry"
	_description = "CRM Enquiry"
	_order = "enquiry_date desc"
	
	_columns = {
		
		## Basic Info
		
		'name': fields.char('Enquiry No',size=30,select=True,readonly=True),
		'enquiry_date': fields.date('Enquiry Date',required=True),
		'notes': fields.text('Notes'),
		'state': fields.selection([('draft','Draft'),('validated','Validated'),('rejected','Rejected')],'Status', readonly=True),
		'remark': fields.char('Rejected For'),
		'source_mode': fields.selection([('auto','Auto'),('manual','Manual')],'Source Mode', readonly=True),
		
		## Module Requirement Info
		
		'customer_id': fields.many2one('res.partner', 'Customer Name',required=True,domain=[('customer','=',True),('partner_state','=','validated')]),
		'segment': fields.selection([('dom','Domestic'),('non_dom','Non-Domestic')],'Segment',required=True),
		'enquiry_by': fields.selection([('customer','Customer'),('dealer','Dealer')],'Enquired By',required=True),
		'reference': fields.selection([('direct','Direct'),('adv','Advertisement'),('mail','Mail')],'Reference',required=True),
		'enquiry_status': fields.selection([('on_hold','On Hold'),('to_be_fol','To be Followed'),('closed','Closed')],'Enquiry Status',required=True),
		'delivery_date': fields.date('Delivery Date',required=True),
		'reminder_date': fields.date('Reminder Date',required=True),
		'expected_date': fields.date('Expected Date'),
		'expected_value': fields.float('Expected Value'),
		
		## Child Tables Declaration
		
		'line_ids': fields.one2many('ch.crm.enquiry', 'header_id', "Line Details"),
		
		## Entry Info
		
		'company_id': fields.many2one('res.company', 'Company Name',readonly=True),
		'active': fields.boolean('Active'),
		'crt_date': fields.datetime('Created On',readonly=True),
		'crt_user_id': fields.many2one('res.users', 'Created By', readonly=True),
		'validated_date': fields.datetime('Validated On', readonly=True),
		'validated_user_id': fields.many2one('res.users', 'Validated By', readonly=True),
		'rejected_date': fields.datetime('Rejected On', readonly=True),
		'rejected_user_id': fields.many2one('res.users', 'Rejected By', readonly=True),
		'updated_date': fields.datetime('Recent Update On', readonly=True),
		'updated_user_id': fields.many2one('res.users', 'Recent Update By', readonly=True),
		
	}
	
	_defaults = {
		
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 't.crm.enquiry', context=c),			
		'enquiry_date' : lambda * a: time.strftime('%Y-%m-%d'),
		'crt_user_id': lambda obj, cr, uid, context: uid,
		'crt_date':lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'state': 'draft',
		'active': True,
		'source_mode': 'manual',
		
	}
	
	def _validations(self, cr, uid, ids, context=None):
		entry = self.browse(cr,uid,ids[0])
		if not entry.line_ids:
			raise osv.except_osv(_('Warning!'),_('Product details should not be empty.'))
		return True
	
	_constraints = [
		
       (_validations, ' Validations of CRM Enquiry ', ['']),
		
       ]
	
	def entry_validate(self,cr,uid,ids,context=None):
		
		rec = self.browse(cr,uid,ids[0])
		
		## Sequence Number Generation
		
		if rec.state == 'draft':
			if rec.name == '' or rec.name == False:
				seq_obj_id = self.pool.get('ir.sequence').search(cr,uid,[('code','=','t.crm.enquiry')])
				seq_rec = self.pool.get('ir.sequence').browse(cr,uid,seq_obj_id[0])
				cr.execute(""" select generatesequenceno(%s,'%s','%s') """%(seq_obj_id[0],seq_rec.code,rec.entry_date))
				entry_name = cr.fetchone();
				entry_name = entry_name[0]
			else:
				entry_name = rec.name
			
			self.write(cr, uid, ids, {'name': entry_name,'state': 'validated','validated_user_id': uid, 'validated_date': time.strftime('%Y-%m-%d %H:%M:%S')})
		
		return True
		
	def entry_reject(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.state == 'validated':
			if rec.remark:
				self.write(cr, uid, ids, {'state': 'rejected','rejected_user_id': uid, 'rejected_date': time.strftime('%Y-%m-%d %H:%M:%S')})
			else:
				raise osv.except_osv(_('Warning !'),_('Enter Reason For rejection.'))
		return True
	
	def unlink(self,cr,uid,ids,context=None):
		unlink_ids = []
		for rec in self.browse(cr,uid,ids):
			if rec.state not in ('draft'):
				raise osv.except_osv(_('Warning !'),_('Draft only can be deleted.'))
			else:
				unlink_ids.append(rec.id)
		return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
		
	def create(self, cr, uid, vals, context=None):
		return super(t_crm_enquiry, self).create(cr, uid, vals, context=context)
	
	def write(self, cr, uid, ids, vals, context=None):
		vals.update({'updated_date': time.strftime('%Y-%m-%d %H:%M:%S'),'updated_user_id':uid})
		return super(t_crm_enquiry, self).write(cr, uid, ids, vals, context)
	
	_sql_constraints = [
		
		('name', 'unique(name)', 'No must be Unique !!'),
	]
	
t_crm_enquiry()

class ch_crm_enquiry(osv.osv):
	
	_name = "ch.crm.enquiry"
	_description = "Product Details"
	
	_columns = {
		
		## Basic Info
		
		'header_id':fields.many2one('t.crm.enquiry','Enquiry No',required=1,ondelete='cascade'),
		'remark': fields.text('Remarks'),
		'active': fields.boolean('Active'),
		
		## Module Requirement Fields
		
		'product_id': fields.many2one('product.product','Product',required=True),
		'uom_id': fields.many2one('product.uom','UOM',required=True),
		'brand_id': fields.many2one('m.brand','Brand'),
		'qty': fields.float('Qty',required=True),
		
		## Child Tables Declaration
		
	}
	
	_defaults = {
		
		'active': True,
		
	}
	
ch_crm_enquiry()

class t_sequence_generate_det(osv.osv):
	_name = 't.sequence.generate.det'
	_order = 'name'
	_columns = 	{
	
	
		'name': fields.char('Name',size=64),
		'ir_sequence_id': fields.many2one('ir.sequence', 'Sequence'),
		'seq_month' : fields.integer('Sequence Month'),
		'seq_year' : fields.integer('Sequence Year'),
		'seq_next_number' : fields.integer('Sequence Next Number'),
		'fiscal_year_code' : fields.char('Fiscal Year Code',size=64),
		'fiscal_year_id' : fields.integer('Fiscal Year ID'),
	}
	
t_sequence_generate_det()

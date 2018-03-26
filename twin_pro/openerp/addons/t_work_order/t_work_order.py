from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
import time
from datetime import date
import openerp.addons.decimal_precision as dp
from datetime import datetime

class t_work_order(osv.osv):
	
	_name = "t.work.order"
	_description = "Work Order"
	_order = "so_date desc"
	
	def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
		res = {}
		cur_obj=self.pool.get('res.currency')
		for order in self.browse(cr, uid, ids, context=context):
			res[order.id] = {
				'amount_untaxed': 0.0,
				'amount_tax': 0.0,
				'amount_total': 0.0,
			}
			val = val1 = 0.0
			cur = 21
			for line in order.line_ids:
			   val1 += line.sub_total
			   for c in self.pool.get('account.tax').compute_all(cr, uid, line.taxes_id, line.unit_price, line.qty, line.product_id, order.customer_id)['taxes']:
					val += c.get('amount', 0.0)
			res[order.id]['amount_tax']=round(val)
			res[order.id]['amount_untaxed']=round(val1)
			res[order.id]['amount_total']=res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
		return res
	
	def _get_order(self, cr, uid, ids, context=None):
		result = {}
		for line in self.pool.get('ch.work.order').browse(cr, uid, ids, context=context):
			result[line.header_id.id] = True
		return result.keys()
	
	_columns = {
		
		## Basic Info
		
		'name': fields.char('Order No',size=30,select=True,readonly=True),
		'so_date': fields.date('WO Date',required=True),
		'notes': fields.text('Notes'),
		'state': fields.selection([('draft','Draft'),('validated','Validated'),('rejected','Rejected')],'Status', readonly=True),
		'remark': fields.char('Rejected For'),
		'source_mode': fields.selection([('auto','Auto'),('manual','Manual')],'Source Mode', readonly=True),
		
		## Module Requirement Info
		
		'customer_id': fields.many2one('res.partner', 'Customer Name',required=True,domain=[('customer','=',True),('partner_state','=','validated')]),
		'order_type': fields.selection([('direct','Direct'),('quotation','Quotation')],'Order Type',required=True),
		'revision': fields.integer('Revision'),
		'delivery_date': fields.date('Delivery Date',required=True),
		'expected_date': fields.date('Expected Date'),
		'expected_value': fields.float('Expected Value'),
		'address': fields.text('Address'),
		'city_id':fields.many2one('res.city','City'),
		'state_id':fields.many2one('res.country.state','State'),
		#~ 'quotation_id':fields.many2one('t.crm.quotation','Quotation',domain=[('state','=','validated')]),
		'quotation_id':fields.many2one('t.crm.quotation','Quotation'),
		
		'amount_untaxed': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Untaxed Amount',
			store={
				'ch.work.order': (_get_order, None, 10),
			}, multi="sums", help="The amount without tax", track_visibility='always'),
		'amount_tax': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Taxes',
			store={
				'ch.work.order': (_get_order, None, 10),
			}, multi="sums", help="The tax amount"),
		'amount_total': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Total',
			store={
				'ch.work.order': (_get_order, None, 10),
			}, multi="sums",help="The total amount"),
		
		## Child Tables Declaration
		
		'line_ids': fields.one2many('ch.work.order', 'header_id', "Line Details"),
		
		## Entry Info
		
		'company_id': fields.many2one('res.company', 'Company Name',readonly=True),
		'active': fields.boolean('Active'),
		'crt_date': fields.datetime('Created On',readonly=True),
		'entry_date': fields.datetime('Entry Date',readonly=True),
		'crt_user_id': fields.many2one('res.users', 'Created By', readonly=True),
		'validated_date': fields.datetime('Validated On', readonly=True),
		'validated_user_id': fields.many2one('res.users', 'Validated By', readonly=True),
		'rejected_date': fields.datetime('Rejected On', readonly=True),
		'rejected_user_id': fields.many2one('res.users', 'Rejected By', readonly=True),
		'updated_date': fields.datetime('Recent Update On', readonly=True),
		'updated_user_id': fields.many2one('res.users', 'Recent Update By', readonly=True),
		
	}
	
	_defaults = {
		
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 't.work.order', context=c),			
		'so_date' : lambda * a: time.strftime('%Y-%m-%d'),
		'crt_user_id': lambda obj, cr, uid, context: uid,
		'crt_date':lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'entry_date':lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'state': 'draft',
		'active': True,
		'source_mode': 'manual',
		'revision': 0,
		
	}
	
	def _validations(self, cr, uid, ids, context=None):
		entry = self.browse(cr,uid,ids[0])
		if not entry.line_ids:
			raise osv.except_osv(_('Warning!'),_('Product details should not be empty.'))
		else:
			for lines in entry.line_ids:
				if lines.unit_price <= 0.00:
					raise osv.except_osv(_('Warning!'),_('Unit Price should not be zero for product (%s)'%(lines.product_id.name_template)))
		return True
	
	_constraints = [
		
	   #~ (_validations, ' Validations of CRM Enquiry ', ['']),
		
	   ]
	def copy(self, cr, uid, id, default=None, context=None):
		if default == None:
			default = {}
		return super(t_crm_quotation, self).copy(cr, uid, id, default, context=context)
	   
	#~ def copy(self, cr, uid, id, default=None, context=None):
		#~ if not default:
			#~ default = {}
		#~ default.update({
			#~ 'revision':1,
			
		#~ })
		#~ return super(t_crm_quotation, self).copy(cr, uid, id,default,context)
	
	def onchange_customer_id(self,cr,uid,ids,customer_id,context=None):
		if customer_id:
			customer_rec = self.pool.get('res.partner').browse(cr,uid,customer_id)
		return {'value': {'address': customer_rec.street,'city_id':customer_rec.city_id.id,'state_id':customer_rec.state_id.id}}
   
   
	def onchange_quotation_id(self,cr,uid,ids,quotation_id,context=None):
		quotation_lines = []
		if quotation_id:
			quotation_rec = self.pool.get('t.crm.quotation').browse(cr,uid,quotation_id)
			
			for lines in quotation_rec.line_ids:
				print "linesssssssssssssssssssssssssssssssssss",lines
				quotation_line_vals = {
						'product_id': lines.product_id.id,
						'uom_id': lines.uom_id.id,
						'brand_id': lines.brand_id.id,
						'unit_price': lines.unit_price,
						'qty': lines.qty,
						'taxes_id': '',
						
                }
                quotation_lines.append(quotation_line_vals)
                print "quotation_linesquotation_linesquotation_lines",quotation_line_vals
		return {'value': {'line_ids': quotation_lines}}
		
	
	def entry_validate(self,cr,uid,ids,context=None):
		
		rec = self.browse(cr,uid,ids[0])
		
		## Sequence Number Generation
		
		if rec.state == 'draft':
			self._validations(self,cr,uid,rec.id,context=context)
			if rec.name == '' or rec.name == False:
				seq_obj_id = self.pool.get('ir.sequence').search(cr,uid,[('code','=','t.work.order')])
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
	
	def button_dummy(self,cr,uid,ids,context=None):
		return True
	
	def unlink(self,cr,uid,ids,context=None):
		unlink_ids = []
		for rec in self.browse(cr,uid,ids):
			if rec.state not in ('draft'):
				raise osv.except_osv(_('Warning !'),_('Draft only can be deleted.'))
			else:
				unlink_ids.append(rec.id)
		return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
		
	def write(self, cr, uid, ids, vals, context=None):
		vals.update({'updated_date': time.strftime('%Y-%m-%d %H:%M:%S'),'updated_user_id':uid})
		return super(t_work_order, self).write(cr, uid, ids, vals, context)
	
	_sql_constraints = [
		
		('name', 'unique(name)', 'No must be Unique !!'),
	]
	
t_work_order()

class ch_work_order(osv.osv):
	
	_name = "ch.work.order"
	_description = "Product Details"
	
	def _amount_line(self, cr, uid, ids, prop, arg, context=None):
		res = {}
		cur_obj=self.pool.get('res.currency')
		tax_obj = self.pool.get('account.tax')
		for line in self.browse(cr, uid, ids, context=context):
			taxes = tax_obj.compute_all(cr, uid, line.taxes_id, line.unit_price, line.qty, line.product_id, line.header_id.customer_id)
			cur = 21
			res[line.id] = taxes['total']
		return res
	
	_columns = {
		
		## Basic Info
		
		'header_id':fields.many2one('t.work.order','Enquiry No',required=1,ondelete='cascade'),
		'remark': fields.text('Remarks'),
		'active': fields.boolean('Active'),
		
		## Module Requirement Fields
		
		'product_id': fields.many2one('product.product','Product',required=True),
		'uom_id': fields.many2one('product.uom','UOM',required=True),
		'brand_id': fields.many2one('m.brand','Brand'),
		'unit_price': fields.float('Unit Price'),
		'taxes_id': fields.many2many('account.tax', 'so_taxes', 'so_id', 'tax_id', 'Taxes'),
		'sub_total': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account')),
		'qty': fields.float('Qty',required=True),
		
		## Child Tables Declaration
		
	}
	
	_defaults = {
		
		'active': True,
		
	}
	
	def onchange_product_id(self,cr,uid,ids,product_id,context=None):
		rec = self.browse(cr,uid,ids[0])
		if product_id:
			product_rec = self.pool.get('product.product').browse(cr,uid,product_id)
			taxes=[]
			if product_rec.hsn_no.id:
				hsn_rec = self.pool.get('m.hsn.code').browse(cr,uid,product_rec.hsn_no.id)
				print "header_id.state_idheader_id.state_idheader_id.state_id",rec.header_id.state_id.code
				if rec.header_id.state_id.code == 'TND':
					taxes = [hsn_rec.sgst_tax_id.id,hsn_rec.cgst_tax_id.id]
				else:
					taxes = [hsn_rec.igst_tax_id.id]
		return {'value': {'uom_id': product_rec.uom_id.id,'taxes_id': taxes}}
	
ch_work_order()


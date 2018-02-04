from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime
import math

class m_hsn_code(osv.osv):
	
	_name = "m.hsn.code"
	_description = "HSN Code"
	
	_columns = {
		
		# Basic Info
		
		'name': fields.char('Name',required=True, select=True),
		'code': fields.char('Code', size=5, required=True),
		'state': fields.selection([('draft','Draft'),('validated','Validated'),('rejected','Rejected')],'Status', readonly=True),
		'notes': fields.text('Notes'),
		'remark': fields.char('Rejected For'),
		'source_mode': fields.selection([('auto','Auto'),('manual','Manual')],'Source Mode', readonly=True),
		
		# Entry Info
		
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
		
		# Module Requirement Info
		
		'sgst_tax_id':fields.many2one('account.tax','SGST',domain=[('tax_type','=','sgst'),('state','=','validated')]),
		'cgst_tax_id':fields.many2one('account.tax','CGST',domain=[('tax_type','=','cgst'),('state','=','validated')]),
		'igst_tax_id':fields.many2one('account.tax','IGST',domain=[('tax_type','=','igst'),('state','=','validated')]),
		
		# Child Tables Declaration
		
		
	}
	
	_defaults = {
		
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'm.expense', context=c),
		'active': True,
		'state': 'draft',
		'crt_user_id': lambda obj, cr, uid, context: uid,
		'crt_date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'source_mode': 'manual',
		
	}
	
	#~ _sql_constraints = [
	#~ 
		#~ ('name', 'unique(name)', 'Name must be unique per Company !!'),
		#~ ('code', 'unique(code)', 'Code must be unique per Company !!'),
		#~ 
	#~ ]
	
	# Basic Needs
	
	def _validations(self, cr, uid,ids, context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.name:
			cr.execute(""" select upper(name) from m_hsn_code where upper(name) = '%s' """ %(rec.name.upper()))
			data = cr.dictfetchall()
			if len(data) > 1:
				raise osv.except_osv(_('Warning !'),_('HSN Name already exists'))
		if rec.code:
			cr.execute(""" select upper(code) from m_hsn_code where upper(code) = '%s' """ %(rec.code.upper()))
			data = cr.dictfetchall()
			if len(data) > 1:
				raise osv.except_osv(_('Warning !'),_('HSN Code already exists'))
		if rec.sgst_tax_id.id and rec.cgst_tax_id.id and rec.igst_tax_id.id:
			cr.execute("""select id from m_hsn_code where sgst_tax_id = %s and cgst_tax_id = %s and igst_tax_id =%s"""%(rec.sgst_tax_id.id,rec.cgst_tax_id.id,rec.igst_tax_id.id))
			data = cr.dictfetchall()
			if len(data) > 1:
				raise osv.except_osv(_('Warning !'),_('HSN Code already exists with this tax combination'))
		return True
	
	def entry_revert(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.state == 'validated':
			self.write(cr, uid, ids, {'state': 'draft'})
		return True
	
	def entry_validate(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.state == 'draft':
			self.write(cr, uid, ids, {'state': 'validated','validated_user_id': uid, 'validated_date': time.strftime('%Y-%m-%d %H:%M:%S')})
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
			if rec.state not in ('draft','cancel'):
				raise osv.except_osv(_('Warning !'),_('Draft only can be deleted.'))
			else:
				unlink_ids.append(rec.id)
		return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
	
	def write(self, cr, uid, ids, vals, context=None):
		vals.update({'updated_date': time.strftime('%Y-%m-%d %H:%M:%S'),'updated_user_id':uid})
		return super(m_hsn_code, self).write(cr, uid, ids, vals, context)
	
	_constraints = [
		
		(_validations, ' Validations of HSN Code ', ['']),
		
	]
	
m_hsn_code()

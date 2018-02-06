from functools import partial
import logging
from lxml import etree
from lxml.builder import E
import openerp
import time
from openerp import SUPERUSER_ID
from openerp import pooler, tools
import openerp.exceptions
from openerp.osv import fields,osv
from openerp.osv.orm import browse_record
from openerp.tools.translate import _
import re
import base64

class m_partner(osv.osv):
	
	_name = "res.partner"
	_inherit = "res.partner"
	_description = "Partner Management"
	
	_columns = {
	
	'city_id' : fields.many2one('res.city','City',domain="[('state','=','validated')]"),
	'tin_no' : fields.char('TIN',size=15),
	'vat_no' : fields.char('VAT',size=12),
	'pan_no' : fields.char('PAN',size=12),
	'tan_no' : fields.char('TAN',size=12),
	'cst_no' : fields.char('CST',size=12),
	'gst_no' : fields.char('GST'),
	'gs_tin_no' : fields.char('GS TIN NO.',size=15),
	'supply_type': fields.selection([('material','Material'),('service','Service'),('contractor','Contractor'),('labour','Labour'),('all','All')],'Supply Type'),
	'company_type': fields.selection([('individual','Individual'),('company','Company'),('trust','Trust')],'Type'),
	'tds': fields.selection([('yes','Yes'),('no','No')],'TDS Applicable'),
	'grade': fields.selection([('a','A'),('b','B'),('c','C')],'Grade'),
	'payment_id': fields.many2one('m.payment.terms','Payment Terms',domain="[('state','=','validated')]"),
	'language': fields.selection([('tamil','Tamil'),('english','English'),('hindi','Hindi'),('malayalam','Malayalam'),('others','Others')],'Preferred Language'),
	'region': fields.selection([('north','North'),('east','East'),('west','West'),('south','South')],'Region'),
	'cheque_in_favour': fields.char('Cheque in Favor Of'),
	'advance_limit': fields.float('Credit Limit'),
	'transport_id': fields.many2one('m.transport','Transport',domain="[('state','=','validated')]"),
	'contact_person': fields.char('Contact Person', size=128),
	'landmark': fields.char('Landmark', size=128),
	'group_flag': fields.boolean('Is Group Company'),
	'delivery_id': fields.many2one('m.delivery.terms','Delivery Type',domain="[('state','=','validated')]"),
	'con_designation': fields.char('Designation'),
	'con_whatsapp': fields.char('Whatsapp No'),
	'dealer': fields.boolean('Dealer'),
	'economic_category': fields.selection([('budget','Budget'),('loyalty','Loyalty')],'Economic Category'),
	'sector': fields.selection([('cp','CP'),('ip','IP'),('both','Both')],'Marketing Division'),
	'dealer_id': fields.many2one('res.partner','Dealer Name',domain=[('dealer','=',True),('partner_state','=','validated')]),
	'remark': fields.text('Rejected For'),
	'cancel_remark': fields.text('Cancel Remarks'),
	'user_ref_id': fields.many2one('res.users','User Name'),
	'adhar_id': fields.char('Adhar ID',size=16),
	'contractor': fields.boolean('Contractor'),
	'tin_flag': fields.boolean('TIN Flag'),
	'mobile_2': fields.char('Mobile2',size=12),
	'email_applicable': fields.selection([('yes','Yes'),('no','No')],'Email Applicable'),
	'sms_applicable': fields.selection([('yes','Yes'),('no','No')],'SMS Applicable'),
	'max_deal_discount': fields.float('Max.Dealer Discount(%)'),
	'max_cust_discount': fields.float('Max.Customer Discount(%)'),
	'max_spl_discount': fields.float('Max.Special Discount(%)'),
	'source_mode': fields.selection([('auto','Auto'),('manual','Manual')],'Source Mode', readonly=True),
	
	## Child table declarations
	
	'delivery_ids':fields.one2many('m.delivery.address', 'src_id', 'Delivery Address'),
	'billing_ids':fields.one2many('m.billing.address', 'bill_id', 'Billing Address'),
	'consult_ids':fields.one2many('m.consultant.fee', 'consult_id', 'Consultant Fees'),
	
	## Entry Info
	
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
	  
		'is_company': True,
		'crt_date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'crt_user_id': lambda obj, cr, uid, context: uid,
		'partner_state': 'draft',
		'tin_flag': False,
		'company_type': 'company',
		'source_mode': 'manual',
	}
	
	def onchange_city(self, cr, uid, ids, city_id, context=None):
		if city_id:
			city_rec = self.pool.get('res.city').browse(cr, uid, city_id, context)		
			return {'value':{'state_id':city_rec.state_id.id,'country_id':city_rec.country_id.id}}
		else:
			pass
		return {}
	
	def onchange_zip(self,cr,uid,ids,zip,context=None):
		if len(str(zip)) in range(6,8):
			value = {'zip':zip}
		else:
			raise osv.except_osv(_('Invalid Zip code !!'),_(' Enter your correct 6-8 digits zip code !!'))
		if zip.isdigit() == False:
			raise osv.except_osv(_('Check zip number !!'),_('Please enter numeric values !!'))
		return {'value': value}
	
	def entry_reject(self, cr, uid, ids, context=None): 
		rec = self.browse(cr, uid, ids[0])
		if rec.partner_state == 'validated':
			if rec.remark:
				self.write(cr, uid, ids, {'partner_state': 'rejected','rejected_user_id':uid,'rejected_date': time.strftime('%Y-%m-%d %H:%M:%S')})
			else:
				raise osv.except_osv(_('Rejection remark is must !!'),_('Enter rejection remark in remark field !!'))
		return True
	
	def entry_validate(self, cr, uid, ids, context=None): 
		rec = self.browse(cr, uid, ids[0])
		if rec.partner_state == 'confirm':
			## Account master creation process start
			
			internal_type = note = account_receivable_id = account_payable_id =  ''
			entry_mode = 'auto'
			account_payable_id = ''
			ac_obj = self.pool.get('account.account')
			old_acc_ids = ac_obj.search(cr,uid,[('master_id','=',rec.id)])
			if old_acc_ids:
				old_acc_rec = ac_obj.browse(cr,uid,old_acc_ids[0])
				ac_obj.write(cr,uid,old_acc_rec.id,{'name': rec.name})
			acc_ids = ac_obj.search(cr,uid,[('name','=',rec.name)])
			ac_type = ''
			if not acc_ids:
				if rec.customer == True:
					ac_type_ids = self.pool.get('account.account.type').search(cr,uid,[('name','=','Asset')])
					if ac_type_ids:
						ac_type_rec = self.pool.get('account.account.type').browse(cr,uid,ac_type_ids[0])
						ac_type = ac_type_rec.id
					internal_type = 'receivable'
					note = 'New Customer Added'
					account_receivable_id = ac_obj.account_creation(cr,uid,rec.name,ac_type,rec.id,entry_mode,internal_type,note,context=context)
				if rec.supplier == True:
					internal_type = 'payable'
					note = 'New Supplier Added'
				if rec.dealer == True:
					internal_type = 'payable'
					note = 'New Delear Added'
				if rec.contractor == True:
					internal_type = 'payable'
					note = 'New Contractor Added'
				if rec.supplier == True or rec.dealer == True or rec.contractor == True:
					ac_type_ids = self.pool.get('account.account.type').search(cr,uid,[('name','=','Liability')])
					if ac_type_ids:
						ac_type_rec = self.pool.get('account.account.type').browse(cr,uid,ac_type_ids[0])
						ac_type = ac_type_rec.id
					account_payable_id = ac_obj.account_creation(cr,uid,rec.name,ac_type,rec.id,entry_mode,internal_type,note,context=context)
				
				self.write(cr, uid, ids, {'property_account_receivable':account_receivable_id,'property_account_payable':account_payable_id})
			
			## Account master creation process end
			
			self.write(cr, uid, ids, {'partner_state': 'validated','validated_user_id':uid,'validated_date': time.strftime('%Y-%m-%d %H:%M:%S')})
		
		return True
	
	def entry_revert(self,cr,uid,ids,context=None):
		rec = self.browse(cr, uid, ids[0])
		if rec.partner_state == 'validated':
			self.write(cr, uid, ids, {'partner_state': 'draft'})
		return True
	
	def unlink(self,cr,uid,ids,context=None):
		unlink_ids = []		
		for rec in self.browse(cr,uid,ids):	
			if rec.partner_state != 'draft':			
				raise osv.except_osv(_('Delete access denied!'),_('Unable to delete. Draft entry only you can delete !!'))
			else:
				unlink_ids.append(rec.id)
		return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)	
	
	def write(self, cr, uid, ids, vals, context=None):		
		vals.update({'updated_date': time.strftime('%Y-%m-%d %H:%M:%S'),'updated_by':uid})
		return super(m_partner, self).write(cr, uid, ids, vals, context)
	
	def _validations(self, cr, uid, ids, context=None):		
		rec = self.browse(cr, uid, ids[0])
		if rec.zip:
			if len(str(rec.zip)) not in range(6,8) and rec.zip.isdigit() != True:
				raise osv.except_osv(_('Invalid Zip code !!'),_('Enter your correct 6-8 digits zip code !!'))
		if rec.gs_tin_no:
			if len(str(rec.gs_tin_no)) != 15:
				raise osv.except_osv(_('Warning !!'),_('GS TIN No. should contain 15 letters. Else system not allow to save. !!'))
		if rec.cst_no:
			if len(str(rec.cst_no)) != 11 and rec.cst_no.isdigit() != True:
				raise osv.except_osv(_('Warning !!'),_('Enter your correct 11 digits GS TIN No. !!'))
		if rec.vat_no:
			if len(str(rec.vat_no)) != 15:
				raise osv.except_osv(_('Warning !!'),_('Enter your correct 15 letters VAT No. !!'))
		if rec.phone:
			if len(str(rec.phone)) not in range(8,15) and rec.phone.isdigit() != True:
				raise osv.except_osv(_('Warning !!'),_('Enter your correct 8-15 digit numerics. Phone No. !!'))
		if rec.email != False:
			if re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", rec.email) == None:
				raise osv.except_osv(_('Invalid Email !!'),_('Enter a valid email address !!'))
		if rec.website != False:
			#~ if re.match('www?.(?:www)?(?:[\w-]{2,255}(?:\.\w{2,6}){1,2})(?:/[\w&%?#-]{1,300})?',rec.website):
			if not re.match('www.(?:www)?(?:[\w-]{2,255}(?:\.\w{2,6}){1,2})(?:/[\w&%?#-]{1,300})?',rec.website):
				raise osv.except_osv(_('Invalid Email !!'),_('Enter a valid Website !!'))
		if rec.bank_ids:
			for item in rec.bank_ids:
				if item.bank_bic:
					if len(str(item.bank_bic)) != 11:
						raise osv.except_osv(_('Warning !!'),_('IFSC should contain 11 letters. !!'))
		if rec.bank_ids:
			for item in rec.bank_ids:
				if item.acc_number:
					if len(str(item.acc_number)) not in range(6,18) and item.acc_number.isdigit() != True:
						raise osv.except_osv(_('Warning !!'),_('Enter your correct 6-18 digit numerics. A/C No. !!'))
		if rec.mobile:
			if len(str(rec.mobile)) not in range(10,12) and rec.mobile.isdigit() != True:
				raise osv.except_osv(_('Warning !!'),_('Enter your correct 10-12 digit numerics. Mobile No. !!'))
		
		if rec.max_deal_discount > 100 and rec.dealer == True:
			raise osv.except_osv(_('Warning!'),_('Max dealer discount(%) should not be accept above 100!'))
		if rec.max_cust_discount > 100 and rec.customer == True:
			raise osv.except_osv(_('Warning!'),_('Max customer discount(%) should not be accept above 100!'))
		if rec.max_spl_discount > 100 and rec.customer == True:
			raise osv.except_osv(_('Warning!'),_('Max special discount(%) should not be accept above 100!'))
		
		if rec.delivery_ids:
			ser_dups = self.pool.get('m.delivery.address').search(cr,uid,[('src_id','=',rec.id),('default','=','t')])
			if len(ser_dups) > 1:
				raise osv.except_osv(_('Warning!'),_('More than one default Delivery address is not allowed !! '))
				
		if rec.billing_ids:
			ser_dups = self.pool.get('m.billing.address').search(cr,uid,[('bill_id','=',rec.id),('default','=','t')])
			if len(ser_dups) > 1:
				raise osv.except_osv(_('Warning!'),_('More than one default Billing address is not allowed !! '))
	
		return True
	
	def _name_validate(self, cr, uid,ids, context=None):
		rec = self.browse(cr,uid,ids[0])
		res = True
		data=''
		if rec.name:
			partner_name = rec.name
			name=partner_name.upper()
			if rec.customer == True:
				cr.execute(""" select upper(name) from res_partner where upper(name) = '%s' and customer = True """ %(name))
				data = cr.dictfetchall()
			elif rec.supplier == True:
				cr.execute(""" select upper(name) from res_partner where upper(name) = '%s' and supplier = True """ %(name))
				data = cr.dictfetchall()
			elif rec.dealer == True:
				cr.execute(""" select upper(name) from res_partner where upper(name) = '%s' and dealer = True """ %(name))
				data = cr.dictfetchall()
			elif rec.contractor == True:
				cr.execute(""" select upper(name) from res_partner where upper(name) = '%s' and contractor = True """ %(name))
				data = cr.dictfetchall()
			if len(data) > 1:
				res = False
			else:
				res = True
		return res
	
	_constraints = [
		
		(_validations,' ',[' ']),
		#~ (_name_validate, ' ', [' ']),
		
		]
	
m_partner()

class m_delivery_address(osv.osv):
	
	_name = "m.delivery.address"
	_description = "Delivery Address"
	
	_columns = {
	
	'name': fields.char('Name'),
	'src_id': fields.many2one('res.partner', 'Partner Master'),
	'street': fields.char('Street', size=128,select=True),
	'street1': fields.char('Street 1', size=128,select=True),
	'landmark': fields.char('Landmark',size=128),
	'city_id': fields.many2one('res.city', 'City',select=True,domain="[('state','=','validated')]"),
	'state_id': fields.many2one('res.country.state','State',domain="[('state','=','validated')]"),
	'country_id': fields.many2one('res.country','Country',domain="[('state','=','validated')]"),
	'contact_no': fields.char('Contact No', size=12),
	'zip': fields.char('ZIP', size=8),
	'date': fields.date('Creation Date'),
	'default': fields.boolean('Default'),
	
	}
	
	_defaults = {
	
	'date' : lambda * a: time.strftime('%Y-%m-%d'),
	
	}
	
	def onchange_city(self, cr, uid, ids, city_id, context=None):
		if city_id:
			city_rec = self.pool.get('res.city').browse(cr, uid, city_id, context)		
			return {'value':{'state_id':city_rec.state_id.id,'country_id':city_rec.country_id.id}}
		else:
			pass
		return {}

m_delivery_address()

class m_billing_address(osv.osv):
	
	_name = "m.billing.address"
	_description = "Billing Address"
	
	_columns = {
	
	'name': fields.char('Name'),
	'bill_id': fields.many2one('res.partner','Partner Master'),
	'street': fields.char('Street', size=128,select=True),
	'street1': fields.char('Street 1', size=128,select=True),
	'landmark': fields.char('Landmark',size=128),
	'city_id': fields.many2one('res.city', 'City',select=True,domain="[('state','=','validated')]"),
	'state_id': fields.many2one('res.country.state','State',domain="[('state','=','validated')]"),
	'country_id': fields.many2one('res.country','Country',domain="[('state','=','validated')]"),
	'contact_no': fields.char('Contact No', size=12),
	'zip': fields.char('ZIP', size=8),
	'date': fields.date('Creation Date'),
	'default': fields.boolean('Default'),
	
	}
	
	_defaults = {
	
	'date' : lambda * a: time.strftime('%Y-%m-%d'),
	
	} 
	
	def onchange_city(self, cr, uid, ids, city_id, context=None):
		if city_id:
			city_rec = self.pool.get('res.city').browse(cr, uid, city_id, context)		
			return {'value':{'state_id':city_rec.state_id.id,'country_id':city_rec.country_id.id}}
		else:
			pass
		return {}
		
m_billing_address()

class m_consultant_fee(osv.osv):
	
	_name = "m.consultant.fee"
	_description = "Consultant Fees"
	
	_columns = {
	
	'consult_id': fields.many2one('res.partner', 'Partner Master'),
	'effective_date': fields.date('Effective Date'),
	'value': fields.float('Value (%)'),
	'state': fields.selection([('active','Active'),('expire','Expired')],'Status'),
	'read_flag': fields.boolean('Read Flag'),
	
	}
	
	_defaults = {
	
	'state' : 'active',
	'read_flag': False,
	
	}
	
	def create(self, cr, uid, vals, context=None):
		new_id = super(m_consultant_fee, self).create(cr, uid, vals, context=context)
		partner = self.browse(cr, uid, new_id, context=context)
		obj = self.search(cr,uid,([('consult_id','=',vals['consult_id'])]))
		if obj:
			for item in obj:
				self.write(cr,uid,item,{'state':'expire','read_flag':True})
			self.write(cr,uid,obj[-1],{'state':'active','read_flag':False})
		return new_id
	
m_consultant_fee()

class ch_bank_details(osv.osv):
	
	_name = "res.partner.bank"
	_description = "Bank Details"
	_inherit = 'res.partner.bank'
	
	_columns = {
	
	'city_id': fields.many2one('res.city','City',domain="[('state','=','validated')]"),
	
	}
	
	def onchange_city(self, cr, uid, ids, city_id, context=None):
		if city_id:
			city_rec = self.pool.get('res.city').browse(cr, uid, city_id, context)		
			return {'value':{'state_id':city_rec.state_id.id,'country_id':city_rec.country_id.id}}
		else:
			pass
		return {}
	
ch_bank_details()

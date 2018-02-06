import re
from _common import rounding
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
from operator import itemgetter
from itertools import groupby
from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import base64

UOM_CONVERSATION = [

    ('one_dimension','One Dimension'),('two_dimension','Two Dimension')
]

class m_product(osv.osv):
	
	_name = "product.product"
	_inherit = "product.product"
	
	_columns = {
		
		'capital': fields.boolean('Capital Goods'),
		'abc': fields.boolean('ABC Analysis'),
		'po_uom_coeff': fields.float('PO Coeff', digits=(16,10), required=True, help="One Purchase Unit of Measure = Value of(PO Coeff)UOM"),
		'product_type': fields.selection([('raw','Raw Materials'),('consu','Consumables'),
											('capital','Capitals and Asset'),('service','Service Items')],'Product Type',required=True,readonly=False,states={'validated':[('readonly',True)]}),
		'remark': fields.text('Approve/Reject Remarks',readonly=False,states={'validated':[('readonly',True)]}),
		'cancel_remark': fields.text('Cancel Remarks'),
		'od': fields.float('OD'),
		'breadth': fields.float('Breadth'),
		'length': fields.float('Length'),
		'thickness': fields.float('Thickness'),
		'weight': fields.float('Weight'),
		'po_uom_in_kgs': fields.float('PO UOM in kgs',digits=(16,10),readonly=False,states={'validated':[('readonly',True)]}),
		'uom_conversation_factor': fields.selection(UOM_CONVERSATION,'UOM Conversation Factor',required=True,readonly=False,states={'validated':[('readonly',True)]}),
		'price_type': fields.selection([('po_uom','PO UOM'),('per_kg','Per Kg')],'Price Type'),
		'service_factor': fields.float('Service Factor'),
		'power_kw': fields.float('Power in KW'),
		'speed_in_rpm': fields.float('Speed In RPM'),
		'max_bore': fields.float('MAX Bore'),
		'coupling_size': fields.float('Coupling Size'),
		'spacer_length': fields.float('Spacer Length'),
		'mechanical_type': fields.char('Type'),
		'operating_condition': fields.char('Operating Condition'),
		'face_combination': fields.char('Face Combination'),
		'api_plan': fields.char('API Plan'),
		'gland_placement': fields.char('Gland Placement'),
		'gland_plate': fields.selection([('w_gland_plate','With Gland Plate'),('wo_gland_plate','Without Gland Plate')],'Gland Plate'),
		'sleeve_dia': fields.char('Sleeve dia(MM)'),
		'is_depreciation': fields.boolean('Is Depreciation'),
		'hsn_no': fields.many2one('m.hsn.code','HSN No.',domain="[('state','=','validated')]"),
		'uom_code': fields.related('uom_id','code', type='char', string='Store UOM Code'),
		
		## Child
		
		'avg_line_ids':fields.one2many('ch.product.yearly.average.price','product_id','Line Entry'),
		
		# Entry Info
		
		'crt_date': fields.datetime('Created On',readonly=True),
		'crt_user_id': fields.many2one('res.users', 'Created By', readonly=True),
		'validated_date': fields.datetime('Validated On', readonly=True),
		'validated_user_id': fields.many2one('res.users', 'Validated By', readonly=True),
		'rejected_date': fields.datetime('Rejected On', readonly=True),
		'rejected_user_id': fields.many2one('res.users', 'Rejected By', readonly=True),
		'updated_date': fields.datetime('Recent Update On', readonly=True),
		'updated_user_id': fields.many2one('res.users', 'Recent Update By', readonly=True),		
		'source_mode': fields.selection([('auto','Auto'),('manual','Manual')],'Source Mode', readonly=True),
		
	}
	
	_defaults = {
		
		'po_uom_coeff': 0.00,
		'user_id': lambda obj, cr, uid, context: uid,
		'crt_user_id': lambda obj, cr, uid, context: uid,
		'crt_date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'source_mode': 'manual',
		
	}
	
	def _po_coeff(self, cr, uid, ids, context=None):
		rec = self.browse(cr, uid, ids[0])
		if rec.uom_id != rec.uom_po_id and rec.po_uom_coeff == 0 and rec.state != 'approved':
			raise osv.except_osv(_('Warning !'),_('Please check and update PO Coeff for %s in product master !!'%(rec.name)))
		if rec.uom_id == rec.uom_po_id and rec.po_uom_coeff != 1:
			raise osv.except_osv(_('Warning !'),_('Both UOM is same so configure PO Coff as 1 for %s !!'%(rec.name)))
		return True	
	
	def _name_validate(self, cr, uid,ids, context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.price_type:
			if rec.price_type == 'per_kg' and rec.po_uom_in_kgs <= 0.00:
				raise osv.except_osv(_('Warning!'),_('Configure PO UOM in kgs in (%s) !!'%(rec.name)))
		if rec.uom_id.id != rec.uom_po_id.id and rec.po_uom_coeff <= 0.00:
			raise osv.except_osv(_('Warning!'),_('Configure PO Coeff in (%s) !!'%(rec.name)))
		if rec.uom_id.code == 'Kg' and rec.po_uom_in_kgs <= 0.00:
			raise osv.except_osv(_('Warning!'),_('Configure PO UOM in kgs in (%s) !!'%(rec.name)))
		if rec.uom_id.id == rec.uom_po_id.id and rec.po_uom_coeff <= 0.00:
			raise osv.except_osv(_('Warning!'),_('Configure PO Coeff in (%s) !!'%(rec.name)))
		if rec.minimum_qty < 0:
			raise osv.except_osv(_('Warning!'),_('Minimum Stock Qty System not allow to save negative and zero values in (%s) !!'%(rec.name)))
		if rec.reorder_qty < 0:
			raise osv.except_osv(_('Warning!'),_('Re-order Qty System not allow to save negative and zero values in (%s) !!'%(rec.name)))
		if rec.tolerance_applicable == True and rec.tolerance_plus <= 0:
			raise osv.except_osv(_('Warning!'),_('Tolerance(+) should be greater than zero in (%s) !!'%(rec.name)))
		if rec.price_type == 'per_kg':
			if rec.uom_po_id.code != 'Kg' and rec.uom_id.code != 'Kg':
				raise osv.except_osv(_('Warning !'),_('If price type is Per Kg select Kgs either Store UOM or PO UOM !!'))
			if rec.po_uom_in_kgs <= 0:
				raise osv.except_osv(_('Warning !'),_('PO UOM in kgs should be greater than Zero !!'))
			#~ if rec.uom_po_id.code == 'Kg':
				#~ raise osv.except_osv(_('Warning !'),_('Select PO UOM in Price Type !!'))
		if rec.pro_seller_ids:
			for line in rec.pro_seller_ids:
				cr.execute(""" select id from product_supplierinfo where name = %s and product_id = %s """ %(line.name.id,rec.id))
				data = cr.dictfetchall()
				if len(data) > 1:
					raise osv.except_osv(_('Warning !'),_('Supplier (%s) must be unique !!')%(line.name.name))
		res = True
		return res 
	
	_constraints = [
		
		(_name_validate, 'product name must be unique !!', ['name']),
		
	]
	
	def entry_validate(self,cr,uid,ids,context=None):
		rec = self.browse(cr, uid, ids[0])
		if rec.state == 'draft':
			self.write(cr, uid, ids, {'state': 'validated','app_user_id': uid, 'approve_date': time.strftime('%Y-%m-%d %H:%M:%S')})
		return True
	
	def entry_revert(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.state == 'validated':
			self.write(cr, uid, ids, {'state':'draft'})
		return True
	
	def entry_reject(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.state == 'validated':
			if rec.remark:
				self.write(cr, uid, ids, {'state':'rejected','rej_user_id':uid,'reject_date':time.strftime('%Y-%m-%d %H:%M:%S')})
			else:
				raise osv.except_osv(_('Warning !'),_('Enter rejection remark in remark field !!'))
		return True
	
	def write(self,cr,uid,ids,vals,context={}):
		if 'tolerance_applicable' in vals:
			if vals['tolerance_applicable'] == True:
				if 'tolerance_plus' in vals:
					if vals['tolerance_plus'] <= 0.00:
						raise osv.except_osv(_('Warning !'),_('Tolerance value should be greater than zero !!'))
					else:
						pass
				else:
					pass
			else:
				pass
		return super(m_product, self).write(cr, uid, ids,vals, context)
	
m_product()

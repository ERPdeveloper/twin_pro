# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################
from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
import time
import openerp.addons.decimal_precision as dp
from datetime import datetime
import math

def location_name_search(self, cr, user, name='', args=None, operator='ilike',
                         context=None, limit=100):
    if not args:
        args = []

    ids = []
    if len(name) == 2:
        ids = self.search(cr, user, [('code', 'ilike', name)] + args,
                          limit=limit, context=context)

    search_domain = [('name', operator, name)]
    if ids: search_domain.append(('id', 'not in', ids))
    ids.extend(self.search(cr, user, search_domain + args,
                           limit=limit, context=context))

    locations = self.name_get(cr, user, ids, context)
    return sorted(locations, key=lambda (id, name): ids.index(id))

class Country(osv.osv):
    _name = 'res.country'
    _description = 'Country'
    _order='name'
    _columns = {
        'name': fields.char('Name', size=64,
            help='The full name of the country.', required=True, translate=True),
        'code': fields.char('Code', size=5,
            help='The ISO country code in two chars.\n'
            'You can use this field for quick search.'),
        'address_format': fields.text('Address Format', help="""You can state here the usual format to use for the \
addresses belonging to this country.\n\nYou can use the python-style string patern with all the field of the address \
(for example, use '%(street)s' to display the field 'street') plus
            \n%(state_name)s: the name of the state
            \n%(state_code)s: the code of the state
            \n%(country_name)s: the name of the country
            \n%(country_code)s: the code of the country"""),
        'currency_id': fields.many2one('res.currency', 'Currency'),
        
        ## Newly added by openerp developers ##
        
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
    }
    _sql_constraints = [
        ('name_uniq', 'unique (name)',
            'The name of the country must be unique !'),
        ('code_uniq', 'unique (code)',
            'The code of the country must be unique !')
    ]
    _defaults = {
        'address_format': "%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s",
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'res.country', context=c),
		'active': True,
		'state': 'draft',
		'crt_user_id': lambda obj, cr, uid, context: uid,
		'crt_date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'source_mode': 'manual',
    }
    

    name_search = location_name_search
    
    def write(self, cr, uid, ids, vals, context=None):
		vals.update({'updated_date': time.strftime('%Y-%m-%d %H:%M:%S'),'updated_user_id':uid})
		return super(Country, self).write(cr, uid, ids, vals, context)
    
    def create(self, cursor, user, vals, context=None):
		if vals.get('code'):
			vals['code'] = vals['code'].upper()
		return super(Country, self).create(cursor, user, vals,
				context=context)
    
    def unlink(self,cr,uid,ids,context=None):
		unlink_ids = []
		for rec in self.browse(cr,uid,ids):
			if rec.state not in ('draft','cancel'):
				raise osv.except_osv(_('Warning !'),_('Draft only can be deleted.'))
			else:
				unlink_ids.append(rec.id)
		return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
    
    def entry_reject(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.state == 'validated':
			if rec.remark:
				self.write(cr, uid, ids, {'state': 'rejected','rejected_user_id': uid, 'rejected_date': time.strftime('%Y-%m-%d %H:%M:%S')})
			else:
				raise osv.except_osv(_('Warning !'),_('Enter Reason For rejection.'))
		return True
    
    def entry_validate(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.state == 'draft':
			self.write(cr, uid, ids, {'state': 'validated','validated_user_id': uid, 'validated_date': time.strftime('%Y-%m-%d %H:%M:%S')})
		return True
    
    def entry_revert(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.state == 'validated':
			self.write(cr, uid, ids, {'state': 'draft'})
		return True

Country()

class CountryState(osv.osv):
    _description="Country state"
    _name = 'res.country.state'
    _order = 'name'
    _columns = {
        'country_id': fields.many2one('res.country', 'Country',
            required=True),
        'name': fields.char('Name', size=64, required=True, 
                            help='Administrative divisions of a country. E.g. Fed. State, Departement, Canton'),
        'code': fields.char('Code', size=5,
            help='The state code in max. three chars.', required=True),
            
		## Newly added by openerp developers ##
        
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
		
    }
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)',
            'The name of the country must be unique !'),
        ('code_uniq', 'unique (code)',
            'The code of the country must be unique !')
    ]
    
    _defaults = {
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'res.country', context=c),
		'active': True,
		'state': 'draft',
		'crt_user_id': lambda obj, cr, uid, context: uid,
		'crt_date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'source_mode': 'manual',
    }

    name_search = location_name_search
    
    def write(self, cr, uid, ids, vals, context=None):
		vals.update({'updated_date': time.strftime('%Y-%m-%d %H:%M:%S'),'updated_user_id':uid})
		return super(CountryState, self).write(cr, uid, ids, vals, context)
    
    #~ def create(self, cursor, user, vals, context=None):
		#~ if vals.get('code'):
			#~ vals['code'] = vals['code'].upper()
		#~ return super(Country, self).create(cursor, user, vals,
				#~ context=context)
    
    def unlink(self,cr,uid,ids,context=None):
		unlink_ids = []
		for rec in self.browse(cr,uid,ids):
			if rec.state not in ('draft','cancel'):
				raise osv.except_osv(_('Warning !'),_('Draft only can be deleted.'))
			else:
				unlink_ids.append(rec.id)
		return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
    
    def entry_reject(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.state == 'validated':
			if rec.remark:
				self.write(cr, uid, ids, {'state': 'rejected','rejected_user_id': uid, 'rejected_date': time.strftime('%Y-%m-%d %H:%M:%S')})
			else:
				raise osv.except_osv(_('Warning !'),_('Enter Reason For rejection.'))
		return True
    
    def entry_validate(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.state == 'draft':
			self.write(cr, uid, ids, {'state': 'validated','validated_user_id': uid, 'validated_date': time.strftime('%Y-%m-%d %H:%M:%S')})
		return True
    
    def entry_revert(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.state == 'validated':
			self.write(cr, uid, ids, {'state': 'draft'})
		return True

CountryState()
		
class city(osv.osv):
    _description="City"
    _name = 'res.city'
    _order = 'name'
    _columns = {
        'country_id': fields.many2one('res.country', 'Country',required=True),
        'state_id': fields.many2one('res.country.state', 'State',required=True),
        'name': fields.char('Name', size=64, required=True,help='Administrative divisions of a country. E.g. Fed. State, Departement, Canton'),
        'code': fields.char('Code', size=5,help='The state code in max. three chars.', required=True),
            
		## Newly added by openerp developers ##
        
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
		
    }
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)',
            'The name of the country must be unique !'),
        ('code_uniq', 'unique (code)',
            'The code of the country must be unique !')
    ]
    
    _defaults = {
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'res.city', context=c),
		'active': True,
		'state': 'draft',
		'crt_user_id': lambda obj, cr, uid, context: uid,
		'crt_date': lambda * a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'source_mode': 'manual',
    }

    name_search = location_name_search
    
    def write(self, cr, uid, ids, vals, context=None):
		vals.update({'updated_date': time.strftime('%Y-%m-%d %H:%M:%S'),'updated_user_id':uid})
		return super(city, self).write(cr, uid, ids, vals, context)
    
    #~ def create(self, cursor, user, vals, context=None):
		#~ if vals.get('code'):
			#~ vals['code'] = vals['code'].upper()
		#~ return super(Country, self).create(cursor, user, vals,
				#~ context=context)
    
    def unlink(self,cr,uid,ids,context=None):
		unlink_ids = []
		for rec in self.browse(cr,uid,ids):
			if rec.state not in ('draft','cancel'):
				raise osv.except_osv(_('Warning !'),_('Draft only can be deleted.'))
			else:
				unlink_ids.append(rec.id)
		return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
    
    def entry_reject(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.state == 'validated':
			if rec.remark:
				self.write(cr, uid, ids, {'state': 'rejected','rejected_user_id': uid, 'rejected_date': time.strftime('%Y-%m-%d %H:%M:%S')})
			else:
				raise osv.except_osv(_('Warning !'),_('Enter Reason For rejection.'))
		return True
    
    def entry_validate(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.state == 'draft':
			self.write(cr, uid, ids, {'state': 'validated','validated_user_id': uid, 'validated_date': time.strftime('%Y-%m-%d %H:%M:%S')})
		return True
    
    def entry_revert(self,cr,uid,ids,context=None):
		rec = self.browse(cr,uid,ids[0])
		if rec.state == 'validated':
			self.write(cr, uid, ids, {'state': 'draft'})
		return True
	
city()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


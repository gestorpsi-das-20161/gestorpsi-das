# -*- coding: utf-8 -*-
from django.db import models
from gestorpsi.organization.models import Organization
from django.contrib.auth.models import User, UserManager
from gestorpsi.util.uuid_field import UuidField
from gestorpsi.util import CryptographicUtils as cryptoUtils

class CustomUser(User):
    id= UuidField(primary_key=True)
    organization = models.ManyToManyField(Organization, null=True)
    try_login = models.IntegerField(default = 0, null=True)
    crypt_temp = models.CharField(max_length=50, blank=True)
    org_active = models.OneToOneField(Organization, related_name="org_active", null=True)
    
    # Use UserManager to get the create_user method, etc.
    objects = UserManager()
    
    def _set_temp(self, value):
        self.crypt_temp= cryptoUtils.encrypt_attrib( value )
        
    def _get_temp(self):
        return cryptoUtils.decrypt_attrib( self.crypt_temp )
    
    temp= property( _get_temp, _set_temp )
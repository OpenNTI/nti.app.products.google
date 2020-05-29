#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.securitypolicy.interfaces import IRolePermissionManager

from zope.securitypolicy.rolepermission import RolePermissionManager

from nti.app.products.google.sso.interfaces import IGoogleLogonSettings
from nti.app.products.google.sso.interfaces import IGoogleSSOIntegration

from nti.dataserver.authorization import ACT_NTI_ADMIN
from nti.dataserver.authorization import ROLE_SITE_ADMIN

from nti.externalization.persistence import NoPickle

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IRolePermissionManager)
@component.adapter(IGoogleSSOIntegration)
@NoPickle
class GoogleSSOIntegrationRolePermissionManager(RolePermissionManager):
    """
    A Zope `IRolePermissionManager` that denies access by site admins.
    """

    def __init__(self, unused_integration):
        super(GoogleSSOIntegrationRolePermissionManager, self).__init__()
        self.denyPermissionToRole(ACT_NTI_ADMIN.id, ROLE_SITE_ADMIN.id)


@interface.implementer(IRolePermissionManager)
@component.adapter(IGoogleLogonSettings)
@NoPickle
class GoogleLogonSettingsRolePermissionManager(RolePermissionManager):
    """
    A Zope `IRolePermissionManager` that denies access by site admins.
    """

    def __init__(self, unused_integration):
        super(GoogleLogonSettingsRolePermissionManager, self).__init__()
        self.denyPermissionToRole(ACT_NTI_ADMIN.id, ROLE_SITE_ADMIN.id)

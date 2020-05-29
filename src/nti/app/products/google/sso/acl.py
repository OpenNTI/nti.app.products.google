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

from zope.cachedescriptors.property import Lazy

from nti.app.products.google.sso.interfaces import IGoogleLogonSettings
from nti.app.products.google.sso.interfaces import IGoogleSSOIntegration

from nti.dataserver.authorization_acl import acl_from_aces

from nti.dataserver.interfaces import ACE_DENY_ALL

from nti.dataserver.interfaces import IACLProvider


@interface.implementer(IACLProvider)
@component.adapter(IGoogleSSOIntegration)
class _GoogleSSOIntegrationACLProvider(object):

    def __init__(self, context):
        self.context = context

    @property
    def __parent__(self):
        # See comments in nti.dataserver.authorization_acl:has_permission
        return self.context.__parent__

    @Lazy
    def __acl__(self):
        return acl_from_aces([ACE_DENY_ALL])


@interface.implementer(IACLProvider)
@component.adapter(IGoogleLogonSettings)
class _GoogleLogonSettingsACLProvider(object):

    def __init__(self, context):
        self.context = context

    @property
    def __parent__(self):
        # See comments in nti.dataserver.authorization_acl:has_permission
        return self.context.__parent__

    @Lazy
    def __acl__(self):
        return acl_from_aces([ACE_DENY_ALL])

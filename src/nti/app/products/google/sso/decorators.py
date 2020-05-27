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

from zope.container.interfaces import ILocation

from nti.app.products.google.sso import ENABLE_GOOGLE_SSO_VIEW

from nti.app.products.google.sso.interfaces import IGoogleLogonSettings
from nti.app.products.google.sso.interfaces import IGoogleSSOIntegration
from nti.app.products.google.sso.interfaces import IPersistentGoogleLogonSettings

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.appserver.pyramid_authorization import has_permission

from nti.dataserver.authorization import ACT_NTI_ADMIN

from nti.dataserver.interfaces import IDataserverFolder

from nti.externalization.interfaces import IExternalMappingDecorator
from nti.externalization.interfaces import StandardExternalFields

from nti.links.links import Link

from nti.traversal.traversal import find_interface

LINKS = StandardExternalFields.LINKS

logger = __import__('logging').getLogger(__name__)


def located_link(parent, link):
    interface.alsoProvides(link, ILocation)
    link.__name__ = ''
    link.__parent__ = parent
    return link


@component.adapter(IGoogleSSOIntegration)
@interface.implementer(IExternalMappingDecorator)
class _GoogleSSOIntegrationDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _predicate(self, context, unused_result):
        # Only NT Admins for now`
        return super(_GoogleSSOIntegrationDecorator, self)._predicate(context, unused_result) \
           and has_permission(ACT_NTI_ADMIN, context, self.request)

    def _do_decorate_external(self, context, result):
        links = result.setdefault(LINKS, [])
        link = None
        logon_settings = component.queryUtility(IGoogleLogonSettings)
        link_context = find_interface(context, IDataserverFolder)
        if logon_settings is None:
            link = Link(link_context,
                        elements=("@@" + ENABLE_GOOGLE_SSO_VIEW,),
                        rel='enable')
        elif IPersistentGoogleLogonSettings.providedBy(logon_settings):
            # Only persistent keys can be deactivated
            link = Link(logon_settings,
                        method='DELETE',
                        rel='disable')
        if link is not None:
            links.append(located_link(link_context, link))


@component.adapter(IPersistentGoogleLogonSettings)
@interface.implementer(IExternalMappingDecorator)
class _GoogleLogonSettingsDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _predicate(self, context, unused_result):
        # Only NT Admins for now`
        return super(_GoogleLogonSettingsDecorator, self)._predicate(context, unused_result) \
           and has_permission(ACT_NTI_ADMIN, context, self.request)

    def _do_decorate_external(self, context, result):
        links = result.setdefault(LINKS, [])
        link = Link(context,
                    method='DELETE')
        edit_link = Link(context,
                         method='PUT',
                         rel='edit')
        links.append(link)
        links.append(edit_link)

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

from nti.app.products.google.sso.authorization import ACT_ENABLE_GOOGLE_SSO

from nti.app.products.google.sso.interfaces import IGoogleSSOIntegration

from nti.app.products.integration.integration import AbstractIntegration

from nti.app.products.integration.interfaces import IIntegrationCollectionProvider

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.app.store.license_utils import can_integrate

from nti.appserver.pyramid_authorization import has_permission

from nti.common.interfaces import IOAuthKeys
from nti.common.interfaces import IPersistentOAuthKeys

from nti.externalization.interfaces import IExternalMappingDecorator
from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.representation import WithRepr

from nti.links.links import Link

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

LINKS = StandardExternalFields.LINKS

logger = __import__('logging').getLogger(__name__)


def located_link(parent, link):
    interface.alsoProvides(link, ILocation)
    link.__name__ = ''
    link.__parent__ = parent
    return link


@WithRepr
@interface.implementer(IGoogleSSOIntegration)
class GoogleSSOIntegration(AbstractIntegration,
                           SchemaConfigured):
    createDirectFieldProperties(IGoogleSSOIntegration)

    __external_can_create__ = False

    __name__ = u'google_sso'

    mimeType = mime_type = "application/vnd.nextthought.integration.googlessointegration"


@interface.implementer(IIntegrationCollectionProvider)
class GoogleIntegrationProvider(object):

    def get_collection_iter(self):
        """
        Return a GoogleSSOIntegration object by which we can enable
        Google SSO authentication.
        """
        result = ()
        if can_integrate():
            result = (GoogleSSOIntegration(title=u'Integrate with Google SSO'),)
        return result


@component.adapter(IGoogleSSOIntegration)
@interface.implementer(IExternalMappingDecorator)
class _GoogleSSOIntegrationDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _predicate(self, context, unused_result):
        return super(_GoogleSSOIntegrationDecorator, self)._predicate(context, unused_result) \
           and has_permission(ACT_ENABLE_GOOGLE_SSO, context, self.request)

    def _do_decorate_external(self, context, result):
        # FIXME: integratoin context?
        links = result.setdefault(LINKS, [])
        link = None
        oauth_keys = component.queryUtility(IOAuthKeys, name="google")
        if oauth_keys is None:
            link = Link(context,
                        elements=("@@" + ENABLE_GOOGLE_SSO_VIEW,),
                        rel='enable_google_sso')
        elif IPersistentOAuthKeys.providedBy(oauth_keys):
            # Only persistent keys can be deactivated
            link = Link(context,
                        method='DELETE',
                        rel='disable_google_sso')
        if link is not None:
            links.append(located_link(context, link))

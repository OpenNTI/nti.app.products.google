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

from nti.app.products.google.interfaces import IGoogleAPIKey

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.appserver.pyramid_authorization import has_permission

from nti.dataserver.authorization import ACT_READ

from nti.dataserver.interfaces import IDataserver

from nti.externalization.interfaces import IExternalMappingDecorator
from nti.externalization.interfaces import StandardExternalFields

from nti.links.links import Link

LINKS = StandardExternalFields.LINKS

logger = __import__('logging').getLogger(__name__)


@component.adapter(IGoogleAPIKey)
@interface.implementer(IExternalMappingDecorator)
class _GoogleAPIKeyDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _predicate(self, context, unused_result):
        return has_permission(ACT_READ, context, self.request)

    def _do_decorate_external(self, context, result):
        links = result.setdefault(LINKS, [])
        ds_folder = component.getUtility(IDataserver)
        ds_folder = ds_folder.dataserver_folder
        link = Link(ds_folder,
                    elements=('++etc++googleapikeys', context.__name__, "@@google.oauth.authorize",),
                    rel='google.authorize')
        links.append(link)

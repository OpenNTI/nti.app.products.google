#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from nti.app.products.google.sso.interfaces import IGoogleSSOIntegration

from nti.app.products.integration.integration import AbstractIntegration

from nti.app.products.integration.interfaces import IIntegrationCollectionProvider

from nti.externalization.representation import WithRepr

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

logger = __import__('logging').getLogger(__name__)


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

    def can_integrate(self):
        #TODO: query site policy/license
        return True

    def get_collection_iter(self):
        """
        Return a GoogleSSOIntegration object by which we can enable
        Google SSO authentication.
        """
        result = ()
        if self.can_integrate():
            result = (GoogleSSOIntegration(title=u'Integrate with Google SSO'),)
        return result

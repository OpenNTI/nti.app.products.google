#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id: model.py 124702 2017-12-08 21:11:48Z carlos.sanchez $
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from zope.container.contained import Contained

from nti.app.products.google.sso.interfaces import IGoogleLogonSettings
from nti.app.products.google.sso.interfaces import IPersistentGoogleLogonSettings

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.externalization.representation import WithRepr

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

logger = __import__('logging').getLogger(__name__)


class AbstractGoogleLogonSettings(SchemaConfigured):

    __parent__ = None
    __name__ = None


@WithRepr
@interface.implementer(IGoogleLogonSettings)
class GoogleLogonSettings(AbstractGoogleLogonSettings):

    createDirectFieldProperties(IGoogleLogonSettings)
    mimeType = mime_type = "application/vnd.nextthought.site.googlelogonsettings"


@WithRepr
@interface.implementer(IPersistentGoogleLogonSettings)
class PersistentGoogleLogonSettings(PersistentCreatedModDateTrackingObject,
                                    Contained,
                                    AbstractGoogleLogonSettings):

    createDirectFieldProperties(IPersistentGoogleLogonSettings)
    mimeType = mime_type = "application/vnd.nextthought.site.persistentgooglelogonsettings"

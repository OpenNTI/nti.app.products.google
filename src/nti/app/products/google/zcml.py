#!/usr/bin/env python
# -*- coding: utf-8 -*

import functools

from zope import interface

from zope.component.zcml import utility

from nti.schema.field import ValidTextLine

from nti.app.products.google.interfaces import IGoogleAPIKey

from nti.app.products.google.traversal import GoogleAPIKey

logger = __import__('logging').getLogger(__name__)


class IRegisterGoogleApiKey(interface.Interface):

    name = ValidTextLine(title=u'The name for this key',
                        required=True)

    appid = ValidTextLine(title=u'The name for this key',
                          required=True)

    key = ValidTextLine(title=u'The API Key',
                        required=True)


def registerGoogleAPIKey(_context, name, appid, key):
    """
    Register google logon settings.
    """
    factory = functools.partial(GoogleAPIKey, name, appid, key)
    utility(_context, provides=IGoogleAPIKey, factory=factory, name=name)

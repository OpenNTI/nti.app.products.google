#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id: zcml.py 124707 2017-12-08 21:48:18Z carlos.sanchez $
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class

import functools

from pyramid.interfaces import IRequest

from zope import interface

from zope.component.zcml import utility
from zope.component.zcml import adapter

from zope.traversing.interfaces import IPathAdapter

from nti.app.products.google.sso.interfaces import IGoogleLogonSettings

from nti.app.products.google.sso.model import GoogleLogonSettings

from nti.appserver.account_creation_views import DenyAccountCreatePathAdapter
from nti.appserver.account_creation_views import DenyAccountCreatePreflightPathAdapter

from nti.dataserver.interfaces import IDataserverFolder

from nti.schema.field import Bool
from nti.schema.field import ValidTextLine

logger = __import__('logging').getLogger(__name__)


class IRegisterGoogleLogonSettings(interface.Interface):

    disable_account_creation = Bool(title=u'Whether to disable platform account creation',
                                    default=True,
                                    required=False)

    update_user_on_login = Bool(title=u'Whether to update user info on login',
                                default=False,
                                required=False)

    read_only_profile = Bool(title=u'Whether the user profile is read-only',
                             default=False,
                             required=False)

    hosted_domains = ValidTextLine(title=u'Valid hosted domains',
                                   description=u"Comma separated valid host domains",
                                   required=False)


def registerGoogleLogonSettings(_context,
                                disable_account_creation,
                                update_user_on_login,
                                read_only_profile,
                                hosted_domains=None):
    """
    Register google logon settings.
    """
    if hosted_domains:
        hosted_domains = hosted_domains.split(',')
    factory = functools.partial(GoogleLogonSettings,
                                update_user_on_login=update_user_on_login,
                                read_only_profile=read_only_profile,
                                hosted_domains=hosted_domains)
    utility(_context, provides=IGoogleLogonSettings, factory=factory)

    if disable_account_creation:
        for name, factory in (("account.create", DenyAccountCreatePathAdapter),
                              ("account.preflight.create", DenyAccountCreatePreflightPathAdapter)):
            adapter(_context,
                    name=name,
                    for_=(IDataserverFolder, IRequest),
                    factory=(factory,),
                    provides=IPathAdapter)

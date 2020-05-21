#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class,expression-not-assigned

from zope import interface

from zope.interface import Attribute

from zope.interface.interfaces import ObjectEvent
from zope.interface.interfaces import IObjectEvent

from nti.app.products.integration.interfaces import IIntegration

from nti.coremetadata.interfaces import IUser

from nti.schema import Bool
from nti.schema import ValidTextLine


class IGoogleSSOIntegration(IIntegration):
    """
    Google SSO integration
    """


class IGoogleLogonSettings(interface.Interface):
    """
    The settings that define Google SSO behavior. The existence of these
    settings indicates Google SSO is enabled for the current site.
    """

    disable_account_creation = Bool(title=u'Whether to disable platform account creation',
                                    default=True,
                                    required=False)

    lookup_user_by_email = Bool(title=u'Whether to lookup a user by email (vs username)',
                                default=True,
                                required=False)

    update_user_on_login = Bool(title=u'Whether to update user info on login',
                                default=True,
                                required=False)

    read_only_profile = Bool(title=u'Whether the user profile is read-only',
                             default=True,
                             required=False)

    hosted_domain = ValidTextLine(title=u'Valid hosted domain',
                                  description=u"Only allow logins if a user's domain matches",
                                  required=False)


class IGoogleLogonLookupUtility(interface.Interface):
    """
    A utility to handle a user after google authentication.
    """

    def lookup_user(identifier):
        """
        Returns the user, if available from the given identifier.

        :raises: AmbiguousUserLookupError
        """

    def generate_username(identifier):
        """
        Creates a username if the google entity does not exist in our system.
        """


class IGoogleUserCreatedEvent(IObjectEvent):
    """
    Fired after an Google user has been created
    """
    request = Attribute(u"Request")


@interface.implementer(IGoogleUserCreatedEvent)
class GoogleUserCreatedEvent(ObjectEvent):

    def __init__(self, obj, request=None):
        super(GoogleUserCreatedEvent, self).__init__(obj)
        self.request = request


class IGoogleUser(IUser):
    """
    A marker interface for a google user.
    """

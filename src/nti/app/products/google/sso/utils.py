#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id: identity.py 110862 2017-04-18 00:30:43Z carlos.sanchez $
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope.event import notify

from nti.externalization.interfaces import ObjectModifiedFromExternalEvent

from nti.identifiers.interfaces import IUserExternalIdentityContainer

from nti.identifiers.utils import get_user_for_external_id


logger = __import__('logging').getLogger(__name__)

GOOGLE_OAUTH_EXTERNAL_ID_TYPE = u'google.oauth'


def set_user_google_id(user, email):
    """
    Set the given google identity for a user.
    """
    identity_container = IUserExternalIdentityContainer(user)
    identity_container.add_external_mapping(GOOGLE_OAUTH_EXTERNAL_ID_TYPE,
                                            email)
    logger.info("Setting google ID for user (%s) (%s/%s)",
                user.username, GOOGLE_OAUTH_EXTERNAL_ID_TYPE, email)
    notify(ObjectModifiedFromExternalEvent(user))


def get_user_for_google_id(email):
    """
    Find any user associated with the given google email.
    """
    return get_user_for_external_id(GOOGLE_OAUTH_EXTERNAL_ID_TYPE, email)

#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import logging
import requests

from zope import component
from zope import interface

from zope.component.hooks import getSite

from zope.event import notify

from zope.schema import ValidationError

import pyramid.httpexceptions as hexc

import pyramid.interfaces

from pyramid.view import view_config

from nti.app.authentication import user_can_login

from nti.app.externalization.error import validation_error_to_dict

from nti.app.products.google.oauth.views import DEFAULT_TOKEN_URL

from nti.app.products.google.oauth.views import initiate_oauth_flow
from nti.app.products.google.oauth.views import exchange_code_for_token
from nti.app.products.google.oauth.views import redirect_google_oauth2_uri as _redirect_uri

from nti.app.products.google.sso.interfaces import IGoogleUser
from nti.app.products.google.sso.interfaces import IGoogleLogonSettings
from nti.app.products.google.sso.interfaces import GoogleUserCreatedEvent
from nti.app.products.google.sso.interfaces import IGoogleLogonLookupUtility

from nti.app.products.google.sso.utils import set_user_google_id
from nti.app.products.google.sso.utils import get_user_for_google_id

from nti.appserver import MessageFactory as _

from nti.appserver.interfaces import IMissingUser
from nti.appserver.interfaces import ILogonLinkProvider
from nti.appserver.interfaces import IUnauthenticatedUserLinkProvider

from nti.appserver.interfaces import AmbiguousUserLookupError

from nti.appserver.logon import create_success_response
from nti.appserver.logon import create_failure_response
from nti.appserver.logon import deal_with_external_account

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.common.string import is_true

from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver.users.common import user_creation_sitename

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IUIReadOnlyProfileSchema
from nti.dataserver.users.interfaces import IUsernameGeneratorUtility

from nti.dataserver.users.users import User

from nti.dataserver.users.utils import get_users_by_email
from nti.dataserver.users.utils import force_email_verification

from nti.externalization.internalization import update_from_external_object

from nti.links.links import Link

logger = logging.getLogger(__name__)

REL_LOGIN_GOOGLE = 'logon.google'
LOGON_GOOGLE_OAUTH2 = 'logon.google.oauth2'

OPENID_CONFIGURATION = None
DEFAULT_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
DISCOVERY_DOC_URL = 'https://accounts.google.com/.well-known/openid-configuration'


def get_openid_configuration():
    global OPENID_CONFIGURATION
    if not OPENID_CONFIGURATION:
        s = requests.get(DISCOVERY_DOC_URL)
        OPENID_CONFIGURATION = s.json() if s.status_code == 200 else {}
    return OPENID_CONFIGURATION


@interface.implementer(IGoogleLogonLookupUtility)
class GoogleLogonLookupUtility(object):
    """
    The default logon lookup utility that utilizes the external identifier.
    """

    def lookup_user(self, identifier):
        return get_user_for_google_id(identifier)

    def generate_username(self, unused_identifier):
        username_util = component.getUtility(IUsernameGeneratorUtility)
        result = username_util.generate_username()
        return result


@interface.implementer(IGoogleLogonLookupUtility)
class GoogleLogonLookupByEmailUtility(object):
    """
    A logon lookup utility that does so by email. This can lead to ambiguous
    results and should only be used for legacy cases.
    """

    def lookup_user(self, identifier):
        """
        This utility maps the given user identifier as the user's email. We
        Only return users for the given site; thus, a user with accounts in
        multiple sites with the same email should be able to SSO with their
        email address.
        """
        user = None
        # XXX: We could query get_users_by_email_sites once we are ensured
        # all users have a user creation site.
        users = get_users_by_email(identifier)
        users = tuple(users)
        if len(users) > 1:
            # Multiple users; check if one and only one is tied to our current
            # site.
            site_users = []
            current_site_name = getattr(getSite(), '__name__', '')
            for user in users:
                user_site_name = user_creation_sitename(user)
                if user_site_name == current_site_name:
                    site_users.append(user)
            if len(site_users) == 1:
                # Great; we found the *one* user for this site
                users = site_users
            else:
                # We either have no users for this site or more than one; we
                # have to raise.
                logger.warn('Ambiguous users found on google auth (id=%s) (users=%s)',
                            identifier,
                            ', '.join(x.username for x in users))
                raise AmbiguousUserLookupError()

        if users:
            user = users[0]
        return user

    def generate_username(self, unused_identifier):
        username_util = component.getUtility(IUsernameGeneratorUtility)
        result = username_util.generate_username()
        return result


@interface.implementer(IGoogleLogonLookupUtility)
class GoogleLogonLookupByUsernameUtility(object):
    """
    A logon lookup utility that does so matching the email to a username.
    """

    def lookup_user(self, identifier):
        return User.get_user(identifier)

    def generate_username(self, identifier):
        return identifier


def _get_google_hosted_domain():
    """
    This param just optimizes the UI experience. If we have more than
    one hosted domains, verify upon authentication.
    """
    hosted_domain = None
    logon_settings = component.queryUtility(IGoogleLogonSettings)
    if      logon_settings is not None \
        and logon_settings.hosted_domains \
        and len(logon_settings.hosted_domains) == 1:
        hosted_domain = logon_settings.hosted_domains[0]
    return hosted_domain


@view_config(name=REL_LOGIN_GOOGLE,
             route_name='objects.generic.traversal',
             context=IDataserverFolder,
             request_method='GET',
             renderer='rest')
def google_oauth1(request, success=None, failure=None, state=None):
    params = {}
    hosted_domain = _get_google_hosted_domain()
    if hosted_domain:
        params['hd'] = hosted_domain

    return initiate_oauth_flow(request,
                               _redirect_uri(request, LOGON_GOOGLE_OAUTH2),
                               scopes=['openid', 'email', 'profile'],
                               success=success,
                               failure=failure,
                               state=state,
                               params=params)


def _update_profile(request, profile, external_values):
    """
    Try updating the profile, skipping if we encounter any error.
    We could loop and only take acceptable fields...

    XXX: might be generally useful elsewhere
    """
    try:
        update_from_external_object(profile,
                                    external_values)
    except ValidationError as invalid:
        error_dict = validation_error_to_dict(request, invalid)
        logger.warn('At least one ensync IMIS field is invalid (%s) (%s)',
                    external_values, error_dict)


def _can_create_google_oath_user():
    """
    Some sites may not allow google auth account creation.
    """
    policy = component.queryUtility(ISitePolicyUserEventListener)
    return getattr(policy, 'GOOGLE_AUTH_USER_CREATION', True)


@view_config(name=LOGON_GOOGLE_OAUTH2,
             route_name='objects.generic.traversal',
             context=IDataserverFolder,
             request_method='GET',
             renderer='rest')
def google_oauth2(request):
    try:
        config = get_openid_configuration()
        token_url = config.get('token_endpoint', DEFAULT_TOKEN_URL)
        redirect_uri = _redirect_uri(request, LOGON_GOOGLE_OAUTH2)
        data = exchange_code_for_token(request,
                                       token_url=token_url,
                                       redirect_uri=redirect_uri)

        if 'access_token' not in data:
            return create_failure_response(request,
                                           request.session.get('google.failure'),
                                           error=_(u'Could not find access token.'))
        if 'id_token' not in data:
            return create_failure_response(request,
                                           request.session.get('google.failure'),
                                           error=_(u'Could not find id token.'))

        # id_token = data['id_token'] #TODO:Validate id token
        access_token = data['access_token']
        logger.debug("Getting user profile")
        userinfo_url = config.get('userinfo_endpoint', DEFAULT_USERINFO_URL)
        response = requests.get(userinfo_url, params={
                                "access_token": access_token})
        if response.status_code != 200:
            return create_failure_response(request,
                                           request.session.get('google.failure'),
                                           error=_(u'Invalid access token.'))
        profile = response.json()
        response = google_logon_from_user_response(request, profile)
    except hexc.HTTPException:
        logger.exception('Failed to login with google')
        raise
    except Exception as e:
        logger.exception('Failed to login with google')
        response = create_failure_response(request,
                                           request.session.get('google.failure'),
                                           error=str(e))
    return response


def google_logon_from_user_response(request, user_response_dict):
    """
    From a user response dict, handle the account lookup/provisioning/update.
    """
    # Make sure our user is from the correct domain.
    firstName = user_response_dict.get('given_name', 'unspecified')
    lastName = user_response_dict.get('family_name', 'unspecified')
    realname = firstName + ' ' + lastName
    email_verified = user_response_dict.get('email_verified', 'false')
    email = user_response_dict['email']

    logon_settings = component.queryUtility(IGoogleLogonSettings)
    if logon_settings.hosted_domains:
        domain = email.split('@')[1]
        if domain not in logon_settings.hosted_domains:
            return create_failure_response(request,
                                           request.session.get('google.failure'),
                                           error=_(u'Invalid domain.'))
    logon_utility = component.getUtility(IGoogleLogonLookupUtility)
    user = logon_utility.lookup_user(email)
    if user is None:
        if not _can_create_google_oath_user():
            return create_failure_response(request,
                                           error="Cannot create user.")
        username = logon_utility.generate_username(email)

        user = deal_with_external_account(request,
                                          username=username,
                                          fname=firstName,
                                          lname=lastName,
                                          email=email,
                                          idurl=None,
                                          iface=None,
                                          user_factory=User.create_user)
        interface.alsoProvides(user, IGoogleUser)
        set_user_google_id(user, email)

        notify(GoogleUserCreatedEvent(user, request))
        if is_true(email_verified):
            force_email_verification(user)  # trusted source

    user_profile = IUserProfile(user)

    if logon_settings.read_only_profile:
        interface.alsoProvides(user_profile, IUIReadOnlyProfileSchema)

    if logon_settings.update_user_on_login:
        external_values = {u'email': email,
                           u'realname': realname}
        _update_profile(request, user_profile, external_values)

    if not user_can_login(user):
        return create_failure_response(request,
                                       error="User cannot login.")
    request.environ['nti.request_had_transaction_side_effects'] = 'True'
    response = create_success_response(request,
                                       userid=user.username,
                                       success=request.session.get('google.success'))
    return response


@component.adapter(pyramid.interfaces.IRequest)
@interface.implementer(IUnauthenticatedUserLinkProvider)
class SimpleUnauthenticatedUserGoogleLinkProvider(object):

    rel = REL_LOGIN_GOOGLE

    def __init__(self, request):
        self.request = request

    def get_links(self):
        result = ()
        # Only return logon links if we are configured for google SSO.
        logon_settings = component.queryUtility(IGoogleLogonSettings)
        if logon_settings is not None:
            elements = (self.rel,)
            root = self.request.route_path('objects.generic.traversal',
                                           traverse=())
            root = root[:-1] if root.endswith('/') else root
            result = [Link(root, elements=elements, rel=self.rel)]
        return result


@interface.implementer(ILogonLinkProvider)
@component.adapter(IMissingUser, pyramid.interfaces.IRequest)
class SimpleMissingUserGoogleLinkProvider(SimpleUnauthenticatedUserGoogleLinkProvider):

    def __init__(self, user, request):
        super(SimpleMissingUserGoogleLinkProvider, self).__init__(request)
        self.user = user

    def __call__(self):
        links = self.get_links()
        return links[0] if links else None

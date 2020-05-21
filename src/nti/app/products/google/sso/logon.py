#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import logging
import requests

from urlparse import urljoin

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import getSite

from zope.event import notify

from zope.schema import ValidationError

import pyramid.httpexceptions as hexc

import pyramid.interfaces

from pyramid.view import view_config

from nti.app.externalization.error import validation_error_to_dict

from nti.app.products.google.sso.interfaces import IGoogleLogonSettings

from nti.appserver import MessageFactory as _

from nti.appserver.interfaces import IMissingUser
from nti.appserver.interfaces import ILogonLinkProvider
from nti.appserver.interfaces import IGoogleLogonLookupUtility
from nti.appserver.interfaces import IUnauthenticatedUserLinkProvider

from nti.appserver.interfaces import AmbiguousUserLookupError

from nti.appserver.logon import create_success_response
from nti.appserver.logon import create_failure_response
from nti.appserver.logon import deal_with_external_account

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.common.string import is_true

from nti.common.interfaces import IOAuthKeys
from nti.common.interfaces import IOAuthService

from nti.dataserver.interfaces import IGoogleUser
from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver.users.common import user_creation_sitename

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import GoogleUserCreatedEvent
from nti.dataserver.users.interfaces import IUIReadOnlyProfileSchema
from nti.dataserver.users.interfaces import IUsernameGeneratorUtility

from nti.dataserver.users.users import User

from nti.dataserver.users.utils import get_users_by_email
from nti.dataserver.users.utils import force_email_verification

from nti.externalization.interfaces import ObjectModifiedFromExternalEvent

from nti.externalization.internalization import update_from_external_object

from nti.identifiers.interfaces import IUserExternalIdentityContainer

from nti.links.links import Link

logger = logging.getLogger(__name__)

REL_LOGIN_GOOGLE = 'logon.google'

OPENID_CONFIGURATION = None
LOGON_GOOGLE_OAUTH2 = 'logon.google.oauth2'
DEFAULT_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
DEFAULT_TOKEN_URL = 'https://www.googleapis.com/oauth2/v4/token'
DEFAULT_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
DISCOVERY_DOC_URL = 'https://accounts.google.com/.well-known/openid-configuration'

GOOGLE_OAUTH_EXTERNAL_ID_TYPE = u'google.oauth'


def redirect_google_oauth2_uri(request):
    root = request.route_path('objects.generic.traversal', traverse=())
    root = root[:-1] if root.endswith('/') else root
    target = urljoin(request.application_url, root)
    target = target + '/' if not target.endswith('/') else target
    target = urljoin(target, LOGON_GOOGLE_OAUTH2)
    return target


_redirect_uri = redirect_google_oauth2_uri


def get_openid_configuration():
    global OPENID_CONFIGURATION
    if not OPENID_CONFIGURATION:
        s = requests.get(DISCOVERY_DOC_URL)
        OPENID_CONFIGURATION = s.json() if s.status_code == 200 else {}
    return OPENID_CONFIGURATION


@interface.implementer(IGoogleLogonLookupUtility)
class GoogleLogonLookupUtility(object):

    @Lazy
    def username_is_email(self):
        """
        Do we lookup user by email? The alternative is when
        the username is the email addr.
        """
        logon_settings = component.getUtility(IGoogleLogonSettings)
        return not logon_settings.lookup_user_by_email

    def lookup_user_by_email(self, identifier):
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

    def lookup_user(self, identifier):
        if self.username_is_email:
            result = User.get_user(identifier)
        else:
            result = self.lookup_user_by_email(identifier)
            # When a user login a child site, then login its parent or sibling site with the same GMail,
            # it would create duplicated users with the same GMail, which may cause a different user returned
            # when login the child site with that gmail.
            # fix get_user_for_external_id?
            #user = get_user_for_external_id(GOOGLE_OAUTH_EXTERNAL_ID_TYPE, identifier)
        return result

    def generate_username(self, identifier):
        if self.username_is_email:
            result = identifier
        else:
            username_util = component.getUtility(IUsernameGeneratorUtility)
            result = username_util.generate_username()
        return result


def _get_google_hosted_domain():
    hosted_domain = None
    login_config = component.queryUtility(IGoogleLogonSettings)
    if login_config is not None:
        hosted_domain = login_config.hd
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

    for key, value in (('success', success), ('failure', failure)):
        value = value or request.params.get(key)
        if value:
            request.session['google.' + key] = value

    # redirect
    auth_svc = component.getUtility(IOAuthService, name="google")
    target = auth_svc.authorization_request_uri(
        client_id=component.getUtility(IOAuthKeys, name="google").APIKey,
        response_type='code',
        scope='openid email profile',
        redirect_uri=_redirect_uri(request),
        state=state,
        **params
    )

    # save state for validation
    request.session['google.state'] = auth_svc.params['state']

    response = hexc.HTTPSeeOther(location=target)
    return response


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
    params = request.params
    auth_keys = component.getUtility(IOAuthKeys, name="google")

    # check for errors
    if 'error' in params or 'errorCode' in params:
        error = params.get('error') or params.get('errorCode')
        return create_failure_response(request,
                                        request.session.get('google.failure'),
                                        error=error)

    # Confirm code
    if 'code' not in params:
        return create_failure_response(request,
                                        request.session.get('google.failure'),
                                        error=_(u'Could not find code parameter.'))
    code = params.get('code')

    # Confirm anti-forgery state token
    if 'state' not in params:
        return create_failure_response(request,
                                        request.session.get('google.failure'),
                                        error=_(u'Could not find state parameter.'))
    params_state = params.get('state')
    session_state = request.session.get('google.state')
    if params_state != session_state:
        return create_failure_response(request,
                                        request.session.get('google.failure'),
                                        error=_(u'Incorrect state values.'))

    # Exchange code for access token and ID token
    config = get_openid_configuration()
    token_url = config.get('token_endpoint', DEFAULT_TOKEN_URL)

    try:
        # Check for redirect url override (e.g. via the OAuth portal)
        redirect_uri = params.get('_redirect_uri')

        data = {'code': code,
                'client_id': auth_keys.APIKey,
                'grant_type': 'authorization_code',
                'client_secret': auth_keys.SecretKey,
                'redirect_uri': redirect_uri or _redirect_uri(request)}
        response = requests.post(token_url, data)
        if response.status_code != 200:
            return create_failure_response(
                request,
                request.session.get('google.failure'),
                error=_('Invalid response while getting access token.'))

        data = response.json()
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
        response = _google_logon_from_user_response(profile)
    except Exception as e:
        logger.exception('Failed to login with google')
        response = create_failure_response(request,
                                            request.session.get('google.failure'),
                                            error=str(e))
    return response


def _google_logon_from_user_response(request, user_response_dict):
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
    if logon_settings.hosted_domain:
        domain = email.split('@')[1]
        if logon_settings.hosted_domain != domain:
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
        # add external_type / external_id
        id_container = IUserExternalIdentityContainer(user)
        id_container.add_external_mapping(GOOGLE_OAUTH_EXTERNAL_ID_TYPE,
                                          email)
        logger.info("Setting Google OAUTH for user (%s) (%s)",
                    user.username, email)
        notify(ObjectModifiedFromExternalEvent(user))

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
        # Only return logon links if we are configured for google SSO.
        logon_settings = component.queryUtility(IGoogleLogonSettings)
        if logon_settings is not None:
            elements = (self.rel,)
            root = self.request.route_path('objects.generic.traversal',
                                           traverse=())
            root = root[:-1] if root.endswith('/') else root
            return [Link(root, elements=elements, rel=self.rel)]


@interface.implementer(ILogonLinkProvider)
@component.adapter(IMissingUser, pyramid.interfaces.IRequest)
class SimpleMissingUserGoogleLinkProvider(SimpleUnauthenticatedUserGoogleLinkProvider):

    def __init__(self, user, request):
        super(SimpleMissingUserGoogleLinkProvider, self).__init__(request)
        self.user = user

    def __call__(self):
        links = self.get_links()
        return links[0] if links else None

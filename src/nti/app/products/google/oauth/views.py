#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

import pyramid.httpexceptions as hexc

from pyramid.view import view_config

import requests

from zope import component

from nti.common.interfaces import IOAuthKeys
from nti.common.interfaces import IOAuthService

from nti.app.products.google import MessageFactory as _

from nti.app.products.google.oauth import OAuthError
from nti.app.products.google.oauth import OAuthInvalidRequest

from nti.dataserver.interfaces import IDataserverFolder


import logging
logger = logging.getLogger(__name__)

DEFAULT_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
DEFAULT_TOKEN_URL = 'https://www.googleapis.com/oauth2/v4/token'

def initiate_oauth_flow(request, redirect_uri, scopes=[], success=None, failure=None, state=None, params={}):
    """
    Given a request and a redirect uri, initiate the oauth2 flow.

    TODO: This looks very close to be suitable for a general oauth2 authorization request
    """

    # We probably don't need to further scope these session keys, but
    # there is a clear sequencing issue of if oauth requests from the
    # same session are interleaved.
    
    for key, value in (('success', success), ('failure', failure)):
        value = value or request.params.get(key)
        if value:
            request.session['google.' + key] = value

    # redirect
    auth_svc = component.getUtility(IOAuthService, name="google")
    target = auth_svc.authorization_request_uri(
        client_id=component.getUtility(IOAuthKeys, name="google").APIKey,
        response_type='code',
        scope=' '.join(scopes),
        redirect_uri=redirect_uri,
        state=state,
        **params
    )

    # save state for validation
    request.session['google.state'] = auth_svc.params['state']

    response = hexc.HTTPSeeOther(location=target)
    return response


def exchange_code_for_token(request, token_url=DEFAULT_TOKEN_URL):
    """
    Given a request from the second portion of the oauth flow
    exchange the code for an access token. Returns the oauth token data
    or raises an exception if the request is invalid.

    TODO: Again this is pretty close to being general for any oauth provider
    """

    params = request.params
    auth_keys = component.getUtility(IOAuthKeys, name="google")

    # check for errors
    if 'error' in params or 'errorCode' in params:
        error = params.get('error') or params.get('errorCode')
        raise OAuthError(error)

    # Confirm code
    if 'code' not in params:
        raise OAuthInvalidRequest(_(u'Could not find code parameter.'))
    
    code = params.get('code')

    # Confirm anti-forgery state token
    if 'state' not in params:
        raise OAuthInvalidRequest(_(u'Could not find state parameter.'))
    
    params_state = params.get('state')
    session_state = request.session.get('google.state')
    if params_state != session_state:
        raise OAuthInvalidRequest(_(u'Incorrect state values.'))

    # Exchange code for access token and ID token
    # Check for redirect url override (e.g. via the OAuth portal)
    redirect_uri = params.get('_redirect_uri')

    data = {'code': code,
            'client_id': auth_keys.APIKey,
            'grant_type': 'authorization_code',
            'client_secret': auth_keys.SecretKey,
            'redirect_uri': redirect_uri or _redirect_uri(request)}
    response = requests.post(token_url, data)
    if response.status_code != 200:
        raise OAuthError(_('Invalid response while getting access token.'))

    return response.json()

@view_config(name='google.oauth.authorize',
             route_name='objects.generic.traversal',
             context=IDataserverFolder,
             request_method='GET',
             renderer='rest')
def google_oauth_authorize(request):
    """
    The first step in the oauth flow to obtain an authorization_token
    from the user. The intent of this view is for use by clients with things
    like the js FilePicker API. The client provides this view with a set of scopes. We
    can't use https://developers.google.com/identity/protocols/oauth2/javascript-implicit-flow
    because that doesn't account for our need to bounce through the oauth portal. The process
    is the same as documented there. Start the process and return the token via fragment on the return url.
    """
    params = request.params
    scopes = [s for s in params.get('scope').split(' ') if s]
    return initiate_oauth_flow(request,
                               request.resource_url(request.context)+'@@google.oauth.authorize2',
                               success=params.get('success'),
                               failure=params.get('failure'),
                               scopes=scopes,
                               state=params.get('state', None))


_FORWARDED_TOKEN_DATA = ('access_token', 'token_type', 'expires_in')

def _oauth_authorize_return(url, data):
    return '%s#%s' % (url, urlencode(data)) if data else url

@view_config(name='google.oauth.authorize2',
             route_name='objects.generic.traversal',
             context=IDataserverFolder,
             request_method='GET',
             renderer='rest')
def google_oauth2(request):
    try:
        data = exchange_code_for_token(request)

        if 'access_token' not in data:
            return  hexc.HTTPSeeOther(_oauth_authorize_return(request.session.get('google.failure'),
                                                             {'error': _(u'Could not find access token.')}))

        # Like https://developers.google.com/identity/protocols/oauth2/javascript-implicit-flow#oauth-2.0-endpoints_4
        # we pass the token (or error) back in a fragment string.
        data = {k:v for k,v in data.iteritems() if k in _FORWARDED_TOKEN_DATA}
        response = hexc.HTTPSeeOther(_oauth_authorize_return(request.session.get('google.success'),
                                                             data))
    except hexc.HTTPException:
        logger.exception('Failed to authorize with google')
        raise
    except Exception as e:
        logger.exception('Failed to authorize with google')
        response = hexc.HTTPSeeOther(_oauth_authorize_return(request.session.get('google.failure'),
                                                             {'error': str(e)}))
    return response

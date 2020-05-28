#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from hamcrest import is_
from hamcrest import is_not
from hamcrest import not_none
from hamcrest import assert_that

import pyramid.interfaces
import pyramid.httpexceptions as hexc

from zope import component
from zope import interface

from nti.app.products.google.sso.interfaces import IGoogleLogonSettings

from nti.app.products.google.sso.logon import google_logon_from_user_response

from nti.app.products.google.sso.model import GoogleLogonSettings

from nti.app.products.google.sso.views import GOOGLE_LOGON_SETTINGS_NAME

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.users import User

from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.dataserver.tests import mock_dataserver

from nti.site.localutility import install_utility


class TestGoogleSSO(ApplicationLayerTest):

    @WithSharedApplicationMockDS
    def test_google_sso(self):
        logon_settings = GoogleLogonSettings(hosted_domains=[],
                                             read_only_profile=False,
                                             update_user_on_login=False)
        logon_settings.__name__ = GOOGLE_LOGON_SETTINGS_NAME
        request = self.request

        class Policy(object):
            interface.implements(pyramid.interfaces.IAuthenticationPolicy)
            def remember(self, request, who):
                return [("Policy", who)]
            def authenticated_userid(self, request):
                return 'google_sso_userid'
            def effective_principals(self, request):
                return [self.authenticated_userid(request)]
            def forget(self, *args, **kwargs):
                pass

        user_response_dict = {u'given_name': u'user_first_name',
                              u'family_name': u'user_last_name',
                              u'email': u'user_email@ssodomain.com'}
        with mock_dataserver.mock_db_trans(self.ds):
            install_utility(logon_settings,
                            utility_name=logon_settings.__name__,
                            provided=IGoogleLogonSettings,
                            local_site_manager=component.getSiteManager())
            request.environ['HTTP_HOST'] = 'mathcounts.nextthought.com'
            request.environ['HTTP_ORIGIN'] = 'https://mathcounts.nextthought.com'
            request.registry.registerUtility(Policy())

            res = google_logon_from_user_response(request, user_response_dict)
            assert_that(res, is_(hexc.HTTPNoContent))
            new_username = res.headers.get('Policy')
            assert_that(new_username, not_none())

            # Second call matches first is not updated
            user_response_dict[u'given_name'] = u'newfirst'
            user_response_dict[u'family_name'] = u'newlast'
            res = google_logon_from_user_response(request, user_response_dict)
            assert_that(res, is_(hexc.HTTPNoContent))
            assert_that(res.headers.get('Policy'), is_(new_username))
            user = User.get_user(new_username)
            assert_that(user, not_none())
            friendly_named = IFriendlyNamed(user)
            assert_that(friendly_named.realname, is_(u'User_first_name User_last_name'))

            # Updating user
            logon_settings.read_only_profile = True
            logon_settings.update_user_on_login = True

            res = google_logon_from_user_response(request, user_response_dict)
            user = User.get_user(new_username)
            friendly_named = IFriendlyNamed(user)
            assert_that(friendly_named.realname, is_(u'newfirst newlast'))

            # Domain restrictions, user can no longer log in
            logon_settings.hosted_domains = [u'validdomain.com', u'validdomain2.com']
            res = google_logon_from_user_response(request, user_response_dict)
            assert_that(res.status_code, is_(401))
            assert_that(res.headers.get('Warning'), is_('Invalid domain.'))

            user_response_dict[u'email'] = u'user_email@validdomain.com'
            res = google_logon_from_user_response(request, user_response_dict)
            new_username2 = res.headers.get('Policy')
            assert_that(new_username2, is_not(new_username))

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import contains_inanyorder

from zope.component.hooks import getSite

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from nti.app.testing.webtest import TestApp

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.authorization import ROLE_ADMIN
from nti.dataserver.authorization import ROLE_SITE_ADMIN

from nti.dataserver.tests import mock_dataserver


class TestIntegration(ApplicationLayerTest):

    default_origin = 'http://mathcounts.nextthought.com'

    def _assign_role_for_site(self, role, username, site=None):
        role_manager = IPrincipalRoleManager(site or getSite())
        role_name = getattr(role, "id", role)
        role_manager.assignRoleToPrincipal(role_name, username)

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_integration(self):
        admin_username = 'google_int@nextthought.com'
        site_admin_username = 'google_sso_site_admin'
        with mock_dataserver.mock_db_trans(self.ds):
            self._create_user(admin_username)
            self._assign_role_for_site(ROLE_ADMIN, admin_username)
            self._create_user(site_admin_username)
        with mock_dataserver.mock_db_trans(self.ds, site_name="mathcounts.nextthought.com"):
            self._assign_role_for_site(ROLE_SITE_ADMIN, site_admin_username)

        admin_env = self._make_extra_environ(admin_username)
        site_admin_env = self._make_extra_environ(site_admin_username)
        def _get_google_int(username, env):
            url = "/dataserver2/users/%s/Integration/Integrations" % username
            res = self.testapp.get(url, extra_environ=env)
            res = res.json_body
            google_int = next((x for x in res['Items'] if x.get('Class') == 'GoogleSSOIntegration'), None)
            return google_int

        assert_that(_get_google_int(site_admin_username, site_admin_env), not_none())
        google_int = _get_google_int(admin_username, admin_env)
        assert_that(google_int, not_none())
        enable_href = self.require_link_href_with_rel(google_int, 'enable')

        # Enable integration
        logon_settings = self.testapp.post(enable_href,
                                           extra_environ=admin_env)
        logon_settings = logon_settings.json_body
        self.require_link_href_with_rel(logon_settings, 'delete')
        edit_rel = self.require_link_href_with_rel(logon_settings, 'edit')
        assert_that(logon_settings, has_entries(u"Class", u'PersistentGoogleLogonSettings',
                                                u'Last Modified', not_none(),
                                                u'Creator', admin_username,
                                                u'NTIID', not_none(),
                                                u'MimeType', u'application/vnd.nextthought.site.persistentgooglelogonsettings',
                                                u'href', not_none(),
                                                u'hosted_domains', none(),
                                                u'read_only_profile', False,
                                                u"update_user_on_login", False,
                                                u'CreatedTime', not_none()))
        settings_ntiid = logon_settings.get('NTIID')
        settings_href = logon_settings.get('href')
        # Persisted
        logon_settings = self.testapp.get(settings_href,
                                          extra_environ=admin_env)
        assert_that(logon_settings.json_body['NTIID'], is_(settings_ntiid))

        # Cannot enable if already enabled
        self.testapp.post(enable_href, extra_environ=admin_env, status=422)

        # Edit
        data = {"hosted_domains": ["nextthought.com", "another_domain"],
                "update_user_on_login": True,
                "read_only_profile": True}
        res = self.testapp.put_json(edit_rel, data, extra_environ=admin_env)
        logon_settings = res.json_body
        assert_that(logon_settings, has_entries(u'hosted_domains', contains_inanyorder("nextthought.com", "another_domain"),
                                                u'read_only_profile', True,
                                                u"update_user_on_login", True))

        unauth_testapp = TestApp(self.app)
        res = unauth_testapp.get('/dataserver2/logon.ping',
                                 extra_environ={'HTTP_ORIGIN': self.default_origin})
        self.require_link_href_with_rel(res.json_body, u'logon.google')
#         assert_that( res.json_body, has_key( 'Links' ) )
#
#         link_rels = [l['rel'] for l in res.json_body['Links']]
#         assert_that( link_rels, has_item( 'account.create' ) )
#         assert_that( link_rels, has_item( 'account.preflight.create' ) )
        # TODO
        # site admin should not have rels
        # disabling
        # logging in - fudging
        # account creation

        # Disabling
        google_int = _get_google_int(admin_username, admin_env)
        assert_that(google_int, not_none())
        disable_href = self.require_link_href_with_rel(google_int, 'disable')
        self.testapp.delete(disable_href, extra_environ=admin_env)
        self.testapp.get(settings_href, extra_environ=admin_env, status=404)


#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,no-member

from hamcrest import is_
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

from zope import component

from nti.app.products.salesforce.interfaces import ISalesforceLogonSettings

from nti.app.products.salesforce.logon import SimpleMissingUserSalesforceLinkProvider
from nti.app.products.salesforce.logon import SimpleUnauthenticatedUserSalesforceLinkProvider

from nti.app.testing.request_response import DummyRequest

from nti.appserver.interfaces import ILogonLinkProvider
from nti.appserver.interfaces import IUnauthenticatedUserLinkProvider

from nti.dataserver.users.missing_user import MissingUser

import nti.testing.base

ZCML_STRING = """
<configure  xmlns="http://namespaces.zope.org/zope"
            xmlns:i18n="http://namespaces.zope.org/i18n"
            xmlns:zcml="http://namespaces.zope.org/zcml"
            xmlns:salesforce="http://nextthought.com/ntp/salesforce">

    <include package="zope.component" file="meta.zcml" />
    <include package="zope.security" file="meta.zcml" />
    <include package="zope.component" />
    <include package="." file="meta.zcml" />

    <configure>
        <salesforce:registerSalesforceLogonSettings client_id="abcde"
                                                    client_secret="fwJJRWVZAURWWUUQ"
                                                    login_url="https://login.salesforce.com/services/oauth2/authorize"
                                                    token_url="https://login.salesforce.com/services/oauth2/token"
                                                    user_info_url="https://login.salesforce.com/services/oauth2/userinfo"
                                                    app_title="salesforce app"
                                                    logon_link_title="logon link title"
                                                    disable_account_creation="true" />
    </configure>
</configure>
"""


class TestZcml(nti.testing.base.ConfiguringTestBase):

    def test_registration(self):
        self.configure_string(ZCML_STRING)
        logon_settings = component.queryUtility(ISalesforceLogonSettings)
        assert_that(logon_settings, not_none())
        assert_that(logon_settings,
                    has_property('client_id', is_("abcde")))
        assert_that(logon_settings,
                    has_property('client_secret', is_("111111111111")))
        assert_that(logon_settings,
                    has_property('app_title', is_("salesforce app")))
        assert_that(logon_settings,
                    has_property('logon_link_title', is_("logon link title")))
        assert_that(logon_settings,
                    has_property('login_url', is_("https://login.salesforce.com/services/oauth2/authorize")))
        assert_that(logon_settings,
                    has_property('token_url', is_("https://login.salesforce.com/services/oauth2/token")))
        assert_that(logon_settings,
                    has_property('user_info_url', is_("https://login.salesforce.com/services/oauth2/userinfo")))

        request = DummyRequest()
        missing_user = MissingUser('test')
        link_providers = component.subscribers((request,),
                                               IUnauthenticatedUserLinkProvider)
        salesforce_links = [x for x in link_providers if isinstance(x, SimpleUnauthenticatedUserSalesforceLinkProvider)]
        assert_that(salesforce_links, has_length(1))
        assert_that(salesforce_links[0].title, is_("logon link title"))

        link_providers = component.subscribers((missing_user, request), ILogonLinkProvider)
        salesforce_links = [x for x in link_providers if isinstance(x, SimpleMissingUserSalesforceLinkProvider)]
        assert_that(salesforce_links, has_length(1))
        assert_that(salesforce_links[0].title, is_("logon link title"))

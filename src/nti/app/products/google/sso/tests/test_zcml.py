#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,no-member

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import contains_inanyorder

from zope import component

from nti.app.products.google.sso.interfaces import IGoogleLogonSettings

from nti.app.products.google.sso.logon import SimpleMissingUserGoogleLinkProvider
from nti.app.products.google.sso.logon import SimpleUnauthenticatedUserGoogleLinkProvider

from nti.app.testing.request_response import DummyRequest

from nti.appserver.interfaces import ILogonLinkProvider
from nti.appserver.interfaces import IUnauthenticatedUserLinkProvider

from nti.dataserver.users.missing_user import MissingUser

import nti.testing.base

ZCML_STRING = """
<configure  xmlns="http://namespaces.zope.org/zope"
            xmlns:i18n="http://namespaces.zope.org/i18n"
            xmlns:zcml="http://namespaces.zope.org/zcml"
            xmlns:salesforce="http://nextthought.com/ntp/google">

    <include package="zope.component" file="meta.zcml" />
    <include package="zope.security" file="meta.zcml" />
    <include package="zope.component" />
    <include package="." file="meta.zcml" />

    <configure>
        <google:registerGoogleLogonSettings disable_account_creation="true",
                                            lookup_user_by_email="true"
                                            update_user_on_login="true"
                                            read_only_profile="true" />
    </configure>
</configure>
"""


ZCML_STRING_DOMAINS = """
<configure  xmlns="http://namespaces.zope.org/zope"
            xmlns:i18n="http://namespaces.zope.org/i18n"
            xmlns:zcml="http://namespaces.zope.org/zcml"
            xmlns:salesforce="http://nextthought.com/ntp/google">

    <include package="zope.component" file="meta.zcml" />
    <include package="zope.security" file="meta.zcml" />
    <include package="zope.component" />
    <include package="." file="meta.zcml" />

    <configure>
        <google:registerGoogleLogonSettings disable_account_creation="false",
                                            lookup_user_by_email="false"
                                            update_user_on_login="false"
                                            read_only_profile="false"
                                            hosted_domains=["nextthought.com","testdomain.com"] />
    </configure>
</configure>
"""


class TestZcml(nti.testing.base.ConfiguringTestBase):

    def test_registration(self):
        self.configure_string(ZCML_STRING)
        logon_settings = component.queryUtility(IGoogleLogonSettings)
        assert_that(logon_settings, not_none())
        assert_that(logon_settings,
                    has_property('lookup_user_by_email', is_(True)))
        assert_that(logon_settings,
                    has_property('update_user_on_login', is_(True)))
        assert_that(logon_settings,
                    has_property('read_only_profile', is_(True)))
        assert_that(logon_settings,
                    has_property('hosted_domains', none()))

        request = DummyRequest()
        missing_user = MissingUser('test')
        link_providers = component.subscribers((request,),
                                               IUnauthenticatedUserLinkProvider)
        salesforce_links = [x for x in link_providers if isinstance(x, SimpleUnauthenticatedUserGoogleLinkProvider)]
        assert_that(salesforce_links, has_length(1))
        assert_that(salesforce_links[0].title, is_("logon link title"))

        link_providers = component.subscribers((missing_user, request), ILogonLinkProvider)
        salesforce_links = [x for x in link_providers if isinstance(x, SimpleMissingUserGoogleLinkProvider)]
        assert_that(salesforce_links, has_length(1))
        assert_that(salesforce_links[0].title, is_("logon link title"))

        self.configure_string(ZCML_STRING_DOMAINS)
        logon_settings = component.queryUtility(IGoogleLogonSettings)
        assert_that(logon_settings, not_none())
        assert_that(logon_settings,
                    has_property('lookup_user_by_email', is_(True)))
        assert_that(logon_settings,
                    has_property('update_user_on_login', is_(True)))
        assert_that(logon_settings,
                    has_property('read_only_profile', is_(True)))
        assert_that(logon_settings,
                    has_property('hosted_domains',
                                 contains_inanyorder("nextthought.com", "testdomain.com")))

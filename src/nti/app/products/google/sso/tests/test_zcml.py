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
from zope import interface

from zope.site.folder import Folder

from zope.traversing.interfaces import IPathAdapter

from nti.app.products.google.sso.interfaces import IGoogleLogonSettings

from nti.app.products.google.sso.logon import SimpleMissingUserGoogleLinkProvider
from nti.app.products.google.sso.logon import SimpleUnauthenticatedUserGoogleLinkProvider

from nti.app.testing.request_response import DummyRequest

from nti.appserver.account_creation_views import DenyAccountCreatePathAdapter
from nti.appserver.account_creation_views import DenyAccountCreatePreflightPathAdapter

from nti.appserver.interfaces import ILogonLinkProvider
from nti.appserver.interfaces import IUnauthenticatedUserLinkProvider

from nti.appserver.logon import NoSuchUser

from nti.dataserver.interfaces import IDataserverFolder

import nti.testing.base


ZCML_STRING = """
<configure  xmlns="http://namespaces.zope.org/zope"
            xmlns:i18n="http://namespaces.zope.org/i18n"
            xmlns:zcml="http://namespaces.zope.org/zcml"
            xmlns:google="http://nextthought.com/ntp/google">

    <include package="zope.component" file="meta.zcml" />
    <include package="zope.security" file="meta.zcml" />
    <include package="zope.component" />
    <include package="." file="meta.zcml" />

    <configure>
        <google:registerGoogleLogonSettings disable_account_creation="true"
                                            update_user_on_login="true"
                                            read_only_profile="true" />

        <subscriber factory="nti.app.products.google.sso.logon.SimpleMissingUserGoogleLinkProvider"
                    provides="nti.appserver.interfaces.ILogonLinkProvider" />

        <subscriber factory="nti.app.products.google.sso.logon.SimpleUnauthenticatedUserGoogleLinkProvider"
                    provides="nti.appserver.interfaces.IUnauthenticatedUserLinkProvider" />
    </configure>
</configure>
"""


ZCML_STRING_DOMAINS = """
<configure  xmlns="http://namespaces.zope.org/zope"
            xmlns:i18n="http://namespaces.zope.org/i18n"
            xmlns:zcml="http://namespaces.zope.org/zcml"
            xmlns:google="http://nextthought.com/ntp/google">

    <include package="zope.component" file="meta.zcml" />
    <include package="zope.security" file="meta.zcml" />
    <include package="zope.component" />
    <include package="." file="meta.zcml" />

    <configure>
        <google:registerGoogleLogonSettings disable_account_creation="false"
                                            update_user_on_login="false"
                                            read_only_profile="false"
                                            hosted_domains="nextthought.com,testdomain.com" />

        <subscriber factory="nti.app.products.google.sso.logon.SimpleMissingUserGoogleLinkProvider"
                    provides="nti.appserver.interfaces.ILogonLinkProvider" />

        <subscriber factory="nti.app.products.google.sso.logon.SimpleUnauthenticatedUserGoogleLinkProvider"
                    provides="nti.appserver.interfaces.IUnauthenticatedUserLinkProvider" />
    </configure>
</configure>
"""


class TestZcml(nti.testing.base.ConfiguringTestBase):

    def test_settings(self):
        self.configure_string(ZCML_STRING)
        logon_settings = component.queryUtility(IGoogleLogonSettings)
        assert_that(logon_settings, not_none())
        assert_that(logon_settings,
                    has_property('update_user_on_login', is_(True)))
        assert_that(logon_settings,
                    has_property('read_only_profile', is_(True)))
        assert_that(logon_settings,
                    has_property('hosted_domains', none()))

        request = DummyRequest()
        ds_folder = Folder()
        interface.alsoProvides(ds_folder, IDataserverFolder)

        path_adapter = component.queryMultiAdapter((ds_folder, request),
                                                   IPathAdapter,
                                                   name='account.create')
        assert_that(isinstance(path_adapter, DenyAccountCreatePathAdapter),
                    is_(True))

        path_adapter = component.queryMultiAdapter((ds_folder, request),
                                                   IPathAdapter,
                                                   name='account.preflight.create')
        assert_that(isinstance(path_adapter, DenyAccountCreatePreflightPathAdapter),
                    is_(True))

        missing_user = NoSuchUser('test')
        link_providers = component.subscribers((request,),
                                               IUnauthenticatedUserLinkProvider)
        user_links = [x for x in link_providers if isinstance(x, SimpleUnauthenticatedUserGoogleLinkProvider)]
        assert_that(user_links, has_length(1))

        link_providers = component.subscribers((missing_user, request),
                                               ILogonLinkProvider)
        user_links = [x for x in link_providers
                      if isinstance(x, SimpleMissingUserGoogleLinkProvider)]
        assert_that(user_links, has_length(1))

    def test_settings_with_domains(self):
        """
        Second pass, with domains and with account creation enabled
        """
        self.configure_string(ZCML_STRING_DOMAINS)
        logon_settings = component.queryUtility(IGoogleLogonSettings)
        assert_that(logon_settings, not_none())
        assert_that(logon_settings,
                    has_property('update_user_on_login', is_(False)))
        assert_that(logon_settings,
                    has_property('read_only_profile', is_(False)))
        assert_that(logon_settings,
                    has_property('hosted_domains',
                                 contains_inanyorder("nextthought.com", "testdomain.com")))

        request = DummyRequest()
        ds_folder = Folder()
        interface.alsoProvides(ds_folder, IDataserverFolder)
        path_adapter = component.queryMultiAdapter((ds_folder, request),
                                                   IPathAdapter,
                                                   name='account.create')
        assert_that(isinstance(path_adapter, DenyAccountCreatePathAdapter),
                    is_(False))

        path_adapter = component.queryMultiAdapter((ds_folder, request),
                                                   IPathAdapter,
                                                   name='account.preflight.create')
        assert_that(isinstance(path_adapter, DenyAccountCreatePreflightPathAdapter),
                    is_(False))

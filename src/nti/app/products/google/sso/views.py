#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from zope import component

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import getSite

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.products.google.sso.interfaces import IGoogleLogonSettings
from nti.app.products.google.sso.interfaces import IPersistentGoogleLogonSettings

from nti.appserver.ugd_edit_views import UGDPutView

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IDataserverFolder

from nti.externalization.interfaces import StandardExternalFields

from nti.site import unregisterUtility

from nti.site.localutility import install_utility

logger = __import__('logging').getLogger(__name__)

MIMETYPE = StandardExternalFields.MIMETYPE

GOOGLE_LOGON_LOOKUP_NAME = u'GoogleLogonLookupUtility'
GOOGLE_LOGON_SETTINGS_NAME = u'GoogleLogonSettings'


def raise_error(data, tb=None,
                factory=hexc.HTTPUnprocessableEntity,
                request=None):
    raise_json_error(request, factory, data, tb)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IDataserverFolder,
             request_method='POST',
             name="enable_google_logon",
             permission=nauth.ACT_NTI_ADMIN)
class CreateGoogleLogonSettingsView(AbstractAuthenticatedView,
                                    ModeledContentUploadRequestUtilsMixin):
    """
    Enable logon settings.

    How should this work with child sites? Should it always be only enabled
    for a current site.
    """

    DEFAULT_FACTORY_MIMETYPE = "application/vnd.nextthought.site.persistentgooglelogonsettings"

    def readInput(self, value=None):
        if self.request.body:
            values = super(CreateGoogleLogonSettingsView, self).readInput(value)
        else:
            values = self.request.params
        values = dict(values)
        # Can't be CaseInsensitive with internalization
        if MIMETYPE not in values:
            values[MIMETYPE] = self.DEFAULT_FACTORY_MIMETYPE
        return values

    @Lazy
    def site(self):
        return getSite()

    @Lazy
    def site_manager(self):
        return self.site.getSiteManager()

    def _register_settings_utility(self, obj):
        obj.__name__ = GOOGLE_LOGON_SETTINGS_NAME
        install_utility(obj,
                        utility_name=obj.__name__,
                        provided=IGoogleLogonSettings,
                        local_site_manager=self.site_manager)
        return obj

    def _do_call(self):
        logger.info("Enabling google oauth logon for site (%s) (%s)",
                    self.site.__name__, self.remoteUser)
        if component.queryUtility(IGoogleLogonSettings):
            raise_error({'message': _(u"Google logon settings already exist"),
                         'code': 'ExistingGoogleLogonSettingsError'})
        logon_settings = self.readCreateUpdateContentObject(self.remoteUser)
        self._register_settings_utility(logon_settings)
        return logon_settings


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IPersistentGoogleLogonSettings,
             request_method='DELETE',
             permission=nauth.ACT_NTI_ADMIN)
class DeleteGoogleLogonSettingsView(AbstractAuthenticatedView):

    def __call__(self):
        logger.info("Disabling google oauth logon for site (%s) (%s)",
                    self.site.__name__, self.remoteUser)
                # Can only unregister in current site
        obj = self._get_local_utility(IGoogleLogonSettings)
        if obj is not None:
            del self.site_manager[obj.__name__]
            unregisterUtility(self.site_manager, obj, IGoogleLogonSettings)
        else:
            # This is also obj != self.context
            raise_error({'message': _(u"Can only delete logon settings in actual site"),
                         'code': 'GoogleLogonSettingsDeleteError'})
        return hexc.HTTPNoContent()


@view_config(route_name='objects.generic.traversal',
             context=IPersistentGoogleLogonSettings,
             request_method='PUT',
             permission=nauth.ACT_NTI_ADMIN,
             renderer='rest')
class GoogleLogonSettingsPutView(UGDPutView):
    pass


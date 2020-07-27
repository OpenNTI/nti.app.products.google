from zope import interface
from zope import component

from zope.cachedescriptors.property import Lazy

from zope.traversing.interfaces import IEtcNamespace

from nti.coremetadata.interfaces import IDataserver

from nti.dataserver.authorization import ACT_READ

from nti.dataserver.authorization_acl import acl_from_aces
from nti.dataserver.authorization_acl import ace_allowing

from nti.dataserver.interfaces import AUTHENTICATED_GROUP_NAME

from nti.app.products.google.interfaces import IGoogleAPIKey
from nti.app.products.google.interfaces import IGoogleAPIKeys


@interface.implementer(IGoogleAPIKey)
class GoogleAPIKey(object):

    __name__ = None

    key = None
    appid = None

    def __init__(self, name, appid, key):
        self.__name__ = name
        self.key = key
        self.appid = appid

    @property
    def __parent__(self):
        return component.queryUtility(IEtcNamespace, name='googleapikeys')


@interface.implementer(IGoogleAPIKeys)
class GoogleAPIKeys(object):

    __name__ = 'googleapikeys'

    def __getitem__(self, key):
        return component.queryUtility(IGoogleAPIKey, name=key)

    @property
    def __parent__(self):
        ds = component.getUtility(IDataserver)
        return ds.dataserver_folder

    @Lazy
    def __acl__(self):
        return acl_from_aces([ace_allowing(AUTHENTICATED_GROUP_NAME, ACT_READ, self)])

from zope import interface
from zope import component

from zope.cachedescriptors.property import Lazy

from nti.dataserver.authorization import ACT_READ

from nti.dataserver.authorization_acl import acl_from_aces
from nti.dataserver.authorization_acl import ace_allowing

from nti.dataserver.interfaces import AUTHENTICATED_GROUP_NAME

from nti.app.products.google.interfaces import IAPIKey
from nti.app.products.google.interfaces import IGoogleApiKeys

@interface.implementer(IAPIKey)
class APIKey(object):

    __name__ = None
    
    key = None
    appid = None

    def __init__(self, name, appid, key):
        self.__name__ = name
        self.key = key
        self.appid = appid


@interface.implementer(IGoogleApiKeys)
class GoogleApiKeys(object):

    __name__ = 'googleapikeys'

    def __getitem__(self, key):
        return component.queryUtility(IAPIKey, name=key)

    @Lazy
    def __acl__(self):
        return acl_from_aces([ace_allowing(AUTHENTICATED_GROUP_NAME, ACT_READ, self)])

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.appserver.workspaces.interfaces import IUserWorkspaceLinkProvider

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserver

from nti.links.links import Link

from nti.app.products.google.interfaces import IGoogleAPIKey

logger = __import__('logging').getLogger(__name__)


@component.adapter(IUser)
@interface.implementer(IUserWorkspaceLinkProvider)
class _APIKeyLinkProvider(object):

    def __init__(self, user):
        self.user = user

    def links(self, unused_workspace):
        result = []
        # May have more than one key at some point; hardcode for now.
        key = component.queryUtility(IGoogleAPIKey, name='filepicker')
        if key is not None:
            ds_folder = component.getUtility(IDataserver)
            ds_folder = ds_folder.dataserver_folder
            lnk = Link(ds_folder,
                       elements=('++etc++googleapikeys', key.__name__),
                       method='GET',
                       rel="GoogleAPIKey")
            result.append(lnk)
        return result

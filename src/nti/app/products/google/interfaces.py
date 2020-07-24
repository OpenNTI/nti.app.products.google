from zope import interface

from zope.traversing.interfaces import IEtcNamespace

from nti.schema.field import ValidTextLine


class IGoogleAPIKey(interface.Interface):

    key = ValidTextLine(title=u'The API key',
                        required=True)

    appid = ValidTextLine(title=u'The name for this key',
                          required=True)


class IGoogleAPIKeys(IEtcNamespace):
    """
    A traversal namespace that looks up :class:`IGoogleAPIKey` by name
    """

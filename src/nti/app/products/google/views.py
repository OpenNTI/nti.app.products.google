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

from nti.app.externalization.error import raise_json_error

from nti.appserver.dataserver_pyramid_views import GenericGetView

from nti.dataserver import authorization as nauth

from nti.app.products.google.interfaces import IGoogleAPIKey

logger = __import__('logging').getLogger(__name__)


def raise_error(data, tb=None,
                factory=hexc.HTTPUnprocessableEntity,
                request=None):
    raise_json_error(request, factory, data, tb)


@view_config(route_name='objects.generic.traversal',
             context=IGoogleAPIKey,
             request_method='GET',
             permission=nauth.ACT_READ,
             renderer='rest')
class GoogleAPIKeyGetView(GenericGetView):
    pass

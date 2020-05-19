#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class,expression-not-assigned

from nti.app.products.integration.interfaces import IIntegration


class IGoogleSSOIntegration(IIntegration):
    """
    Google SSO integration
    """

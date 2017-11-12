# -*- coding: utf-8 -*-
"""
    sphinx.util.rst
    ~~~~~~~~~~~~~~~

    reST helper functions.

    :copyright: Copyright 2007-2017 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
from __future__ import absolute_import

import re
from contextlib import contextmanager

from docutils.parsers.rst import roles
from docutils.parsers.rst.languages import en as english
from docutils.utils import Reporter

from sphinx.util import logging

if False:
    # For type annotation
    from typing import Generator  # NOQA

symbols_re = re.compile(r'([!-/:-@\[-`{-~])')
logger = logging.getLogger(__name__)


def escape(text):
    # type: (unicode) -> unicode
    return symbols_re.sub(r'\\\1', text)  # type: ignore


@contextmanager
def default_role(docname, name):
    # type: (unicode, unicode) -> Generator
    if name:
        dummy_reporter = Reporter('', 4, 4)
        role_fn, _ = roles.role(name, english, 0, dummy_reporter)
        if role_fn:
            roles._roles[''] = role_fn
        else:
            logger.warning('default role %s not found', name, location=docname)

    yield

    roles._roles.pop('', None)  # if a document has set a local default role

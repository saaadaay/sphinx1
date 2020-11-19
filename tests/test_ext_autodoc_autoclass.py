"""
    test_ext_autodoc_autoclass
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Test the autodoc extension.  This tests mainly the Documenters; the auto
    directives are tested in a test source file translated by test_build.

    :copyright: Copyright 2007-2020 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import sys

import pytest
from test_ext_autodoc import do_autodoc


@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_classes(app):
    actual = do_autodoc(app, 'function', 'target.classes.Foo')
    assert list(actual) == [
        '',
        '.. py:function:: Foo()',
        '   :module: target.classes',
        '',
    ]

    actual = do_autodoc(app, 'function', 'target.classes.Bar')
    assert list(actual) == [
        '',
        '.. py:function:: Bar(x, y)',
        '   :module: target.classes',
        '',
    ]

    actual = do_autodoc(app, 'function', 'target.classes.Baz')
    assert list(actual) == [
        '',
        '.. py:function:: Baz(x, y)',
        '   :module: target.classes',
        '',
    ]

    actual = do_autodoc(app, 'function', 'target.classes.Qux')
    assert list(actual) == [
        '',
        '.. py:function:: Qux(foo, bar)',
        '   :module: target.classes',
        '',
    ]


def test_decorators(app):
    actual = do_autodoc(app, 'class', 'target.decorator.Baz')
    assert list(actual) == [
        '',
        '.. py:class:: Baz(name=None, age=None)',
        '   :module: target.decorator',
        '',
    ]

    actual = do_autodoc(app, 'class', 'target.decorator.Qux')
    assert list(actual) == [
        '',
        '.. py:class:: Qux(name=None, age=None)',
        '   :module: target.decorator',
        '',
    ]

    actual = do_autodoc(app, 'class', 'target.decorator.Quux')
    assert list(actual) == [
        '',
        '.. py:class:: Quux(name=None, age=None)',
        '   :module: target.decorator',
        '',
    ]


@pytest.mark.skipif(sys.version_info < (3, 7), reason='python 3.7+ is required.')
@pytest.mark.sphinx('html', testroot='ext-autodoc')
def test_show_inheritance_for_subclass_of_generic_type(app):
    options = {'show-inheritance': True}
    actual = do_autodoc(app, 'class', 'target.classes.Quux', options)
    assert list(actual) == [
        '',
        '.. py:class:: Quux(iterable=(), /)',
        '   :module: target.classes',
        '',
        '   Bases: :class:`List`\\ [:obj:`Union`\\ [:class:`int`, :class:`float`]]',
        '',
        '   A subclass of List[Union[int, float]]',
        '',
    ]

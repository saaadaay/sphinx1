# -*- coding: utf-8 -*-
"""
    test_cmdline
    ~~~~~~~~~~~~

    Test the :class:`sphinx.cmdline` module.

    :copyright: Copyright 2007-2017 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import os
import os.path

import mock

from sphinx.cmdline import main, _find_source_dir


@mock.patch('os.listdir')
@mock.patch('os.path.isdir')
@mock.patch('os.path.exists')
def test_find_source_dir(mock_exists, mock_isdir, mock_listdir):
    """Test basic behavior of source dir."""
    src_dir = os.path.join('doc', 'source')

    def path_exists(path):
        return path == os.path.join(src_dir, 'conf.py')

    def path_isdir(path):
        return path == 'doc'  # mimic only the 'doc' directory existing

    def listdir(path):
        return ['stuff', 'source']

    mock_exists.side_effect = path_exists
    mock_isdir.side_effect = path_isdir
    mock_listdir.side_effect = listdir

    assert _find_source_dir() == src_dir

    # we should only have checked 'doc' since no other directory "existed"
    mock_listdir.assert_called_once_with('doc')


@mock.patch('os.path.isfile', return_value=True)
@mock.patch('os.path.isdir', return_value=True)
@mock.patch('sphinx.cmdline.Sphinx')
def test_posargs_full(mock_sphinx, mock_isdir, mock_isfile):
    """Validate behavior with the full complement of posargs."""
    args = ['srcdir', 'outdir', 'file_a', 'file_b', 'file_c']
    main(args)

    mock_sphinx.assert_called_once_with(
        args[0], args[0], args[1], os.path.join(args[1], '.doctrees'),
        mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY,
        mock.ANY, mock.ANY)
    mock_sphinx.return_value.build.assert_called_once_with(False, args[2:])


@mock.patch('os.path.isfile', return_value=True)
@mock.patch('os.path.isdir', return_value=True)
@mock.patch('sphinx.cmdline.Sphinx')
def test_posargs_no_filenames(mock_sphinx, mock_isdir, mock_isfile):
    """Validate behavior with the source and output dir posarg."""
    args = ['srcdir', 'outdir']
    main(args)

    mock_sphinx.assert_called_once_with(
        args[0], args[0], args[1], os.path.join(args[1], '.doctrees'),
        mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY,
        mock.ANY, mock.ANY)
    mock_sphinx.return_value.build.assert_called_once_with(False, [])


@mock.patch('os.path.isfile', return_value=True)
@mock.patch('os.path.isdir', return_value=True)
@mock.patch('sphinx.cmdline.Sphinx')
def test_posargs_no_outputdir(mock_sphinx, mock_isdir, mock_isfile):
    """Validate behavior with only the source dir posarg."""
    args = ['srcdir']
    main(args)

    mock_sphinx.assert_called_once_with(
        args[0], args[0], None, None, mock.ANY, mock.ANY, mock.ANY, mock.ANY,
        mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY)
    mock_sphinx.return_value.build.assert_called_once_with(False, [])


@mock.patch('sphinx.cmdline._find_source_dir')
@mock.patch('os.path.isfile', return_value=True)
@mock.patch('os.path.isdir', return_value=True)
@mock.patch('sphinx.cmdline.Sphinx')
def test_posargs_none(mock_sphinx, mock_isdir, mock_isfile, mock_find_src):
    """Validate behavior with no posargs."""
    args = []
    main(args)

    srcdir = mock_find_src.return_value

    mock_sphinx.assert_called_once_with(
        srcdir, srcdir, None, None, mock.ANY, mock.ANY, mock.ANY, mock.ANY,
        mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY)
    mock_sphinx.return_value.build.assert_called_once_with(False, [])

sphinx-apidoc
=============

Synopsis
--------

**sphinx-apidoc** [*options*] -o <*outputdir*> <*sourcedir*> [*pathnames* ...]

Description
-----------

:program:`sphinx-apidoc` is a tool for automatic generation of Sphinx sources
that, using the :rst:dir:`autodoc` extension, document a whole package in the
style of other automatic API documentation tools.

*sourcedir* is the path to a Python package to document, and *outputdir* is the
directory where the generated sources are placed. Any *pathnames* given are
paths to be excluded from the generation.

.. warning::

   ``sphinx-apidoc`` generates source files that use :mod:`sphinx.ext.autodoc`
   to document all found modules.  If any modules have side effects on import,
   these will be executed by ``autodoc`` when ``sphinx-build`` is run.

   If you document scripts (as opposed to library modules), make sure their main
   routine is protected by a ``if __name__ == '__main__'`` condition.

Options
-------

.. program:: sphinx-apidoc

.. option:: -o <outputdir>

   Directory to place the output files. If it does not exist, it is created.

.. option:: -f, --force

   Force overwritting of any existing generated files.

.. option:: -l, --follow-links

   Follow symbolic links.

.. option:: -n, --dry-run

   Do not create any files.

.. option:: -s <suffix>

   Suffix for the source files generated. Defaults to ``rst``.

.. option:: -d <maxdepth>

   Maximum depth for the generated table of contents file.

.. option:: -T, --no-toc

   Do not create a table of contents file. Ignored when :option:`--full` is
   provided.

.. option:: -F, --full

   Generate a full Sphinx project (``conf.py``, ``Makefile`` etc.) using
   the same mechanism as :program:`sphinx-quickstart`.

.. option:: -e, --separate

   Put documentation for each module on its own page.

   .. versionadded:: 1.2

.. option:: -E, --no-headings

   Do not create headings for the modules/packages. This is useful, for
   example, when docstrings already contain headings.

.. option:: -P, --private

   Include "_private" modules.

   .. versionadded:: 1.2

.. option:: --implicit-namespaces

   By default sphinx-apidoc processes sys.path searching for modules only.
   Python 3.3 introduced :pep:`420` implicit namespaces that allow module path
   structures such as ``foo/bar/module.py`` or ``foo/bar/baz/__init__.py``
   (notice that ``bar`` and ``foo`` are namespaces, not modules).

   Interpret paths recursively according to PEP-0420.

.. option:: -M

   Put module documentation before submodule documentation.

These options are used when :option:`--full` is specified:

.. option:: -a

   Append module_path to sys.path.

.. option:: -H <project>

   Sets the project name to put in generated files (see :confval:`project`).

.. option:: -A <author>

   Sets the author name(s) to put in generated files (see
   :confval:`copyright`).

.. option:: -V <version>

   Sets the project version to put in generated files (see :confval:`version`).

.. option:: -R <release>

   Sets the project release to put in generated files (see :confval:`release`).

See also
--------

:manpage:`sphinx-build(1)`, :manpage:`sphinx-autogen(1)`

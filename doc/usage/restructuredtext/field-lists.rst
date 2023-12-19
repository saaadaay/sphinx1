.. highlight:: rst

===========
Field Lists
===========

:ref:`As previously discussed <rst-field-lists>`, field lists are sequences of
fields marked up like this::

    :fieldname: Field content

Sphinx extends standard docutils behavior for field lists and adds some extra
functionality that is covered in this section.

.. note::

    The values of field lists will be parsed as
    strings. You cannot use Python collections such as lists or dictionaries.


.. _metadata:

File-wide metadata
------------------

A field list near the top of a file is normally parsed by docutils as the
*docinfo* and shown on the page.  However, in Sphinx, a field list preceding
any other markup is moved from the *docinfo* to the Sphinx environment as
document metadata, and is not displayed in the output.

.. note::

   A field list appearing after the document title *will* be part of the
   *docinfo* as normal and will be displayed in the output.


.. _special-metadata-fields:

Special metadata fields
-----------------------

Sphinx provides custom behavior for bibliographic fields compared to docutils.

At the moment, these metadata fields are recognized:

``tocdepth``
   The maximum depth for a table of contents of this file. ::

       :tocdepth: 2

   .. note::

      This metadata effects to the depth of local toctree.  But it does not
      effect to the depth of *global* toctree.  So this would not be change
      the sidebar of some themes which uses global one.

   .. versionadded:: 0.4

``nocomments``
   If set, the web application won't display a comment form for a page
   generated from this source file. ::

       :nocomments:

``orphan``
   If set, warnings about this file not being included in any toctree will be
   suppressed. ::

       :orphan:

   .. versionadded:: 1.0

``nosearch``
   If set, full text search for this file is disabled. ::

       :nosearch:

   .. note:: object search is still available even if `nosearch` option is set.

   .. versionadded:: 3.0

``notranslate``
   If set, no paragraphs from this document will be added to Gettext message
   catalogs. This may be useful to save work to the translators, e.g., if you
   want to internationalize tutorials but not technical reference material. When
   found in a document ``.../index``, this recursively applies to all
   documents in the directory ``.../``.

   .. versionadded:: 7.3.0

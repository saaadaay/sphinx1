# -*- coding: utf-8 -*-
"""
    sphinx.io
    ~~~~~~~~~

    Input/Output files

    :copyright: Copyright 2007-2017 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
import codecs

from docutils.io import FileInput, NullOutput
from docutils.core import Publisher
from docutils.readers import standalone
from docutils.writers import UnfilteredWriter
from six import string_types, text_type, iteritems
from typing import Any, Union  # NOQA

from sphinx.transforms import (
    ApplySourceWorkaround, ExtraTranslatableNodes, CitationReferences,
    DefaultSubstitutions, MoveModuleTargets, HandleCodeBlocks, SortIds,
    AutoNumbering, AutoIndexUpgrader, FilterSystemMessages,
    UnreferencedFootnotesDetector
)
from sphinx.transforms.compact_bullet_list import RefOnlyBulletListTransform
from sphinx.transforms.i18n import (
    PreserveTranslatableMessages, Locale, RemoveTranslatableInline,
)
from sphinx.util import logging
from sphinx.util import import_object, split_docinfo
from sphinx.util.docutils import LoggingReporter

if False:
    # For type annotation
    from typing import Any, Dict, List, Tuple, Union  # NOQA
    from docutils import nodes  # NOQA
    from docutils.io import Input  # NOQA
    from docutils.parsers import Parser  # NOQA
    from docutils.transforms import Transform  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.builders import Builder  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA


logger = logging.getLogger(__name__)


class SphinxBaseReader(standalone.Reader):
    """
    Add our source parsers
    """
    def __init__(self, app, parsers={}, *args, **kwargs):
        # type: (Sphinx, Dict[unicode, Parser], Any, Any) -> None
        standalone.Reader.__init__(self, *args, **kwargs)
        self.parser_map = {}  # type: Dict[unicode, Parser]
        for suffix, parser_class in parsers.items():
            if isinstance(parser_class, string_types):
                parser_class = import_object(parser_class, 'source parser')  # type: ignore
            parser = parser_class()
            if hasattr(parser, 'set_application'):
                parser.set_application(app)
            self.parser_map[suffix] = parser

    def read(self, source, parser, settings):
        # type: (Input, Parser, Dict) -> nodes.document
        self.source = source

        for suffix in self.parser_map:
            if source.source_path.endswith(suffix):
                self.parser = self.parser_map[suffix]
                break
        else:
            # use special parser for unknown file-extension '*' (if exists)
            self.parser = self.parser_map.get('*')

        if not self.parser:
            self.parser = parser
        self.settings = settings
        self.input = self.source.read()
        self.parse()
        return self.document

    def get_transforms(self):
        # type: () -> List[Transform]
        return standalone.Reader.get_transforms(self) + self.transforms

    def new_document(self):
        # type: () -> nodes.document
        document = standalone.Reader.new_document(self)
        reporter = document.reporter
        document.reporter = LoggingReporter(reporter.source, reporter.report_level,
                                            reporter.halt_level, reporter.debug_flag,
                                            reporter.error_handler)
        return document


class SphinxStandaloneReader(SphinxBaseReader):
    """
    Add our own transforms.
    """
    transforms = [ApplySourceWorkaround, ExtraTranslatableNodes, PreserveTranslatableMessages,
                  Locale, CitationReferences, DefaultSubstitutions, MoveModuleTargets,
                  HandleCodeBlocks, AutoNumbering, AutoIndexUpgrader, SortIds,
                  RemoveTranslatableInline, PreserveTranslatableMessages, FilterSystemMessages,
                  RefOnlyBulletListTransform, UnreferencedFootnotesDetector]


class SphinxI18nReader(SphinxBaseReader):
    """
    Replacer for document.reporter.get_source_and_line method.

    reST text lines for translation do not have the original source line number.
    This class provides the correct line numbers when reporting.
    """

    transforms = [ApplySourceWorkaround, ExtraTranslatableNodes, CitationReferences,
                  DefaultSubstitutions, MoveModuleTargets, HandleCodeBlocks,
                  AutoNumbering, SortIds, RemoveTranslatableInline,
                  FilterSystemMessages, RefOnlyBulletListTransform,
                  UnreferencedFootnotesDetector]

    def __init__(self, *args, **kwargs):
        # type: (Any, Any) -> None
        SphinxBaseReader.__init__(self, *args, **kwargs)
        self.lineno = None  # type: int

    def set_lineno_for_reporter(self, lineno):
        # type: (int) -> None
        self.lineno = lineno

    def new_document(self):
        # type: () -> nodes.document
        document = SphinxBaseReader.new_document(self)
        reporter = document.reporter

        def get_source_and_line(lineno=None):
            # type: (int) -> Tuple[unicode, int]
            return reporter.source, self.lineno

        reporter.get_source_and_line = get_source_and_line
        return document


class SphinxDummyWriter(UnfilteredWriter):
    supported = ('html',)  # needed to keep "meta" nodes

    def translate(self):
        # type: () -> None
        pass


def SphinxDummySourceClass(source, *args, **kwargs):
    """Bypass source object as is to cheat Publisher."""
    return source


class SphinxFileInput(FileInput):
    def __init__(self, app, env, *args, **kwds):
        # type: (Sphinx, BuildEnvironment, Any, Any) -> None
        self.app = app
        self.env = env

        # set up error handler
        codecs.register_error('sphinx', self.warn_and_replace)  # type: ignore

        kwds['error_handler'] = 'sphinx'  # py3: handle error on open.
        FileInput.__init__(self, *args, **kwds)

    def decode(self, data):
        # type: (Union[unicode, bytes]) -> unicode
        if isinstance(data, text_type):  # py3: `data` already decoded.
            return data
        return data.decode(self.encoding, 'sphinx')  # py2: decoding

    def read(self):
        # type: () -> unicode
        def get_parser_type(source_path):
            # type: (unicode) -> Tuple[unicode]
            for suffix, parser_class in iteritems(self.app.registry.get_source_parsers()):
                if source_path.endswith(suffix):
                    if isinstance(parser_class, string_types):
                        parser_class = import_object(parser_class, 'source parser')  # type: ignore  # NOQA
                    return parser_class.supported
            return ('restructuredtext',)

        data = FileInput.read(self)
        if self.app:
            arg = [data]
            self.app.emit('source-read', self.env.docname, arg)
            data = arg[0]
        docinfo, data = split_docinfo(data)
        if 'restructuredtext' in get_parser_type(self.source_path):
            if self.env.config.rst_epilog:
                data = data + '\n' + self.env.config.rst_epilog + '\n'
            if self.env.config.rst_prolog:
                data = self.env.config.rst_prolog + '\n' + data
        return docinfo + data

    def warn_and_replace(self, error):
        # type: (Any) -> Tuple
        """Custom decoding error handler that warns and replaces."""
        linestart = error.object.rfind(b'\n', 0, error.start)
        lineend = error.object.find(b'\n', error.start)
        if lineend == -1:
            lineend = len(error.object)
        lineno = error.object.count(b'\n', 0, error.start) + 1
        logger.warning('undecodable source characters, replacing with "?": %r',
                       (error.object[linestart + 1:error.start] + b'>>>' +
                        error.object[error.start:error.end] + b'<<<' +
                        error.object[error.end:lineend]),
                       location=(self.env.docname, lineno))
        return (u'?', error.end)


def read_doc(app, env, filename):
    # type: (Sphinx, BuildEnvironment, unicode) -> nodes.document
    """Parse a document and convert to doctree."""
    reader = SphinxStandaloneReader(app, parsers=app.registry.get_source_parsers())
    source = SphinxFileInput(app, env, source=None, source_path=filename,
                             encoding=env.config.source_encoding)

    pub = Publisher(reader=reader,
                    writer=SphinxDummyWriter(),
                    source_class=SphinxDummySourceClass,
                    destination=NullOutput())
    pub.set_components(None, 'restructuredtext', None)
    pub.process_programmatic_settings(None, env.settings, None)
    pub.set_source(source, filename)
    pub.publish()
    return pub.document

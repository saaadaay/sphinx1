"""Test the intersphinx extension."""

from __future__ import annotations

import posixpath
import re
import zlib
from http.server import BaseHTTPRequestHandler
from io import BytesIO
from typing import TYPE_CHECKING

import pytest

from tests.utils import http_server

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import BinaryIO

    from sphinx.ext.intersphinx._shared import InventoryCacheEntry
    from sphinx.util.typing import InventoryItem


class InventoryEntry:
    """Entry in the Intersphinx inventory."""

    __slots__ = (
        'name', 'display_name', 'domain_name',
        'object_type', 'uri', 'anchor', 'priority',
    )

    def __init__(
        self,
        name: str = 'this',
        *,
        display_name: str | None = None,
        domain_name: str = 'py',
        object_type: str = 'obj',
        uri: str = 'index.html',
        anchor: str = '',
        priority: int = 0,
    ):
        if anchor.endswith(name):
            anchor = anchor[:-len(name)] + '$'

        if anchor:
            uri += '#' + anchor

        if display_name is None or display_name == name:
            display_name = '-'

        self.name = name
        self.display_name = display_name
        self.domain_name = domain_name
        self.object_type = object_type
        self.uri = uri
        self.anchor = anchor
        self.priority = priority

    def format(self) -> str:
        """Format the entry as it appears in the inventory file."""
        return (f'{self.name} {self.domain_name}:{self.object_type} '
                f'{self.priority} {self.uri} {self.display_name}\n')


class IntersphinxProject:
    def __init__(
        self,
        name: str = 'foo',
        version: str | int = 1,
        baseurl: str = '',
        baseuri: str = '',
        file: str | None = None,
    ) -> None:
        #: The project name.
        self.name = name
        #: The escaped project name.
        self.safe_name = re.sub(r'\\s+', ' ', name)

        #: The project version as a string.
        self.version = version = str(version)
        #: The escaped project version.
        self.safe_version = re.sub(r'\\s+', ' ', version)

        #: The project base URL (e.g., http://localhost:7777).
        self.baseurl = baseurl
        #: The project base URI, relative to *baseurl* (e.g., 'foo').
        self.uri = baseuri
        #: The project URL, as specified in :confval:`intersphinx_mapping`.
        self.url = posixpath.join(baseurl, baseuri)
        #: The project local file, if any.
        self.file = file

    @property
    def record(self) -> dict[str, tuple[str | None, str | None]]:
        """The :confval:`intersphinx_mapping` record for this project."""
        return {self.name: (self.url, self.file)}

    def normalize(self, entry: InventoryEntry) -> tuple[str, InventoryItem]:
        """Format an inventory entry as if it were part of this project."""
        url = posixpath.join(self.url, entry.uri)
        return entry.name, (self.safe_name, self.safe_version, url, entry.display_name)


class FakeInventory:
    protocol_version: int

    def __init__(self, project: IntersphinxProject | None = None) -> None:
        self.project = project or IntersphinxProject()

    def serialize(self, entries: Iterable[InventoryEntry] | None = None) -> bytes:
        buffer = BytesIO()
        self._write_headers(buffer)
        entries = entries or [InventoryEntry()]
        self._write_body(buffer, (item.format().encode() for item in entries))
        return buffer.getvalue()

    def _write_headers(self, buffer: BinaryIO) -> None:
        buffer.write((f'# Sphinx inventory version {self.protocol_version}\n'
                      f'# Project: {self.project.safe_name}\n'
                      f'# Version: {self.project.safe_version}\n').encode())

    def _write_body(self, buffer: BinaryIO, lines: Iterable[bytes]) -> None:
        raise NotImplementedError


class FakeInventoryV2(FakeInventory):
    protocol_version = 2

    def _write_headers(self, buffer: BinaryIO) -> None:
        super()._write_headers(buffer)
        buffer.write(b'# The remainder of this file is compressed using zlib.\n')

    def _write_body(self, buffer: BinaryIO, lines: Iterable[bytes]) -> None:
        compressor = zlib.compressobj(9)
        buffer.writelines(map(compressor.compress, lines))
        buffer.write(compressor.flush())


class SingleEntryProject(IntersphinxProject):
    name = 'foo'
    port = 7777  # needd since otherwise it's an automatic port

    def __init__(
        self,
        version: int,
        route: str,
        *,
        item_name: str = 'bar',
        domain_name: str = 'py',
        object_type: str = 'module'
    ) -> None:
        self.item_name = item_name
        self.domain_name = domain_name
        self.object_type = object_type
        self.reftype = f'{domain_name}:{object_type}'
        super().__init__(self.name, version, f'http://localhost:{self.port}', route)

    def make_entry(self) -> InventoryEntry:
        """Get an inventory entry for this project."""
        name = f'{self.item_name}_{self.version}'
        return InventoryEntry(name, domain_name=self.domain_name, object_type=self.object_type)


def make_inventory_handler(*projects: SingleEntryProject) -> type[BaseHTTPRequestHandler]:
    name, port = projects[0].name, projects[0].port
    assert all(p.name == name for p in projects)
    assert all(p.port == port for p in projects)

    class InventoryHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200, 'OK')

            data = b''
            for project in projects:
                # create the data to return depending on the endpoint
                if self.path.startswith(f'/{project.uri}/'):
                    entry = project.make_entry()
                    data = FakeInventoryV2(project).serialize([entry])
                    break

            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(*args, **kwargs):
            pass

    return InventoryHandler


def test_intersphinx_project_fixture():
    # check that our fixture class is correct
    project = SingleEntryProject(1, 'route')
    assert project.url == 'http://localhost:7777/route'


@pytest.mark.sphinx('dummy', testroot='basic', freshenv=True)
def test_load_mappings_cache(make_app, app_params):
    project = SingleEntryProject(1, 'a')
    # clean build
    args, kwargs = app_params
    confoverrides = {'extensions': ['sphinx.ext.intersphinx'],
                     'intersphinx_mapping': project.record}

    InventoryHandler = make_inventory_handler(project)
    with http_server(InventoryHandler, port=project.port):
        app = make_app(*args, confoverrides=confoverrides, **kwargs)
        app.build()

    # the inventory when querying the 'old' URL
    entry = project.make_entry()
    item = dict([project.normalize(entry)])
    assert list(app.env.intersphinx_cache) == ['http://localhost:7777/a']
    e: InventoryCacheEntry = app.env.intersphinx_cache['http://localhost:7777/a']
    assert (e[0], e[2]) == ('foo', {'py:module': item})
    assert app.env.intersphinx_named_inventory == {'foo': {'py:module': item}}


@pytest.mark.sphinx('dummy', testroot='basic', freshenv=True)
def test_load_mappings_cache_update(make_app, app_params):
    old_project = SingleEntryProject(1337, 'old')
    new_project = SingleEntryProject(1701, 'new')

    args, kwargs = app_params
    baseconfig = {'extensions': ['sphinx.ext.intersphinx']}
    InventoryHandler = make_inventory_handler(old_project, new_project)
    with http_server(InventoryHandler, port=SingleEntryProject.port):
        # build normally to create an initial cache
        confoverrides1 = baseconfig | {'intersphinx_mapping': old_project.record}
        _ = make_app(*args, confoverrides=confoverrides1, **kwargs)
        _.build()
        # switch to new url and assert that the old URL is no more stored
        confoverrides2 = baseconfig | {'intersphinx_mapping': new_project.record}
        app = make_app(*args, confoverrides=confoverrides2, **kwargs)
        app.build()

    entry = new_project.make_entry()
    item = dict([new_project.normalize(entry)])
    # check that the URLs were changed accordingly
    assert list(app.env.intersphinx_cache) == ['http://localhost:7777/new']
    e: InventoryCacheEntry = app.env.intersphinx_cache['http://localhost:7777/new']
    assert (e[0], e[2]) == ('foo', {'py:module': item})
    assert app.env.intersphinx_named_inventory == {'foo': {'py:module': item}}


@pytest.mark.sphinx('dummy', testroot='basic', freshenv=True)
def test_load_mappings_cache_revert_update(make_app, app_params):
    old_project = SingleEntryProject(1337, 'old')
    new_project = SingleEntryProject(1701, 'new')

    args, kwargs = app_params
    baseconfig = {'extensions': ['sphinx.ext.intersphinx']}
    InventoryHandler = make_inventory_handler(old_project, new_project)
    with http_server(InventoryHandler, port=SingleEntryProject.port):
        # build normally to create an initial cache
        confoverrides1 = baseconfig | {'intersphinx_mapping': old_project.record}
        _ = make_app(*args, confoverrides=confoverrides1, **kwargs)
        _.build()
        # switch to new url and build
        confoverrides2 = baseconfig | {'intersphinx_mapping': new_project.record}
        _ = make_app(*args, confoverrides=confoverrides2, **kwargs)
        _.build()
        # switch back to old url (re-use 'old_item')
        confoverrides3 = baseconfig | {'intersphinx_mapping': old_project.record}
        app = make_app(*args, confoverrides=confoverrides3, **kwargs)
        app.build()

    entry = old_project.make_entry()
    item = dict([old_project.normalize(entry)])
    # check that the URLs were changed accordingly
    assert list(app.env.intersphinx_cache) == ['http://localhost:7777/old']
    e: InventoryCacheEntry = app.env.intersphinx_cache['http://localhost:7777/old']
    assert (e[0], e[2]) == ('foo', {'py:module': item})
    assert app.env.intersphinx_named_inventory == {'foo': {'py:module': item}}

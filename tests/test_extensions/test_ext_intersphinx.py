"""Test the intersphinx extension."""

import http.server
from unittest import mock

import pytest
from docutils import nodes

from sphinx import addnodes
from sphinx.ext.intersphinx import (
    INVENTORY_FILENAME,
    _get_safe_url,
    _process_disabled_reftypes,
    _strip_basic_auth,
    fetch_inventory,
    inspect_main,
    load_mappings,
    missing_reference,
    normalize_intersphinx_mapping,
)
from sphinx.ext.intersphinx import setup as intersphinx_setup
from sphinx.util.console import strip_colors

from tests.test_util.intersphinx_data import INVENTORY_V2, INVENTORY_V2_NO_VERSION
from tests.utils import http_server


def fake_node(domain, type, target, content, **attrs):
    contnode = nodes.emphasis(content, content)
    node = addnodes.pending_xref('')
    node['reftarget'] = target
    node['reftype'] = type
    node['refdomain'] = domain
    node.attributes.update(attrs)
    node += contnode
    return node, contnode


def reference_check(app, *args, **kwds):
    node, contnode = fake_node(*args, **kwds)
    return missing_reference(app, app.env, node, contnode)


def set_config(app, mapping):
    app.config.intersphinx_mapping = mapping
    app.config.intersphinx_cache_limit = 0
    app.config.intersphinx_disabled_reftypes = []
    _process_disabled_reftypes(app.env)


@mock.patch('sphinx.ext.intersphinx.InventoryFile')
@mock.patch('sphinx.ext.intersphinx._read_from_url')
def test_fetch_inventory_redirection(_read_from_url, InventoryFile, app, status, warning):  # NoQA: PT019
    intersphinx_setup(app)
    _read_from_url().readline.return_value = b'# Sphinx inventory version 2'

    # same uri and inv, not redirected
    _read_from_url().url = 'https://hostname/' + INVENTORY_FILENAME
    fetch_inventory(app, 'https://hostname/', 'https://hostname/' + INVENTORY_FILENAME)
    assert 'intersphinx inventory has moved' not in status.getvalue()
    assert InventoryFile.load.call_args[0][1] == 'https://hostname/'

    # same uri and inv, redirected
    status.seek(0)
    status.truncate(0)
    _read_from_url().url = 'https://hostname/new/' + INVENTORY_FILENAME

    fetch_inventory(app, 'https://hostname/', 'https://hostname/' + INVENTORY_FILENAME)
    assert status.getvalue() == ('intersphinx inventory has moved: '
                                 'https://hostname/%s -> https://hostname/new/%s\n' %
                                 (INVENTORY_FILENAME, INVENTORY_FILENAME))
    assert InventoryFile.load.call_args[0][1] == 'https://hostname/new'

    # different uri and inv, not redirected
    status.seek(0)
    status.truncate(0)
    _read_from_url().url = 'https://hostname/new/' + INVENTORY_FILENAME

    fetch_inventory(app, 'https://hostname/', 'https://hostname/new/' + INVENTORY_FILENAME)
    assert 'intersphinx inventory has moved' not in status.getvalue()
    assert InventoryFile.load.call_args[0][1] == 'https://hostname/'

    # different uri and inv, redirected
    status.seek(0)
    status.truncate(0)
    _read_from_url().url = 'https://hostname/other/' + INVENTORY_FILENAME

    fetch_inventory(app, 'https://hostname/', 'https://hostname/new/' + INVENTORY_FILENAME)
    assert status.getvalue() == ('intersphinx inventory has moved: '
                                 'https://hostname/new/%s -> https://hostname/other/%s\n' %
                                 (INVENTORY_FILENAME, INVENTORY_FILENAME))
    assert InventoryFile.load.call_args[0][1] == 'https://hostname/'


def test_missing_reference(tmp_path, app, status, warning):
    inv_file = tmp_path / 'inventory'
    inv_file.write_bytes(INVENTORY_V2)
    set_config(app, {
        'https://docs.python.org/': str(inv_file),
        'py3k': ('https://docs.python.org/py3k/', str(inv_file)),
        'py3krel': ('py3k', str(inv_file)),  # relative path
        'py3krelparent': ('../../py3k', str(inv_file)),  # relative path, parent dir
    })

    # load the inventory and check if it's done correctly
    normalize_intersphinx_mapping(app, app.config)
    load_mappings(app)
    inv = app.env.intersphinx_inventory

    assert inv['py:module']['module2'] == \
        ('foo', '2.0', 'https://docs.python.org/foo.html#module-module2', '-')

    # check resolution when a target is found
    rn = reference_check(app, 'py', 'func', 'module1.func', 'foo')
    assert isinstance(rn, nodes.reference)
    assert rn['refuri'] == 'https://docs.python.org/sub/foo.html#module1.func'
    assert rn['reftitle'] == '(in foo v2.0)'
    assert rn[0].astext() == 'foo'

    # create unresolvable nodes and check None return value
    assert reference_check(app, 'py', 'foo', 'module1.func', 'foo') is None
    assert reference_check(app, 'py', 'func', 'foo', 'foo') is None
    assert reference_check(app, 'py', 'func', 'foo', 'foo') is None

    # check handling of prefixes

    # prefix given, target found: prefix is stripped
    rn = reference_check(app, 'py', 'mod', 'py3k:module2', 'py3k:module2')
    assert rn[0].astext() == 'module2'

    # prefix given, but not in title: nothing stripped
    rn = reference_check(app, 'py', 'mod', 'py3k:module2', 'module2')
    assert rn[0].astext() == 'module2'

    # prefix given, but explicit: nothing stripped
    rn = reference_check(app, 'py', 'mod', 'py3k:module2', 'py3k:module2',
                         refexplicit=True)
    assert rn[0].astext() == 'py3k:module2'

    # prefix given, target not found and nonexplicit title: prefix is not stripped
    node, contnode = fake_node('py', 'mod', 'py3k:unknown', 'py3k:unknown',
                               refexplicit=False)
    rn = missing_reference(app, app.env, node, contnode)
    assert rn is None
    assert contnode[0].astext() == 'py3k:unknown'

    # prefix given, target not found and explicit title: nothing is changed
    node, contnode = fake_node('py', 'mod', 'py3k:unknown', 'py3k:unknown',
                               refexplicit=True)
    rn = missing_reference(app, app.env, node, contnode)
    assert rn is None
    assert contnode[0].astext() == 'py3k:unknown'

    # check relative paths
    rn = reference_check(app, 'py', 'mod', 'py3krel:module1', 'foo')
    assert rn['refuri'] == 'py3k/foo.html#module-module1'

    rn = reference_check(app, 'py', 'mod', 'py3krelparent:module1', 'foo')
    assert rn['refuri'] == '../../py3k/foo.html#module-module1'

    rn = reference_check(app, 'py', 'mod', 'py3krel:module1', 'foo', refdoc='sub/dir/test')
    assert rn['refuri'] == '../../py3k/foo.html#module-module1'

    rn = reference_check(app, 'py', 'mod', 'py3krelparent:module1', 'foo',
                         refdoc='sub/dir/test')
    assert rn['refuri'] == '../../../../py3k/foo.html#module-module1'

    # check refs of standard domain
    rn = reference_check(app, 'std', 'doc', 'docname', 'docname')
    assert rn['refuri'] == 'https://docs.python.org/docname.html'


def test_missing_reference_pydomain(tmp_path, app, status, warning):
    inv_file = tmp_path / 'inventory'
    inv_file.write_bytes(INVENTORY_V2)
    set_config(app, {
        'https://docs.python.org/': str(inv_file),
    })

    # load the inventory and check if it's done correctly
    normalize_intersphinx_mapping(app, app.config)
    load_mappings(app)

    # no context data
    kwargs = {}
    node, contnode = fake_node('py', 'func', 'func', 'func()', **kwargs)
    rn = missing_reference(app, app.env, node, contnode)
    assert rn is None

    # py:module context helps to search objects
    kwargs = {'py:module': 'module1'}
    node, contnode = fake_node('py', 'func', 'func', 'func()', **kwargs)
    rn = missing_reference(app, app.env, node, contnode)
    assert rn.astext() == 'func()'

    # py:attr context helps to search objects
    kwargs = {'py:module': 'module1'}
    node, contnode = fake_node('py', 'attr', 'Foo.bar', 'Foo.bar', **kwargs)
    rn = missing_reference(app, app.env, node, contnode)
    assert rn.astext() == 'Foo.bar'


def test_missing_reference_stddomain(tmp_path, app, status, warning):
    inv_file = tmp_path / 'inventory'
    inv_file.write_bytes(INVENTORY_V2)
    set_config(app, {
        'cmd': ('https://docs.python.org/', str(inv_file)),
    })

    # load the inventory and check if it's done correctly
    normalize_intersphinx_mapping(app, app.config)
    load_mappings(app)

    # no context data
    kwargs = {}
    node, contnode = fake_node('std', 'option', '-l', '-l', **kwargs)
    rn = missing_reference(app, app.env, node, contnode)
    assert rn is None

    # std:program context helps to search objects
    kwargs = {'std:program': 'ls'}
    node, contnode = fake_node('std', 'option', '-l', 'ls -l', **kwargs)
    rn = missing_reference(app, app.env, node, contnode)
    assert rn.astext() == 'ls -l'

    # refers inventory by name
    kwargs = {}
    node, contnode = fake_node('std', 'option', 'cmd:ls -l', '-l', **kwargs)
    rn = missing_reference(app, app.env, node, contnode)
    assert rn.astext() == '-l'

    # term reference (normal)
    node, contnode = fake_node('std', 'term', 'a term', 'a term')
    rn = missing_reference(app, app.env, node, contnode)
    assert rn.astext() == 'a term'

    # term reference (case insensitive)
    node, contnode = fake_node('std', 'term', 'A TERM', 'A TERM')
    rn = missing_reference(app, app.env, node, contnode)
    assert rn.astext() == 'A TERM'

    # label reference (normal)
    node, contnode = fake_node('std', 'ref', 'The-Julia-Domain', 'The-Julia-Domain')
    rn = missing_reference(app, app.env, node, contnode)
    assert rn.astext() == 'The Julia Domain'

    # label reference (case insensitive)
    node, contnode = fake_node('std', 'ref', 'the-julia-domain', 'the-julia-domain')
    rn = missing_reference(app, app.env, node, contnode)
    assert rn.astext() == 'The Julia Domain'


@pytest.mark.sphinx('html', testroot='ext-intersphinx-cppdomain')
def test_missing_reference_cppdomain(tmp_path, app, status, warning):
    inv_file = tmp_path / 'inventory'
    inv_file.write_bytes(INVENTORY_V2)
    set_config(app, {
        'https://docs.python.org/': str(inv_file),
    })

    # load the inventory and check if it's done correctly
    normalize_intersphinx_mapping(app, app.config)
    load_mappings(app)

    app.build()
    html = (app.outdir / 'index.html').read_text(encoding='utf8')
    assert ('<a class="reference external"'
            ' href="https://docs.python.org/index.html#cpp_foo_bar"'
            ' title="(in foo v2.0)">'
            '<code class="xref cpp cpp-class docutils literal notranslate">'
            '<span class="pre">Bar</span></code></a>' in html)
    assert ('<a class="reference external"'
            ' href="https://docs.python.org/index.html#foons"'
            ' title="(in foo v2.0)"><span class="n"><span class="pre">foons</span></span></a>' in html)
    assert ('<a class="reference external"'
            ' href="https://docs.python.org/index.html#foons_bartype"'
            ' title="(in foo v2.0)"><span class="n"><span class="pre">bartype</span></span></a>' in html)


def test_missing_reference_jsdomain(tmp_path, app, status, warning):
    inv_file = tmp_path / 'inventory'
    inv_file.write_bytes(INVENTORY_V2)
    set_config(app, {
        'https://docs.python.org/': str(inv_file),
    })

    # load the inventory and check if it's done correctly
    normalize_intersphinx_mapping(app, app.config)
    load_mappings(app)

    # no context data
    kwargs = {}
    node, contnode = fake_node('js', 'meth', 'baz', 'baz()', **kwargs)
    rn = missing_reference(app, app.env, node, contnode)
    assert rn is None

    # js:module and js:object context helps to search objects
    kwargs = {'js:module': 'foo', 'js:object': 'bar'}
    node, contnode = fake_node('js', 'meth', 'baz', 'baz()', **kwargs)
    rn = missing_reference(app, app.env, node, contnode)
    assert rn.astext() == 'baz()'


def test_missing_reference_disabled_domain(tmp_path, app, status, warning):
    inv_file = tmp_path / 'inventory'
    inv_file.write_bytes(INVENTORY_V2)
    set_config(app, {
        'inv': ('https://docs.python.org/', str(inv_file)),
    })

    # load the inventory and check if it's done correctly
    normalize_intersphinx_mapping(app, app.config)
    load_mappings(app)

    def case(*, term, doc, py):
        def assert_(rn, expected):
            if expected is None:
                assert rn is None
            else:
                assert rn.astext() == expected

        kwargs = {}

        node, contnode = fake_node('std', 'term', 'a term', 'a term', **kwargs)
        rn = missing_reference(app, app.env, node, contnode)
        assert_(rn, 'a term' if term else None)

        node, contnode = fake_node('std', 'term', 'inv:a term', 'a term', **kwargs)
        rn = missing_reference(app, app.env, node, contnode)
        assert_(rn, 'a term')

        node, contnode = fake_node('std', 'doc', 'docname', 'docname', **kwargs)
        rn = missing_reference(app, app.env, node, contnode)
        assert_(rn, 'docname' if doc else None)

        node, contnode = fake_node('std', 'doc', 'inv:docname', 'docname', **kwargs)
        rn = missing_reference(app, app.env, node, contnode)
        assert_(rn, 'docname')

        # an arbitrary ref in another domain
        node, contnode = fake_node('py', 'func', 'module1.func', 'func()', **kwargs)
        rn = missing_reference(app, app.env, node, contnode)
        assert_(rn, 'func()' if py else None)

        node, contnode = fake_node('py', 'func', 'inv:module1.func', 'func()', **kwargs)
        rn = missing_reference(app, app.env, node, contnode)
        assert_(rn, 'func()')

    # the base case, everything should resolve
    assert app.config.intersphinx_disabled_reftypes == []
    _process_disabled_reftypes(app.env)
    case(term=True, doc=True, py=True)

    # disabled a single ref type
    app.config.intersphinx_disabled_reftypes = ['std:doc']
    _process_disabled_reftypes(app.env)
    case(term=True, doc=False, py=True)

    # disabled a whole domain
    app.config.intersphinx_disabled_reftypes = ['std:*']
    _process_disabled_reftypes(app.env)
    case(term=False, doc=False, py=True)

    # disabled all domains
    app.config.intersphinx_disabled_reftypes = ['*']
    _process_disabled_reftypes(app.env)
    case(term=False, doc=False, py=False)


def test_inventory_not_having_version(tmp_path, app, status, warning):
    inv_file = tmp_path / 'inventory'
    inv_file.write_bytes(INVENTORY_V2_NO_VERSION)
    set_config(app, {
        'https://docs.python.org/': str(inv_file),
    })

    # load the inventory and check if it's done correctly
    normalize_intersphinx_mapping(app, app.config)
    load_mappings(app)

    rn = reference_check(app, 'py', 'mod', 'module1', 'foo')
    assert isinstance(rn, nodes.reference)
    assert rn['refuri'] == 'https://docs.python.org/foo.html#module-module1'
    assert rn['reftitle'] == '(in foo)'
    assert rn[0].astext() == 'Long Module desc'


def test_load_mappings_warnings(tmp_path, app, status, warning):
    """
    load_mappings issues a warning if new-style mapping
    identifiers are not string
    """
    inv_file = tmp_path / 'inventory'
    inv_file.write_bytes(INVENTORY_V2)
    set_config(app, {
        'https://docs.python.org/': str(inv_file),
        'py3k': ('https://docs.python.org/py3k/', str(inv_file)),
        'repoze.workflow': ('https://docs.repoze.org/workflow/', str(inv_file)),
        'django-taggit': ('https://django-taggit.readthedocs.org/en/latest/',
                          str(inv_file)),
        12345: ('https://www.sphinx-doc.org/en/stable/', str(inv_file)),
    })

    # load the inventory and check if it's done correctly
    normalize_intersphinx_mapping(app, app.config)
    load_mappings(app)
    warnings = warning.getvalue().splitlines()
    assert len(warnings) == 2
    assert "The pre-Sphinx 1.0 'intersphinx_mapping' format is " in warnings[0]
    assert 'intersphinx identifier 12345 is not string. Ignored' in warnings[1]


def test_load_mappings_fallback(tmp_path, app, status, warning):
    inv_file = tmp_path / 'inventory'
    inv_file.write_bytes(INVENTORY_V2)
    set_config(app, {})

    # connect to invalid path
    app.config.intersphinx_mapping = {
        'fallback': ('https://docs.python.org/py3k/', '/invalid/inventory/path'),
    }
    normalize_intersphinx_mapping(app, app.config)
    load_mappings(app)
    assert "failed to reach any of the inventories" in warning.getvalue()

    rn = reference_check(app, 'py', 'func', 'module1.func', 'foo')
    assert rn is None

    # clear messages
    status.truncate(0)
    warning.truncate(0)

    # add fallbacks to mapping
    app.config.intersphinx_mapping = {
        'fallback': ('https://docs.python.org/py3k/', ('/invalid/inventory/path',
                                                       str(inv_file))),
    }
    normalize_intersphinx_mapping(app, app.config)
    load_mappings(app)
    assert "encountered some issues with some of the inventories" in status.getvalue()
    assert warning.getvalue() == ""

    rn = reference_check(app, 'py', 'func', 'module1.func', 'foo')
    assert isinstance(rn, nodes.reference)


class TestStripBasicAuth:
    """Tests for sphinx.ext.intersphinx._strip_basic_auth()"""

    def test_auth_stripped(self):
        """Basic auth creds stripped from URL containing creds"""
        url = 'https://user:12345@domain.com/project/objects.inv'
        expected = 'https://domain.com/project/objects.inv'
        actual = _strip_basic_auth(url)
        assert expected == actual

    def test_no_auth(self):
        """Url unchanged if param doesn't contain basic auth creds"""
        url = 'https://domain.com/project/objects.inv'
        expected = 'https://domain.com/project/objects.inv'
        actual = _strip_basic_auth(url)
        assert expected == actual

    def test_having_port(self):
        """Basic auth creds correctly stripped from URL containing creds even if URL
        contains port
        """
        url = 'https://user:12345@domain.com:8080/project/objects.inv'
        expected = 'https://domain.com:8080/project/objects.inv'
        actual = _strip_basic_auth(url)
        assert expected == actual


def test_getsafeurl_authed():
    """_get_safe_url() with a url with basic auth"""
    url = 'https://user:12345@domain.com/project/objects.inv'
    expected = 'https://user@domain.com/project/objects.inv'
    actual = _get_safe_url(url)
    assert expected == actual


def test_getsafeurl_authed_having_port():
    """_get_safe_url() with a url with basic auth having port"""
    url = 'https://user:12345@domain.com:8080/project/objects.inv'
    expected = 'https://user@domain.com:8080/project/objects.inv'
    actual = _get_safe_url(url)
    assert expected == actual


def test_getsafeurl_unauthed():
    """_get_safe_url() with a url without basic auth"""
    url = 'https://domain.com/project/objects.inv'
    expected = 'https://domain.com/project/objects.inv'
    actual = _get_safe_url(url)
    assert expected == actual


def test_inspect_main_noargs(capsys):
    """inspect_main interface, without arguments"""
    assert inspect_main([]) == 1

    expected = (
        "Print out an inventory file.\n"
        "Error: must specify local path or URL to an inventory file."
    )
    stdout, stderr = capsys.readouterr()
    assert stdout == ""
    assert stderr == expected + "\n"


def test_inspect_main_file(capsys, tmp_path):
    """inspect_main interface, with file argument"""
    inv_file = tmp_path / 'inventory'
    inv_file.write_bytes(INVENTORY_V2)

    inspect_main([str(inv_file)])

    stdout, stderr = capsys.readouterr()
    assert stdout.startswith("c:function\n")
    assert stderr == ""


def test_inspect_main_url(capsys):
    """inspect_main interface, with url argument"""
    class InventoryHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200, "OK")
            self.end_headers()
            self.wfile.write(INVENTORY_V2)

        def log_message(*args, **kwargs):
            # Silenced.
            pass

    with http_server(InventoryHandler) as server:
        url = f'http://localhost:{server.server_port}/{INVENTORY_FILENAME}'
        inspect_main([url])

    stdout, stderr = capsys.readouterr()
    assert stdout.startswith("c:function\n")
    assert stderr == ""


@pytest.mark.sphinx('html', testroot='ext-intersphinx-role')
def test_intersphinx_role(app, warning):
    inv_file = app.srcdir / 'inventory'
    inv_file.write_bytes(INVENTORY_V2)
    app.config.intersphinx_mapping = {
        'inv': ('https://example.org/', str(inv_file)),
    }
    app.config.intersphinx_cache_limit = 0
    app.config.nitpicky = True

    # load the inventory and check if it's done correctly
    normalize_intersphinx_mapping(app, app.config)
    load_mappings(app)

    app.build()
    content = (app.outdir / 'index.html').read_text(encoding='utf8')
    warnings = strip_colors(warning.getvalue()).splitlines()
    index_path = app.srcdir / 'index.rst'
    assert warnings == [
        f"{index_path}:21: WARNING: role for external cross-reference not found in domain 'py': 'nope'",
        f"{index_path}:28: WARNING: role for external cross-reference not found in domains 'cpp', 'std': 'nope'",
        f"{index_path}:39: WARNING: inventory for external cross-reference not found: 'invNope'",
        f"{index_path}:44: WARNING: role for external cross-reference not found in domain 'c': 'function' (perhaps you meant one of: 'func', 'identifier', 'type')",
        f"{index_path}:45: WARNING: role for external cross-reference not found in domains 'cpp', 'std': 'function' (perhaps you meant one of: 'cpp:func', 'cpp:identifier', 'cpp:type')",
        f'{index_path}:9: WARNING: external py:mod reference target not found: module3',
        f'{index_path}:14: WARNING: external py:mod reference target not found: module10',
        f'{index_path}:19: WARNING: external py:meth reference target not found: inv:Foo.bar',
    ]

    html = '<a class="reference external" href="https://example.org/{}" title="(in foo v2.0)">'
    assert html.format('foo.html#module-module1') in content
    assert html.format('foo.html#module-module2') in content

    assert html.format('sub/foo.html#module1.func') in content

    # default domain
    assert html.format('index.html#std_uint8_t') in content

    # std roles without domain prefix
    assert html.format('docname.html') in content
    assert html.format('index.html#cmdoption-ls-l') in content

    # explicit inventory
    assert html.format('cfunc.html#CFunc') in content

    # explicit title
    assert html.format('index.html#foons') in content

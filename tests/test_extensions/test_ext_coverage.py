"""Test the coverage builder."""

import pickle

import pytest


@pytest.mark.sphinx('coverage', testroot='root')
def test_build(app, status, warning):
    app.build()

    py_undoc = (app.outdir / 'python.txt').read_text(encoding='utf8')
    assert py_undoc.startswith('Undocumented Python objects\n'
                               '===========================\n')
    assert 'autodoc_target\n--------------\n' in py_undoc
    assert ' * Class -- missing methods:\n' in py_undoc
    assert ' * raises\n' in py_undoc
    assert ' * function\n' not in py_undoc  # these two are documented
    assert ' * Class\n' not in py_undoc     # in autodoc.txt

    assert " * mod -- No module named 'mod'" in py_undoc  # in the "failed import" section

    assert "undocumented  py" not in status.getvalue()

    c_undoc = (app.outdir / 'c.txt').read_text(encoding='utf8')
    assert c_undoc.startswith('Undocumented C API elements\n'
                              '===========================\n')
    assert 'api.h' in c_undoc
    assert ' * Py_SphinxTest' in c_undoc

    undoc_py, undoc_c, py_undocumented, py_documented = pickle.loads((app.outdir / 'undoc.pickle').read_bytes())
    assert len(undoc_c) == 1
    # the key is the full path to the header file, which isn't testable
    assert list(undoc_c.values())[0] == {('function', 'Py_SphinxTest')}

    assert 'autodoc_target' in undoc_py
    assert 'funcs' in undoc_py['autodoc_target']
    assert 'raises' in undoc_py['autodoc_target']['funcs']
    assert 'classes' in undoc_py['autodoc_target']
    assert 'Class' in undoc_py['autodoc_target']['classes']
    assert 'undocmeth' in undoc_py['autodoc_target']['classes']['Class']

    assert "undocumented  c" not in status.getvalue()


@pytest.mark.sphinx('coverage', testroot='ext-coverage')
def test_coverage_ignore_pyobjects(app, status, warning):
    app.build()
    actual = (app.outdir / 'python.txt').read_text(encoding='utf8')
    expected = '''\
Undocumented Python objects
===========================

Statistics
----------

+----------------------+----------+--------------+
| Module               | Coverage | Undocumented |
+======================+==========+==============+
| coverage_not_ignored | 0.00%    | 2            |
+----------------------+----------+--------------+
| TOTAL                | 0.00%    | 2            |
+----------------------+----------+--------------+

coverage_not_ignored
--------------------

Classes:
 * Documented -- missing methods:

   - not_ignored1
   - not_ignored2
 * NotIgnored

'''
    assert actual == expected


@pytest.mark.sphinx('coverage', testroot='root',
                    confoverrides={'coverage_show_missing_items': True})
def test_show_missing_items(app, status, warning):
    app.build()

    assert "undocumented" in status.getvalue()

    assert "py  function  raises" in status.getvalue()
    assert "py  class     Base" in status.getvalue()
    assert "py  method    Class.roger" in status.getvalue()

    assert "c   api       Py_SphinxTest [ function]" in status.getvalue()


@pytest.mark.isolate()  # because we are modifying the application in-place
@pytest.mark.sphinx('coverage', testroot='root',
                    confoverrides={'coverage_show_missing_items': True})
def test_show_missing_items_quiet(app, status, warning):
    app.quiet = True
    app.build()

    stdout, stderr = status.getvalue(), warning.getvalue()

    for warning_only in [
        "undocumented python function: autodoc_target :: raises",
        "undocumented python class: autodoc_target :: Base",
        "undocumented python method: autodoc_target :: Class :: roger",
        "undocumented c api: Py_SphinxTest [function]",
    ]:
        assert warning_only not in stdout
        assert warning_only in stderr

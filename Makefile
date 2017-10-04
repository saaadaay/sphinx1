PYTHON ?= python

.PHONY: all type-check clean clean-pyc clean-patchfiles clean-backupfiles \
        clean-generated test build

all: clean-pyc clean-backupfiles type-check test

type-check:
	mypy sphinx/

clean: clean-pyc clean-pycache clean-patchfiles clean-backupfiles clean-generated clean-testfiles clean-buildfiles clean-mypyfiles

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +

clean-pycache:
	find . -name __pycache__ -exec rm -rf {} +

clean-patchfiles:
	find . -name '*.orig' -exec rm -f {} +
	find . -name '*.rej' -exec rm -f {} +

clean-backupfiles:
	find . -name '*~' -exec rm -f {} +
	find . -name '*.bak' -exec rm -f {} +
	find . -name '*.swp' -exec rm -f {} +
	find . -name '*.swo' -exec rm -f {} +

clean-generated:
	find . -name '.DS_Store' -exec rm -f {} +
	rm -rf Sphinx.egg-info/
	rm -rf doc/_build/
	rm -f sphinx/pycode/*.pickle
	rm -f utils/*3.py*
	rm -f utils/regression_test.js

clean-testfiles:
	rm -rf tests/.coverage
	rm -rf tests/build
	rm -rf .tox/
	rm -rf .cache/

clean-buildfiles:
	rm -rf build

clean-mypyfiles:
	rm -rf .mypy_cache/

test:
	@cd tests; $(PYTHON) run.py --ignore py35 -v $(TEST)

test-async:
	@cd tests; $(PYTHON) run.py -v $(TEST)

build:
	@$(PYTHON) setup.py build

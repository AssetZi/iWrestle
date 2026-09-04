# iWrestle events pipeline. Run these from the pipeline/ directory.
PY := ./.venv/bin/python
SOURCE ?= pywrestling
FILE ?= $(shell ls -t data/events.*.json 2>/dev/null | head -1)

.PHONY: help venv test collect review approve push push-prod reconcile clean

help:
	@echo "make venv          create .venv and install pinned deps"
	@echo "make test          offline parser and mapping tests"
	@echo "make collect       scrape SOURCE=$(SOURCE) into data/"
	@echo "make review        show the newest collected file"
	@echo "make approve       approve every complete event in it"
	@echo "make push          write approved events to CloudKit development"
	@echo "make push-prod     write them to production (asks first)"
	@echo "make reconcile     compare CloudKit against the local ledger"
	@echo ""
	@echo "current FILE: $(FILE)"

venv:
	python3 -m venv .venv
	./.venv/bin/pip install --quiet --upgrade pip
	./.venv/bin/pip install --quiet -r requirements.txt
	@echo "venv ready"

test:
	$(PY) -m pytest tests -q

collect:
	$(PY) bin/collect.py --source $(SOURCE)

# Re-run the parser against the saved page: no network, no geocoding.
collect-offline:
	$(PY) bin/collect.py --source $(SOURCE) \
		--from-fixture fixtures/$(SOURCE)-index.html --skip-geocode

review:
	$(PY) bin/review.py $(FILE)

approve:
	$(PY) bin/review.py $(FILE) --approve-all

push:
	$(PY) bin/push.py $(FILE)

push-dry:
	$(PY) bin/push.py $(FILE) --dry-run

push-prod:
	$(PY) bin/push.py $(FILE) --production

reconcile:
	$(PY) bin/reconcile.py

clean:
	rm -rf data/events.*.json data/assets .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +

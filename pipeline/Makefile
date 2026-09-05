# iWrestle events pipeline. Run these from the pipeline/ directory.
PY := ./.venv/bin/python
SOURCE ?= pywrestling
DATE := $(shell date +%Y%m%d)
FILE ?= $(shell ls -t data/events.*.json 2>/dev/null | head -1)

.PHONY: help venv test token-check collect collect-offline enrich enrich-dry review approve push push-dry push-prod reconcile routine clean

help:
	@echo "make venv          create .venv and install pinned deps"
	@echo "make test          offline parser and mapping tests"
	@echo "make token-check   is the cktool token saved and working?"
	@echo "make collect       scrape SOURCE=$(SOURCE) into data/"
	@echo "make enrich        read banners with Claude, fill gaps (needs ANTHROPIC_API_KEY)"
	@echo "make review        show the newest collected file"
	@echo "make approve       approve every complete event in it"
	@echo "make push          write approved events to CloudKit development"
	@echo "make push-prod     write them to production (asks first)"
	@echo "make reconcile     compare CloudKit against the local ledger"
	@echo "make routine       collect + enrich + approve + push (development) for every source"
	@echo ""
	@echo "current FILE: $(FILE)"

venv:
	python3 -m venv .venv
	./.venv/bin/pip install --quiet --upgrade pip
	./.venv/bin/pip install --quiet -r requirements.txt
	@echo "venv ready"

test:
	$(PY) -m pytest tests -q

# Is the cktool token saved and does it reach our container?
token-check:
	@xcrun cktool query-records \
		--team-id RLZG42V7Y4 \
		--container-id iCloud.zacherlInvestmentsLLC.iWrestle \
		--environment development --database-type public \
		--record-type Event --limit 1 >/dev/null 2>/tmp/cktool-check.err \
		&& echo "token OK: reached the development database" \
		|| (echo "token NOT working:"; cat /tmp/cktool-check.err | head -3)

collect:
	$(PY) bin/collect.py --source $(SOURCE)

# Re-run the parser against the saved page: no network, no geocoding.
collect-offline:
	$(PY) bin/collect.py --source $(SOURCE) \
		--from-fixture fixtures/$(SOURCE)-index.html --skip-geocode

enrich:
	$(PY) bin/enrich.py $(FILE)

enrich-dry:
	$(PY) bin/enrich.py $(FILE) --dry-run

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

# The unattended chain. Development only: production is always a person.
# enrich exit code 2 means no API key; the chain continues without it.
routine:
	@set -e; for src in pywrestling flowrestling; do \
		f=data/events.$$src.$(DATE).json; \
		echo "== $$src"; \
		$(PY) bin/collect.py --source $$src --out $$f; \
		$(PY) bin/enrich.py $$f || [ $$? -eq 2 ]; \
		$(PY) bin/review.py $$f --approve-all; \
		$(PY) bin/push.py $$f; \
	done; \
	$(PY) bin/reconcile.py

clean:
	rm -rf data/events.*.json data/assets data/enrich-cache.json .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +

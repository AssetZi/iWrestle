# iWrestle events pipeline. Run these from the pipeline/ directory.
PY := ./.venv/bin/python
SOURCE ?= pywrestling
DATE := $(shell date +%Y%m%d)
# The newest collected file for SOURCE. Override with FILE=path.
FILE ?= $(shell ls -t data/events.$(SOURCE).*.json 2>/dev/null | head -1)

.PHONY: help venv test exclude token-check token-check-cktool collect collect-offline enrich enrich-dry review approve push push-dry push-replace push-prod promote reconcile routine clean

help:
	@echo "make venv          create .venv and install pinned deps"
	@echo "make test          offline parser and mapping tests"
	@echo "make token-check   is the cktool token saved and working?"
	@echo "make collect       scrape SOURCE=$(SOURCE) into data/"
	@echo "make enrich        read banners with Claude, fill gaps (needs ANTHROPIC_API_KEY)"
	@echo "make review        show the newest collected file (add ARGS=\"--flagged --state PA\")"
	@echo "make approve       approve every complete event in it"
	@echo "make push          write approved events to CloudKit development"
	@echo "make push-replace  also re-push events whose content changed"
	@echo "make push-prod     write them to production (asks first)"
	@echo "make promote       push-prod for the newest file of every source"
	@echo "make reconcile     compare CloudKit against the local ledger"
	@echo "make exclude KEY=\"name or key\" REASON=\"why\"   remove an event for good"
	@echo "make routine       collect + enrich + approve + push (development) for every source"
	@echo ""
	@echo "current SOURCE: $(SOURCE)   FILE: $(FILE)"

venv:
	python3 -m venv .venv
	./.venv/bin/pip install --quiet --upgrade pip
	./.venv/bin/pip install --quiet -r requirements.txt
	@echo "venv ready"

test:
	$(PY) -m pytest tests -q

# Can we reach the container? Uses the server-to-server key when one is
# configured, else the cktool user token.
token-check:
	@$(PY) bin/keycheck.py
	@$(PY) -c "from iwpipe.config import CLOUDKIT_KEY_ID; import sys; sys.exit(0 if CLOUDKIT_KEY_ID else 1)" \
	  && exit 0 || $(MAKE) --no-print-directory token-check-cktool

token-check-cktool:
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
	$(PY) bin/review.py $(FILE) $(ARGS)

approve:
	$(PY) bin/review.py $(FILE) --approve-all

push:
	$(PY) bin/push.py $(FILE)

push-dry:
	$(PY) bin/push.py $(FILE) --dry-run

# Re-push events already in development whose content changed since.
push-replace:
	$(PY) bin/push.py $(FILE) --replace

push-prod:
	$(PY) bin/push.py $(FILE) --production --replace

# Publish the newest file of every source to production, one confirmation
# each. Answering n at a prompt skips that source and moves on.
promote:
	@for src in pywrestling flowrestling trackwrestling; do \
		f=$$(ls -t data/events.$$src.*.json 2>/dev/null | head -1); \
		if [ -z "$$f" ]; then echo "== $$src: nothing collected"; continue; fi; \
		echo "== $$src ($$f)"; \
		$(PY) bin/push.py $$f --production --replace || true; \
	done

# Take an event out of the directory: deletes it everywhere and keeps it out.
exclude:
	$(PY) bin/exclude.py "$(KEY)" --reason "$(if $(REASON),$(REASON),removed by hand)"

reconcile:
	$(PY) bin/reconcile.py

# The unattended chain. Development only: production is always a person.
# enrich exit code 2 means no API key; the chain continues without it.
# pywrestling goes first: it has the flyer and the contact, so when Flo lists
# the same PA tournament it is Flo's copy that is set aside as the duplicate.
routine:
	@set -e; for src in pywrestling flowrestling trackwrestling; do \
		f=data/events.$$src.$(DATE).json; \
		echo "== $$src"; \
		$(PY) bin/collect.py --source $$src --out $$f; \
		$(PY) bin/enrich.py $$f || [ $$? -eq 2 ]; \
		$(PY) bin/review.py $$f --approve-all; \
		$(PY) bin/push.py $$f --replace; \
	done; \
	$(PY) bin/reconcile.py

clean:
	rm -rf data/events.*.json data/assets data/enrich-cache.json .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +

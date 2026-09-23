# iWrestle events pipeline. Run these from the pipeline/ directory.
PY := ./.venv/bin/python
SOURCE ?= pywrestling
DATE := $(shell date +%Y%m%d)
# The newest collected file for SOURCE. Override with FILE=path.
FILE ?= $(shell ls -t data/events.$(SOURCE).*.json 2>/dev/null | head -1)
# A collected file older than this is stale; promote refuses it unless FORCE=1.
STALE_DAYS ?= 10

.PHONY: help venv test enrich-eval exclude token-check token-check-cktool collect collect-offline enrich enrich-dry review approve push push-dry push-replace push-prod promote reconcile routine clean clean-assets

help:
	@echo "make venv          create .venv and install pinned deps"
	@echo "make test          offline parser and mapping tests"
	@echo "make enrich-eval   score the enrich prompt against tests/evals/enrich (costs about a dollar)"
	@echo "make token-check   are the server-to-server keys accepted?"
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
	@echo "make clean-assets  delete rendered logos and flyers (the next push re-sends every event)"
	@echo ""
	@echo "current SOURCE: $(SOURCE)   FILE: $(FILE)"

venv:
	python3 -m venv .venv
	./.venv/bin/pip install --quiet --upgrade pip
	./.venv/bin/pip install --quiet -r requirements.txt
	@echo "venv ready"

test:
	$(PY) -m pytest tests -q

# Live calls to the model: run after a PROMPT_VERSION bump, not on every test.
enrich-eval:
	$(PY) bin/enrich_eval.py $(ARGS)

# Can we reach both environments with the server-to-server key?
token-check:
	@$(PY) bin/keycheck.py

# The cktool user token is only needed for schema work; this says whether one is saved.
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

# Re-push events already in development whose content changed.
push-replace:
	$(PY) bin/push.py $(FILE) --replace

push-prod:
	$(PY) bin/push.py $(FILE) --production --replace

# Publish the newest file of every source to production, one confirmation
# each. Answering n at a prompt skips that source and moves on. A file
# older than STALE_DAYS is skipped (a collect that failed leaves last
# week's file as the newest); FORCE=1 pushes it anyway.
promote:
	@status=0; for src in pywrestling flowrestling trackwrestling; do \
		f=$$(ls -t data/events.$$src.*.json 2>/dev/null | head -1); \
		if [ -z "$$f" ]; then echo "== $$src: nothing collected"; continue; fi; \
		if [ -z "$(FORCE)" ] && [ -z "$$(find $$f -mtime -$(STALE_DAYS))" ]; then \
			echo "== $$src: $$f is older than $(STALE_DAYS) days; run make collect SOURCE=$$src first, or FORCE=1"; \
			status=1; continue; fi; \
		echo "== $$src ($$f)"; \
		$(PY) bin/push.py $$f --production --replace || status=1; \
	done; exit $$status

# Take an event out of the directory: deletes it everywhere and keeps it out.
exclude:
	$(PY) bin/exclude.py "$(KEY)" --reason "$(if $(REASON),$(REASON),removed by hand)"

reconcile:
	$(PY) bin/reconcile.py

# The unattended chain. Development only: production is always a person.
# --yes answers the mass-replace question: development is the sandbox and
# the only cost of re-pushing it is time. Production keeps every prompt.
# enrich exit code 2 means enrichment is unavailable (no key, rejected
# key); the chain continues without it. A push that reports failed events
# does not stop the other sources, but the routine exits 1 at the end so
# the report says so.
# pywrestling goes first: it has the flyer and the contact, so when Flo lists
# the same PA tournament it is Flo's copy that is set aside as the duplicate.
routine:
	@status=0; for src in pywrestling flowrestling trackwrestling; do \
		f=data/events.$$src.$(DATE).json; \
		echo "== $$src"; \
		$(PY) bin/collect.py --source $$src --out $$f || { status=1; continue; }; \
		$(PY) bin/enrich.py $$f || [ $$? -eq 2 ] || status=1; \
		$(PY) bin/review.py $$f --approve-all || { status=1; continue; }; \
		$(PY) bin/push.py $$f --replace --yes || status=1; \
	done; \
	$(PY) bin/reconcile.py || status=1; \
	exit $$status

# Rendered assets are kept on purpose: their bytes are part of the content
# hash, so deleting them makes the next push --replace re-send every event.
clean:
	rm -rf data/events.*.json data/enrich-cache.json .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +

clean-assets:
	@echo "This deletes every rendered logo and flyer; the next push --replace re-sends all events."
	@read -p "Type yes to continue: " a && [ "$$a" = "yes" ] && rm -rf data/assets || echo "kept"

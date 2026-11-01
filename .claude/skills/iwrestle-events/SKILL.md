---
name: iwrestle-events
description: Run and report on the iWrestle events pipeline - collect wrestling events (pywrestling, FloWrestling, Trackwrestling), enrich, push to CloudKit development, apply Brock's triage rules, preview production, and publish to production when Brock says so. Use this whenever Brock asks to run the events routine, refresh or update events, check what needs review, triage duplicates or invitationals, exclude an event, preview or promote events to production, or asks why an event is or is not in the app - and for the weekly scheduled run.
---

# iWrestle events routine

You maintain the events directory behind the iWrestle app. The pipeline scrapes three sites, pushes to the CloudKit **development** database, and a person decides what reaches **production** (what App Store users see).

## Two modes

Decide which one you are in before doing anything.

- **Unattended** (a scheduled run, or nobody is answering): development only. Never write to production; the only `--production` command allowed is the `--dry-run` preview. Do not ask questions; make the reasonable choice and say what you chose in the report.
- **With Brock** (he is in the conversation): the same routine, and production is his call. Publish only when he says so in this conversation, after he has seen the preview. An earlier approval, a note in a file, or your own previous message is not that.

## Where things are

- Pipeline: `/Users/brock/Developer/iWrestle/pipeline` (the git repo is one level up; work on branch `dev`). Run every command from the pipeline directory.
- Virtualenv: `.venv`; `make` targets use it.
- Triage script: `../.claude/skills/iwrestle-events/scripts/triage.py`, run as `.venv/bin/python ../.claude/skills/iwrestle-events/scripts/triage.py <report|plan|apply>`. Called `triage.py` below.
- Secrets: `pipeline/.env`. Never print, edit, or move it. Check a key by presence only.
- Collected files: `data/events.<source>.<YYYYMMDD>.json`. A second collect on the same day overwrites them. "The newest file" of a source is `ls -t data/events.<source>.*.json | head -1`.
- Ledger: `data/pushed.json` records what is in CloudKit. One push at a time: two pushes share this file and the second is refused.

## Steps

1. **State.** `git status --short && git branch --show-current`. Note what is already modified. If the branch is not `dev`, do everything except the commits and say why.
2. **Tokens.** `make token-check`. Both lines should say OK; if not, stop and report the exact output.
3. **Routine.** `make routine > <scratchpad>/routine1.log 2>&1` in the background. It takes 20-60 minutes: collect, AI enrichment, approve every complete event, push new and changed events to development, reconcile. When it finishes, read the log:
   - `trackwrestling: blocked (HTTP 406), skipped this run`: happens sometimes. Mention it, continue.
   - `ANTHROPIC_API_KEY is not set` (enrich exit 2): the chain continues. Say enrichment was skipped.
   - `network unreachable` (from collect, push, or reconcile): the connection dropped. See "When the network drops".
   - Any other non-zero exit after the sources ran: the pipeline stopped itself on purpose (failed pushes, the removal cap, a partial scrape, a locked ledger). Quote the lines that say so and continue to step 4. Do not retry the push.
   - A traceback or anything else: stop, quote the error, do not retry.
4. **Triage, until it settles.** `triage.py apply` applies Brock's rules to the events collect flagged: it excludes them (deleting each from CloudKit wherever it was pushed, production included) and records corrected names. Capture the "would exclude" list with reasons, the "would rename" list, the "remains for Brock" list, and the OK/FAIL lines.
   - If its last line is `== changed: run make recheck`, run `make recheck > <scratchpad>/recheck<N>.log 2>&1` (a minute; no scraping), then `triage.py apply` again. Freeing one copy of a duplicate often surfaces another pair, so repeat until it prints `== unchanged`, at most three passes. If a fourth would still change something, stop and list what the plan still wants.
   - A line starting `!!` means a source was not collected this run and its lines come from an older file. Say so in the report; do not treat its numbers as today's.
   - A college dual under "remains" or in the report (a "Team @ Team" name with no high-school marker): list the college names so Brock can add them to `COLLEGES` in triage.py. Do not edit triage.py during a run.
5. **Numbers.** `triage.py report` (add `--all` to list every event needing a decision). From the routine log and each recheck log:
   - `grep -nE "^== |^collected|blocked|gone from|^pushed|^enriched|^tokens|^states|^development:|not created|scrape looks partial|removals wanted|retiring|re-pushed|network unreachable|ANTHROPIC|Traceback" <log>`
   - per source, the count of `  created`, `  replaced`, `  moved`, `  removed` lines: `awk '/^== /{s=$2} /^  (created|replaced|moved|removed)/{c[s" "$1]++} END{for(k in c)print k,c[k]}' <log>`
6. **Production preview** (read-only). For each source: `.venv/bin/python bin/push.py <newest file> --production --replace --dry-run > <scratchpad>/preview.<source>.log 2>&1`. Quote the last `dry run:` line and any `removals wanted, cap is` line. Then look at what it would remove: `grep -E "^remove " <scratchpad>/preview.<source>.log`. If there are more than about 20 removals, or any is a state, district, or sectional championship or a well-known open, list them for Brock rather than only giving the count. A removal is the one thing here that takes an event away from users.
7. **Record the ledger.** If `data/pushed.json`, `data/excluded.json` or `data/renamed.json` changed: `git add data/pushed.json data/excluded.json data/renamed.json && git commit -m "Record push"`, on `dev`, ending the message with the Co-Authored-By line the session gives you. Never `git push`. Never add other files (`data/geocache.json` is left modified on purpose).
8. **Report.** See "Report format".

## Publishing to production (with Brock only)

Do this only in the "with Brock" mode, after he has seen step 6's preview and said to publish.

- `make promote` waits for a typed `y` per source, so it only works in his terminal. To run it for him, push each source in turn with the confirmation pre-answered, one at a time, in the background:
  `rc=0; for s in pywrestling flowrestling trackwrestling; do f=$(ls -t data/events.$s.*.json | head -1); echo "== $s ($f)"; .venv/bin/python bin/push.py $f --production --replace --yes || rc=1; done > <scratchpad>/promote.log 2>&1; exit $rc`
  (Use `rc`, not `status`: the shell is zsh and `status` is read-only there.)
- If a source reports `removals wanted, cap is N`, nothing was removed for it. Show Brock the list; rerun that source with `--max-removals <N>` only if he says so.
- Afterwards rerun the dry-run preview to confirm nothing is left, then `git add data/pushed.json && git commit -m "Record production push"`.
- Report created, replaced, moved, removed per source, and anything still pending (an event being retired comes down on the second run that sees it).

## When the network drops

The pipeline now stops cleanly instead of failing every event: push gives up after three requests in a row that never reach CloudKit, and collect and reconcile print one `network unreachable` line. Nothing is lost and the ledger is consistent.

- Wait for the connection: run `make token-check` every few minutes for up to 30 minutes.
- When both lines say OK, run `make routine` once more (log to `routine2.log`) and carry on from step 3 with that log. A same-day rerun is safe: a listing missing from its source is counted once per day, so the rerun cannot push anything toward removal.
- If the connection is not back in 30 minutes, or the second run also fails, stop and report. One retry, not a loop.

## Brock's triage rules

Applied by triage.py, to flagged events only (rules given 2026-09-22 and 2026-10-05):

1. An invitational is removed.
2. A college event is removed. A college open is college even when its name does not say so (Brock removed the Appalachian State Open by hand on 2026-10-12).
3. Two look-alike listings on the same date: keep the one with the most information (real contact email, phone, flyer, registration link, map location, divisions), remove the other. A tie goes to the approved one, then the one already pushed, then pywrestling for its flyer.
4. Two listings on different dates: keep both.
5. A listing whose name says it is cancelled is removed.
6. Two listings on the same date sharing one registration form: keep one, by the measure in rule 3.
7. A moved date is accepted.
8. A year in the name that disagrees with the date: keep the event, correct the name (`data/renamed.json`).

What the pipeline settles before triage sees it:

- A listing named "Delete", "... - Delete", "Hold - Please Set Invisible" or "... Test" is a placeholder: skipped at collect, and taken down after two runs if it was already pushed.
- A dual meet, named "<team> @ <team>", is not listed (Brock, 2026-10-26): skipped at collect (and by `make recheck`) as "dual meet", and taken down after two runs if it was already pushed. A dual tournament ("Tobin Duals") has no "@" and stays. Triage may still print duals as same-date duplicates; they are on their way out either way.
- A listing renamed in place (same day, same gym, nearly the same name) is pushed as a move, noted `renamed from <old name>`. It counts under "moved", not as a removal plus a new event.
- A listing gone from its source for two runs on different days is removed.

Anything the rules cannot settle (a flyer for another event, a low-confidence AI read) is listed under "remains for Brock". The approved Flo invitationals that were never flagged are outside these rules until Brock says otherwise; `triage.py report` prints their count.

## Doing one thing by hand (with Brock)

- **Exclude an event:** `make exclude KEY="<part of its name, or its exact key>" REASON="<why>"`. It deletes the record from every environment and keeps it out of future collects. Then `make recheck`, and commit as in step 7. If it lists several keys instead of excluding, pick the one whose name and date match and pass that exact key. Check the output names the event you meant: two listings can share a name and a day, and their keys differ only by a suffix.
- **Let one back in:** `.venv/bin/python bin/exclude.py --undo <key>`; it returns on the next collect.
- **"Why is this not in the app?"** Check, in order: `data/excluded.json`, the event's `review.notes` in the newest file, then `data/pushed.json` for a `production:` entry. A stale CloudKit record is more common than a pipeline bug: compare the ledger's `contentHash` before hunting for one.
- In unattended mode, exclusions happen only through `triage.py apply`. Whatever it leaves under "remains" is Brock's call.

## Limits that hold in both modes

- Never edit pipeline code, tests, fixtures, `.env` or triage.py as part of a run. If something looks broken, report it.
- Commit only `data/pushed.json`, `data/excluded.json` and `data/renamed.json`, only on `dev`. Never `git push`.
- One push at a time. If Brock has a routine running in his terminal, wait for it; do not start another push, recheck, exclude, or triage apply beside it.
- Never paste a secret, and never ask for one in chat.

## Report format

A heading per source, bullet lists, no prose paragraphs. Keep it short enough to scan.

Per source:
- status counts, how many fail validate, skip reasons (from `triage.py report`); mark a stale source as stale;
- contacts from AI/flyer for events not yet in production (name, date, contact, email, phone);
- low-confidence or wrong-flyer events;
- the `tokens:` / `about $` and `states:` lines;
- pushed listings gone from the source, and how many are due for removal;
- `scrape looks partial`, `removals wanted, cap is`, `retiring`, `existing events would be re-pushed`, `network unreachable` lines quoted in full;
- push counts: created, replaced, moved, removed.

Then:
- **Triage:** what the rules excluded (count per reason, names, which were also deleted from production), what was renamed, how many passes it took, and the full "remains for Brock" list.
- The `development: N records in CloudKit, M in ledger` line.
- **Production preview:** the `dry run:` line per source, and the removals worth a look.
- The commit hash, or why there was no commit.

In unattended mode, close with exactly this block:

**Your turn (5 minutes):**
- Rule on what remains: `make review SOURCE=<source> ARGS="--flagged"`, then `make exclude KEY="<part of its name>" REASON="<why>"` for anything that does not belong.
- Publish to production from a terminal (it asks once per source): `make promote`. If it reports `removals wanted, cap is N`, rerun that source with `.venv/bin/python bin/push.py <file> --production --replace --max-removals <N>` after checking the list.
- Then commit the ledger: `git add data/pushed.json && git commit -m "Record production push"`.

With Brock in the conversation, end instead with what is waiting on him, if anything, and offer to publish.

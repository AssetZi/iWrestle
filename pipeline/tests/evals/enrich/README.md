# Enrich prompt eval

One directory per case: the organizer's `banner.jpg`, their `flyer.pdf` when
they posted one, the event as collect sees it before enrichment
(`event.json`), and the answers a person checked (`expected.json`).

Run `make enrich-eval` after every `PROMPT_VERSION` bump in
`iwpipe/enrich.py`. It calls the model live (about a dollar for the set) and
fails under 80% agreement. `make enrich-eval ARGS=--list` shows the set
without calling anything.

To add a case, copy the two files out of `data/assets/<key>/` (the flyer is
`source-flyer.pdf` there), write `event.json` from the collected file with
the AI-filled fields blanked, and put only facts a person verified in
`expected.json`; leave a field out rather than guess.

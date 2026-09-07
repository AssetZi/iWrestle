# iWrestle events pipeline

Collects wrestling events from public listings and writes them into the
app's CloudKit public database, so events do not have to be typed in by hand.

Three stages, deliberately separated by a human gate:

```
collect  →  enrich  →  review  →  push
scrape      Claude      you edit    cktool writes
to JSON     reads the   the JSON    to CloudKit
            banner
```

Nothing reaches CloudKit until a person marks an event `approved`. The
database is public and every record is visible to every user of the app.

## One-time setup

```bash
cd pipeline
make venv
cp .env.example .env      # then edit it
```

Fill in `.env`:

| Key | Why it matters |
| --- | --- |
| `ADMIN_RECORD_NAME` | Must equal `admin` in `iWrestle/Models/Constants.swift`. Pushed events carry it as their `userID`, which is what makes them appear under Settings → My events and stay editable in the app. |
| `DEFAULT_CONTACT_EMAIL` | Shown on events whose source lists no contact and whose banner prints none. Leave the `example.com` placeholder and every such event is flagged in review. Phone is optional and never invented. |
| `ANTHROPIC_API_KEY` | Lets `make enrich` read banner images with Claude. Create one at console.anthropic.com → Settings → API keys. Without it the enrich step is skipped and reported. |
| `NOMINATIM_EMAIL` | OpenStreetMap asks geocoding clients to identify themselves. |

### CloudKit access

There are two ways to write to CloudKit. **Prefer the server-to-server key**:
it never expires, which is what lets the scheduled routine run unattended.

**Server-to-server key (recommended).** The private key lives in
`pipeline/secrets/cloudkit-s2s.pem` (gitignored, mode 600). To create one:

```bash
openssl ecparam -name prime256v1 -genkey -noout -out secrets/cloudkit-s2s.pem
chmod 600 secrets/cloudkit-s2s.pem
openssl ec -in secrets/cloudkit-s2s.pem -pubout
```

Paste that public key into CloudKit Console -> Tokens -> Server-to-Server
Keys, and put the Key ID it returns into `.env` as `CLOUDKIT_KEY_ID`. The
pipeline then signs its own requests (`iwpipe/ckws.py`) and needs neither
Xcode nor a browser login. Server-to-server keys reach the public database
only, which is the only one iWrestle uses.

**cktool user token (fallback).** Used automatically when `CLOUDKIT_KEY_ID`
is empty. It is a browser session: it lapses after 30 minutes, or two weeks
if you tick "Keep me signed in" while generating it.

1. Open the [CloudKit Console](https://icloud.developer.apple.com/dashboard/), sign in, and go to **Settings → Tokens**.
2. Create a **user token** (create-record acts as you) and copy it.
3. Save it to the login keychain:

```bash
xcrun cktool save-token <token> --type user
```

Confirm either one took:

```bash
xcrun cktool query-records --team-id RLZG42V7Y4 --container-id iCloud.zacherlInvestmentsLLC.iWrestle --environment development --database-type public --record-type Event --limit 1
```

Some operations (schema export/import) need a **management token** instead;
save that one with `--type management`.

## Daily use

```bash
make collect SOURCE=pywrestling   # scrape into data/events.pywrestling.<date>.json
make enrich                       # Claude reads each banner and fills the gaps
make review                       # read the flags
make approve                      # or edit review.status by hand
make push                         # writes to the development environment
make push-prod                    # writes to production, asks first
```

`make routine` runs collect → enrich → approve → push (development) for every
source, then reconciles. It is what the scheduled task calls.

`make collect-offline` re-runs the parser against the saved page in
`fixtures/` with no network calls, which is how to iterate on parsing. It
skips each event's detail page, so registration links and banners only
appear on a real run.

### Development vs production

Debug builds run from Xcode read the **development** database. TestFlight and
App Store builds read **production**. Push to development first, look at the
events in the app, then push the same file to production.

## What each stage does

**collect** scrapes a source, then normalizes everything the app is strict
about: age groups and event types become the exact raw values from
`AgeGroupPicker.swift` and `EventTypePicker.swift`, dates become a single UTC
timestamp, addresses are geocoded, and a logo and flyer are produced for every
event. Anything doubtful becomes a note rather than a crash.

**enrich** sends each event's banner image, plus the organizer's flyer PDF
when one was found, to Claude (`claude-opus-5`, structured JSON output) and
fills only what is empty or defaulted: contact
name, email, phone, organizer website, divisions, start and weigh-in times,
entry fee, a registration URL if one is printed, and where the logo sits so
it can be cropped. Scraped values are never overwritten. Every AI-sourced
value carries an `AI: … from banner` note (shown in cyan by review) and the
overall confidence is recorded, so nothing from the model reaches CloudKit
without a person seeing it flagged. Results are cached per banner in
`data/enrich-cache.json`; a rerun costs nothing. A full pywrestling run is
roughly a dollar or two.

**review** prints one line per event with its flags and lets you set
`review.status` to `approved` or `skip`. Only approved events are pushed.

**push** builds a cktool fields file per event and runs `create-record`,
recording each success in `data/pushed.json` along with a hash of what was
sent. cktool cannot update a record, so `push --replace` (what the routine
uses) deletes and recreates an event whose content changed since it was
pushed; unchanged events are left alone. Plain `push` never touches an
existing record.

**reconcile** lists what is actually in CloudKit and can delete a record the
pipeline created, by its natural key.

## Required fields

`Event.init?(safeRecord:)` in `iWrestle/Models/Event.swift` returns nil when a
record is missing its logo, flyer, location, age groups, or any of the four
contact fields. Such a record is dropped from every fetch, so it exists in the
database but never appears in the app. The pipeline therefore guarantees all
of them:

- **Logo**: cropped from the banner when Claude locates one there, else from
  the flyer PDF's first page, else a source logo URL, else a slate-and-gold
  monogram tile matching the app's own fallback.
- **Flyer**: the source's real PDF if it has one; else the organizer's banner
  graphic laid onto a page with the essentials and links under it; else a
  one-page PDF rendered from the event's text. Every link on a flyer is a PDF
  link annotation, so it is tappable in the app's QuickLook viewer.
- **Contact**: the email and phone printed on the organizer's flyer PDF
  when there is one, else what enrich reads off the banner, else the
  organizer's name plus the default email from `.env`, flagged in review. Phone is optional: the app hides an empty row. It is still written
  as an empty string because the App Store build's decode guard needs the
  field to exist; the relaxed guard ships with the next app update.

## Duplicates

Each event gets a natural key: `source:name-slug:YYYY-MM-DD`. Successful
pushes are recorded in `data/pushed.json`, which is committed to git. A later
collect marks anything already pushed as `skip`, so re-running a scraper does
not create duplicates. Development and production are tracked separately.

The same event listed by two different sources is not caught automatically.
Resolve those in review.

## Field shapes

cktool names `stringType`, `int64Type`, `timestampType`, `assetType` and
`assetListType` in its docs but not the location or reference encodings.
Both were confirmed against the development database on the first push and
are now the only shapes in `iwpipe/cktool.py`:

```json
"location": {"type": "locationType", "value": {"latitude": 41.3, "longitude": -74.8}}
"userID":   {"type": "referenceType", "value": {"recordName": "...", "action": "NONE"}}
```

## Sources

| Source | State | Notes |
| --- | --- | --- |
| FloWrestling | Working, national | The backbone. Flo owns Trackwrestling, and its `events/search` endpoint has no date window, so the union of a few broad queries enumerates the whole country's schedule twelve months ahead. Each event comes with coordinates (no geocoding) and its Flo information page; `GET /api/event-hub/{coreId}` adds the organizer's name and email, the street address, website and registration, cached in `data/flo-details.json` for 30 days. |
| Trackwrestling | Working, supplement | Slow and careful: the site returns 406 to browser-looking clients, and to everyone from an address that asks too often. One bare session, three seconds between requests, and a block turns into `trackwrestling: blocked, skipped this run` rather than a failure. Every row is looked up on Flo by name and day; when Flo has it, Flo's version wins. Track-only events link to their registration or to the same gateway the site's own Enter Event button opens, never the landing page. |
| pywrestling.com | Working | Static HTML, ~34 PA events. Blocks are found by content, not CSS class, because class names are generated. Divisions come from icon filenames. Each block carries a 2:1 banner graphic that feeds enrich (logo location). Every event has up to three pages: an info page (`slug-M-D.html`), a sign-up page (`slug-M-D-or.html`), and sometimes only the organizer's own site; the event link prefers them in that order and is never the site root. The organizer's real flyer PDF sits inside the JotForm on either page as a PDF Embedder widget, parsed out of the widget settings and downloaded. Email and phone are read off the PDF text, the PDF becomes the flyer, and it is attached to the enrich request. Two events sometimes share one form, so a PDF that names a different event is dropped and noted. Webmaster and form-owner addresses are excluded. Needs geocoding. |

### College-level events

Neither Flo nor Trackwrestling says what level an event is, so it is
inferred (`iwpipe/level.py`): a university or college venue, a name in the
open/invitational/duals family, and no youth marker anywhere. Those events
become `Open` and are skipped with the note `college-level event`. Set
`INCLUDE_COLLEGE=1` in `.env` to keep them.

### Scale

A national run collects several hundred events. The first one is slow
(one detail request per event, then one cktool create per event, roughly
30–60 minutes); later runs only touch new or changed events. `make review
ARGS="--flagged"` shows only the events that need a decision, and
`ARGS="--state PA"` narrows to one state.

### FloWrestling API

The public pages return 406 to scripts, but the API host does not:

```
POST https://prod-web-api.flowrestling.org/api/schedule/events/search
{"tz": "America/New_York", "query": "a", "limit": 100, "offset": 0}
GET  https://prod-web-api.flowrestling.org/api/event-hub/{coreId}
```

`events/search` needs a non-empty query and pages by `offset` against
`meta.total`; the plain `events` listing is stuck to about a week and
ignores its cursor, so it is only used by tests. Multi-day events are
returned once per day under the same id and are collapsed to one record.
Events with no logo of their own carry a FloWrestling-branded still (or a
Track governing-body badge), which is rejected in favor of the monogram.

### Overlapping sources

pywrestling and FloWrestling both list many of the same Pennsylvania
tournaments. Collect flags an event whose name and date match one already
pushed from a different source and marks it `skip`, so the first source in
wins and the second is surfaced for a decision rather than pushed blindly.

## Scheduling

A Claude desktop scheduled task named `iwrestle-events-routine` runs
`make routine` (pywrestling, FloWrestling, Trackwrestling) on the 1st and
15th at 8am and reports what it did: counts of
approved, incomplete and skipped events, which events got AI-sourced
contacts, possible duplicates across sources, the enrich cost line, and the
reconcile counts. It only ever writes to the **development** database.
Production is always `make push-prod`, run by a person after `make review`.

The task runs while the Claude desktop app is open; if the app was closed at
8am it runs at the next launch. `cktool` only exists on a Mac with Xcode, so
the push step cannot move to CI.

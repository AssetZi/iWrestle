# iWrestle events pipeline

Collects wrestling events from public listings and writes them into the
app's CloudKit public database, so events do not have to be typed in by hand.

Three stages, deliberately separated by a human gate:

```
collect  →  review  →  push
scrape      you edit    cktool writes
to JSON     the JSON    to CloudKit
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
| `DEFAULT_CONTACT_EMAIL` | Shown on events whose source lists no contact. Leave the `example.com` placeholder and every collected event is flagged in review. |
| `DEFAULT_CONTACT_PHONE` | Same. |
| `NOMINATIM_EMAIL` | OpenStreetMap asks geocoding clients to identify themselves. |

### CloudKit token

`cktool` needs a token, which only you can create:

1. Open the [CloudKit Console](https://icloud.developer.apple.com/dashboard/), sign in, and go to **Settings → Tokens**.
2. Create a **user token** (create-record acts as you) and copy it.
3. Save it to the login keychain:

```bash
xcrun cktool save-token <token> --type user
```

Confirm it took:

```bash
xcrun cktool query-records --team-id RLZG42V7Y4 --container-id iCloud.zacherlInvestmentsLLC.iWrestle --environment development --database-type public --record-type Event --limit 1
```

Some operations (schema export/import) need a **management token** instead;
save that one with `--type management`.

## Daily use

```bash
make collect SOURCE=pywrestling   # scrape into data/events.pywrestling.<date>.json
make review                       # read the flags
make approve                      # or edit review.status by hand
make push                         # writes to the development environment
make push-prod                    # writes to production, asks first
```

`make collect-offline` re-runs the parser against the saved page in
`fixtures/` with no network calls, which is how to iterate on parsing.

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

**review** prints one line per event with its flags and lets you set
`review.status` to `approved` or `skip`. Only approved events are pushed.

**push** builds a cktool fields file per event and runs `create-record`,
recording each success in `data/pushed.json`.

**reconcile** lists what is actually in CloudKit and can delete a record the
pipeline created, by its natural key.

## Required fields

`Event.init?(safeRecord:)` in `iWrestle/Models/Event.swift` returns nil when a
record is missing its logo, flyer, location, age groups, or any of the four
contact fields. Such a record is dropped from every fetch, so it exists in the
database but never appears in the app. The pipeline therefore guarantees all
of them:

- **Logo**: a source image if one exists, otherwise a slate-and-gold monogram
  tile matching the app's own fallback.
- **Flyer**: the source PDF if one exists, otherwise a one-page PDF rendered
  from the event's own text.
- **Contact**: the source contact if parseable, otherwise the organizer's name
  plus the defaults from `.env`, flagged in review.

## Duplicates

Each event gets a natural key: `source:name-slug:YYYY-MM-DD`. Successful
pushes are recorded in `data/pushed.json`, which is committed to git. A later
collect marks anything already pushed as `skip`, so re-running a scraper does
not create duplicates. Development and production are tracked separately.

The same event listed by two different sources is not caught automatically.
Resolve those in review.

## Field shapes

cktool documents `stringType`, `int64Type`, `timestampType`, `assetType` and
`assetListType` by name, but not how a location or a reference is encoded. Two
plausible encodings are implemented in `iwpipe/cktool.py`, and the first push
tries them in order, keeping whichever the server accepts. Once one succeeds,
make it the only one and delete the other.

## Sources

| Source | State | Notes |
| --- | --- | --- |
| pywrestling.com | Working | Static HTML. Blocks are found by content, not CSS class, because class names are generated. Divisions are read from icon filenames. |
| FloWrestling | Not built | Listing is partly JS rendered; an XHR endpoint exists behind a session cookie. |
| Trackwrestling | Not built | Initial HTML carries ~30 tournaments; search and paging need a headless browser. |
| USA Wrestling | Blocked | Event listings sit behind a login. |

## Scheduling

Manual for now. `cktool` only runs on macOS with Xcode installed, so an
unattended push has to run on this Mac. Collecting and reviewing could run
anywhere, but the push step cannot move to CI.

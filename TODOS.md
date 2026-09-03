# TODOS

## Add Event

### Validate contact email format

**What:** Check that the event contact email looks like an email, not just that it is non-empty.

**Why:** Non-emptiness is the only current check, so a single character passes. Organizers whose events publish with an unreachable contact email cannot be contacted about their own event.

**Context:** The check lives in `missingFields(data:logo:wantsImagesMade:)` in `iWrestle/Views/AddEvent/EventFormValidation.swift` (`.contactInfo` case). Add a format check and decide how strict to be — a permissive "has an @ and a dot after it" is usually the right call over a full RFC regex. The add screen already marks the empty email field with the danger border after a submit attempt, so a format failure can reuse `isInvalid` on that `FormTextField`.

**Effort:** S
**Priority:** P3
**Depends on:** None

## Testing

### Stand up a test target

**What:** Add an XCTest target to the project; cover `missingFields()` first.

**Why:** The repo has zero test files today (`git ls-files` confirms), so every change is verified by hand.

**Context:** `missingFields(data:logo:wantsImagesMade:)` in `iWrestle/Views/AddEvent/EventFormValidation.swift` is a pure function over plain values with no SwiftUI or CloudKit dependency — the cheapest possible first test. Table-drive it: one case per required field missing, one all-empty case asserting form order, one complete case asserting an empty result. `AddressParts` and `String.monogram` in `iWrestle/Utilities/EventFormatting.swift` are the next cheapest targets (pure string parsing that every list row depends on).

**Effort:** M
**Priority:** P3
**Depends on:** None

## Cleanup

### Retire or re-enable the dead `wantsImagesMade` flag

**What:** Decide the fate of the paid-logo flag and remove the unreachable code paths it leaves behind.

**Why:** The flag is permanently `false`, so two code paths can never execute and read as intentional to anyone new.

**Context:** The redesign removed the commented-out `CreateMyLogosToggle()` from `iWrestle/Views/AddEvent/AddEventScreen.swift`, so the flag is now a `@State` that is never set: the `wantsImagesMade ||` operand in the `.logo` check in `EventFormValidation.swift` is dead, and `StoreKitManager.purchaseListing(logoGen:)` always receives `false`. Settle this when the paid-logo product decision is made — if it ships, add the toggle back to the FILES section; if not, delete the flag, the operand, and the `event_with_logo_gen` product path.

**Effort:** S
**Priority:** P3
**Depends on:** Paid-logo product decision

## Redesign follow-ups

### Ship a real event share link

**What:** Give `EventDetailView`'s share button a URL (universal link or `iwrestle://event/<recordName>`) that opens the event in the app.

**Why:** The redesign's share action currently sends the event's essentials as text (name, date, address, registration link) because no public event URL exists. A link is what the design intends ("Event link copied") and what recipients expect.

**Context:** `iWrestle/Views/Components/EventDetailView.swift` (`shareText`). Registering a URL scheme needs `CFBundleURLTypes`, which has no `INFOPLIST_KEY_` build setting — add an `Info.plist` alongside the generated keys (`INFOPLIST_FILE` merges with `GENERATE_INFOPLIST_FILE`), then handle `onOpenURL` in `RootView` by fetching the record ID and pushing `AppRoute.eventDetail`.

**Effort:** M
**Priority:** P2
**Depends on:** None

### Dark launch screen

**What:** Make the generated launch screen ink-black instead of white.

**Why:** The app is forced dark; the white system launch screen flashes before the first frame.

**Context:** `UILaunchScreen` supports `UIColorName`, but only through an `Info.plist` entry (no `INFOPLIST_KEY_` equivalent) — pair with the share-link item above, which needs the same plist.

**Effort:** S
**Priority:** P3
**Depends on:** None

### Restyle the Terms / Privacy sheets

**What:** Move `TermsOfServiceView` and `PrivacyPolicyView` onto the Geist / Slate Sky Gold styles.

**Why:** They are the last two screens still on system fonts and `.thinMaterial` cards; they open from the add-event terms line.

**Context:** `iWrestle/Views/AddEvent/TermsOfServiceView.swift`, `iWrestle/Views/AddEvent/Privacy.swift`. Their `TermsCard` / `SectionHeader` / `BodyText` helpers are the only things to restyle.

**Effort:** S
**Priority:** P3
**Depends on:** None

# TODOS

## Add Event

### Surface CloudKit create-event failures

**What:** Stop `createEvent()` from dismissing the form when event creation fails, and show the user what happened.

**Why:** `createEvent()` calls `dismiss()` unconditionally, even when `ck.createEvent` returns nil — and it runs *after* the StoreKit purchase has already gone through. A paying user gets a closed form, no event, and no error message. They have lost money silently. A nil return from `ck.getPhotoURL(image:)` has the same shape: bare `return`, no message, the form just sits there.

**Context:** `iWrestle/Views/AddEvent/AddEventScreen.swift:180-189` and the identical copy in `AddEventAdmin.swift`. The fix is to keep the form open on failure, set an error, and offer a retry. Note there is **no existing scaffolding** for this: a `showRetry` flag used to exist but was never assigned `true` anywhere, so the "Retry" branch had never executed; it was deleted as dead code when the validation refactor landed. Design the retry UX deliberately — real error text, and a decision about whether a retry re-charges or reuses the completed transaction.

**Effort:** M
**Priority:** P1
**Depends on:** None

### Extract the duplicated add-event form

**What:** Merge the near-identical `AddEventScreen` and `AddEventScreenAdmin` view bodies into one component parameterized by submit behavior.

**Why:** Every fix to the add-event form currently has to be written twice, and the two copies can silently drift apart.

**Context:** `iWrestle/Views/AddEvent/AddEventScreen.swift` and `AddEventAdmin.swift`. The form bodies are duplicated; the screens differ only in the submit path — the admin screen has no StoreKit (no `storekit` state, no `.task { loadProducts() }`) and calls `createEvent()` directly. The validation rules were already lifted out into `EventFormValidation.swift`, so what remains duplicated is the view body. Parameterize on a submit closure.

**Effort:** M
**Priority:** P2
**Depends on:** None

### Validate contact email format

**What:** Check that the event contact email looks like an email, not just that it is non-empty.

**Why:** Non-emptiness is the only current check, so a single character passes. Organizers whose events publish with an unreachable contact email cannot be contacted about their own event.

**Context:** The check lives in `missingFields(data:logo:wantsImagesMade:)` in `iWrestle/Views/AddEvent/EventFormValidation.swift` (`.contactInfo` case). Add a format check and decide how strict to be — a permissive "has an @ and a dot after it" is usually the right call over a full RFC regex.

**Effort:** S
**Priority:** P3
**Depends on:** None

## Edit Event

### Fix the silent hang in edit-event save

**What:** Make `saveEvent()` reset loading state and surface an error on both of its failure paths.

**Why:** The save spinner can run forever with no message, and the user's edit is silently lost.

**Context:** `iWrestle/Views/Settings/Components/UserEventDetailView.swift:135-157`. Two distinct triggers, and the existing bug report only covered the first:
1. When the address changed but `location` is nil, line 140 bails via a bare `return`.
2. More likely in practice: the whole body runs inside `Task { }` with no `do`/`catch` around `try await ck.updateEvent(...)` at line 153. A CloudKit throw is swallowed by the unawaited task.

In both cases `ogEvent` never updates, `dismiss()` never fires, and **no path resets `isLoading`**. Wrap in `do`/`catch`, reset `isLoading` on every exit, and show the error.

**Effort:** S
**Priority:** P2
**Depends on:** None

## Testing

### Stand up a test target

**What:** Add an XCTest target to the project; cover `missingFields()` first.

**Why:** The repo has zero test files today (`git ls-files` confirms), so every change is verified by hand.

**Context:** `missingFields(data:logo:wantsImagesMade:)` in `iWrestle/Views/AddEvent/EventFormValidation.swift` is a pure function over plain values with no SwiftUI or CloudKit dependency — the cheapest possible first test, and it covers both add screens at once since they share it. Table-drive it: one case per required field missing, one all-empty case asserting form order, one complete case asserting an empty result.

**Effort:** M
**Priority:** P3
**Depends on:** None

## Cleanup

### Retire or re-enable the dead `wantsImagesMade` flag

**What:** Decide the fate of the paid-logo flag and remove the unreachable code paths it leaves behind.

**Why:** The flag is permanently `false`, so two code paths can never execute and read as intentional to anyone new.

**Context:** `CreateMyLogosToggle()` is its only setter and is commented out at `iWrestle/Views/AddEvent/AddEventScreen.swift:98` ("not gonna have this option in first iteration"). Consequences: the `wantsImagesMade ||` operand in the `.logo` check in `EventFormValidation.swift` is dead, and the `Group { if !wantsImagesMade { ... } }` wrapper around the logo picker always renders. The operand was deliberately carried over verbatim during the validation refactor so that change provably altered no behavior. Settle this when the paid-logo product decision is made — if it ships, wire the toggle; if not, delete both paths.

**Effort:** S
**Priority:** P3
**Depends on:** Paid-logo product decision

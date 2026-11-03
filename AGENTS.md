# Agent workflow

Pick the parts of this workflow that fit the task.

- Read-only reviews and investigations need no worktree, commit, or PR. If an investigation leads to edits, isolate those edits first.
- Code changes use isolation, the architecture rules, the checks, and evidence of the behavior changed. Capture a failure before fixing it.
- Small documentation edits use an isolated branch and a content check. No runtime evidence, no review loop.
- Ship when the task calls for a PR. A request for a plan, review, or local experiment does not imply publishing it.

## Workflow

1. **Isolate.** `/new-feature` before any edit. Branch from `origin/main`. Never build on `main`.
2. **Build.** `/code-structure` when adding a feature that shares mechanics with an existing one or when choosing what goes in a view, model, or service. Plain MV SwiftUI: views, `@Observable` models, one service per backend. Services live in `iWrestle/Managers/` and are named `*Manager` (CloudKitManager, StoreKitManager); add to that folder rather than starting a parallel one. GUARDRAILS.md (if present) wins over this file on conflicts.
3. **Prove.** Run the checks below. `/evidence-driven-testing` for any changed runtime behavior. Record the failure before the fix and the success after.
4. **Ship.** Open the PR with evidence that fits the change. `/sim-before-after` when a screenshot pair helps. `/review-loop` for code changes, cap 3. Stop at 5/5 with zero unresolved actionable findings, or at the cap, and report the real result. Present the PR URL.

Run `/unslop` over anything a person will read: commit messages, PR title and body, docs, code comments, the closing reply. Apply it to text you wrote or changed, not prose you didn't touch.

## Rules

- Never commit directly to `main`. Never force-push to `main`. Only `--force-with-lease`, only on your own branch.
- One worktree and one branch per task. Never touch another task's worktree or uncommitted work.
- Scope check before starting: `gh pr list`, `gh pr diff <n> --name-only`. Ask only when changes conflict in behavior or depend on unfinished work.
- Resolve `Package.resolved` conflicts by regenerating, never by hand.
- Worktrees do not isolate the simulator. Confirm the installed bundle is yours before trusting it.
- If a conflict can't be resolved confidently, stop and report.
- Do not merge the PR unless told to. Keep the worktree until the PR is merged or closed.
- The events pipeline is the one task that runs in the primary checkout, not a worktree: its venv, cache and secrets are gitignored there. Its ledger commits go on a `data/ledger-<date>` branch cut from `origin/main` and land by pull request. The `iwrestle-events` skill has the steps.

## Completing a task that ships

1. Keep changes limited to the task.
2. Run the checks below.
3. Assemble evidence into before/after pairs or test output pairs.
4. Commit with a clear message, rebase onto `origin/main`, rerun the checks.
5. `git push -u origin <branch>` (after a rebase of a pushed branch, `--force-with-lease`).
6. Open the PR. Body sections: What changed, How it was tested (every claim backed by evidence), Before / after, Risks and follow-ups. Run the title and body through `/unslop`.
7. `/review-loop` with cap 3.
8. End with the PR URL.

## Checks in this repo

- Build: `xcodebuild -scheme iWrestle -destination 'platform=iOS Simulator,name=iPhone 17,OS=26.0' build`
- Tests: `xcodebuild -scheme iWrestle -destination 'platform=iOS Simulator,name=iPhone 17,OS=26.0' test` (target: iWrestleTests)
- Lint: none yet. The repo has no `.swiftlint.yml`, and `swiftlint` with default rules reports hundreds of violations, so do not run it as a check. Add the config first, then add the command here.
- Whitespace: `git diff --check`
- Bundle ID for simulator evidence: `zacherlInvestmentsLLC.iWrestle`

The destination pins `OS=26.0` because a bare `name=iPhone 17` matches every installed iOS 26 and 27 runtime and xcodebuild silently takes the first. 26.0 is the deployment target, so checks run on the oldest OS the app supports. If that runtime is missing, install it or change both lines together.

Evidence goes under `.artifacts/` (gitignored). Monthly `/complexity-audit` stays separate from this workflow.

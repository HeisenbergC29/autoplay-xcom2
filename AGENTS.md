# Agent working agreement

Current user instructions take precedence. Read [docs/TEAM.pl.md](docs/TEAM.pl.md)
and [docs/PROJECT-STATE.pl.md](docs/PROJECT-STATE.pl.md) before changing this project.

## Roles and communication

- **LEAD** is the assistant maintaining the original project. It owns technical
  direction, integration review, merges and publication.
- **HELPER** is the external GPT-6 collaborator. It may independently research,
  implement, test and propose useful changes, including work from its own repo.
- **USER** compiles with the Windows WOTC SDK, runs game missions and supplies
  reports. Ideas from the user are welcome, but are not a prerequisite for work.
- Use GitHub issues and PR conversations as the durable handoff. Start comments
  with `LEAD:` or `HELPER:` when roles could be confused. A shared GitHub login
  does not make a helper comment a lead approval.
- At each session start, read current issues, comments and PRs. Do not assume
  another agent is continuously watching GitHub or automatically notified here.

## Working branches and ownership

- `main` is the common integration source. It is not a claim of a successful
  Windows build or gameplay validation.
- Claim an issue with role, intended files and the base commit before editing.
  Use `helper/<issue>-<topic>` or `lead/<issue>-<topic>` for focused work.
- A helper opens a draft PR early and can continue other independent tasks while
  waiting for review. Keep at most three active implementation PRs. Do not wait
  idle for permission to perform already authorized research or reversible work.
- Coordinate overlapping edits to the controller/planners in the issue. Rebase
  or merge current `main` into the work branch before requesting final review.
- HELPER does not push to `main`, merge its own PR, force-push shared branches,
  publish releases, or change project-wide scoring/acceptance policy unilaterally.
- LEAD records the reviewed head SHA and decision in the PR. If both agents use
  the same account, use a lead comment rather than attempting self-approval.
  A new head invalidates the previous merge decision until reviewed again.
- These are working rules. Do not claim branch protection is technically enabled
  without checking the repository settings.

## Importing the helper repository

1. Begin with an inventory issue/PR: source repository URL, branch/head SHA,
   common ancestor if any, and a feature-to-commit table compared with current
   `main` and the v16 baseline in PROJECT-STATE.
2. Classify each item: useful new behavior, already implemented, conflicting,
   superseded, or needing SDK/game evidence. Explain the useful ones.
3. Port all useful work as separate reviewable topics, not a wholesale v15 fork
   merge or copies over current files. Preserve v16 fixes and regression tests.
4. Preserve source attribution: `cherry-pick -x` where suitable, otherwise cite
   source URLs and commits in the PR. Resolve conflicts deliberately.
5. Adapt tests/docs to the final implementation. Report expected gameplay tests
   separately from tests actually run. Do not import unrelated assets/build output.

## Product invariants

- Target Steam XCOM 2 Collection on Windows running **War of the Chosen**, all
  official DLC, with this mod alone. One autoplay serves all mission types.
- Mission success for the project means native victory **and a known mission
  score > 0**. Preserve the native outcome separately. Zero/negative is not a
  successful attempt; missing/partial points cannot certify success.
- Native mission points exclude earlier ladder missions. Keep the zero-based
  `wotc_legacy_observed_v2` comparison and its partial marker; never invent initial
  bonuses, a maximum, or scoring changes to turn a failed benchmark green.
- No artificially granted AP/ammo outside normal legal ability effects, forced
  hits/victory, RNG lookahead, hidden contacts, or enemy current
  AP/ammo/cooldown/charge/private-intent inspection. Native bonus actions, free
  reloads and AP-granting abilities remain legitimate when available. SDK template knowledge
  and observations currently visible to the player are legitimate inputs.
- Keep runtime game-state/history reads observational. Do not move a live history
  unit temporarily to fake a shot preview. Label geometric forecasts as estimates.
- Preserve native legality, full-route hazards, collateral/objective protection,
  rescue/loot constraints, manual OFF/pause and mission/history cache boundaries.
- Do not remove safety checks to silence a stop. Reject/replan invalid proposals
  with bounded retries and useful diagnostics; genuine dispatch failures remain
  distinguishable. A false stock end-turn return alone is not rejection evidence.
- Failure of this planner does not establish that a scenario is impossible.

## Validation and evidence

- Public baseline command: `python -m unittest discover -s tests -p 'test_*.py' -v`.
  Optional private SDK/config tests skip when inputs are absent. Report pass/skip
  counts honestly; green public CI does not certify those skipped contracts.
- With legitimately available private inputs, use APX_SDK_SOURCE_ROOT,
  APX_GAME_CONFIG_ROOT, APX_SDK_CONFIG_ROOT and APX_GAME_DLC_ROOT as documented in
  CONTRIBUTING. Run `tools/check-sdk-references.py --sdk <SDK source root>` for UC
  changes. This checks references, not compilation or native behavior.
- Use existing meaningful regression checks appropriate to the change. Pure
  helper/source-contract tests do not replace Windows compilation or full missions.
- Keep compile/game checks `NOT RUN` until evidence is supplied by the user or a
  real capable environment. Name the exact commit, recording revision and scenario.
- SDK source and raw game/DLC INIs are private inputs, not repository contents.
  Publish derived metadata with relative provenance only. Keep raw supplied logs,
  saves, account paths and archives out of commits; share a suitable summary.
- Do not bump the runtime recording revision for documentation/CI-only changes.
  Update revision and diagnostics together when runtime behavior changes.

## Review handoff

An implementation PR states the issue, final behavior, evidence/source commits,
tests actually run (including skips), limits, game test scenario and remaining
questions. A helper marks it ready when reviewable. LEAD can merge source work
after review/CI while explicitly tracking outstanding Windows/game validation;
merging is not gameplay acceptance or a binary release.

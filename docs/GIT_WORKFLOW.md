# Git and Pull Request Workflow

## Goals

The repository should remain easy to audit, bisect, release, and hand between humans and coding agents. Git history is part of the project documentation.

The default rule is: **substantive work happens on a focused branch and is merged through a pull request.**

## Protected branch mindset

Treat `main` as production-quality history even before formal GitHub branch protection is configured.

Do not:

- develop features directly on `main`;
- force-push `main`;
- rewrite released history;
- merge known-failing code simply to “save progress”;
- put multiple unrelated initiatives into one PR;
- commit secrets, credentials, downloaded caches, or unapproved copyrighted source material.

The only direct-main exception should be unavoidable repository bootstrap/administrative work where no branch can yet exist, and it should be minimal.

## Starting a task

1. Read `AGENTS.md`, `ROADMAP.md`, `TODO.md`, and `CHANGELOG.md`.
2. Inspect current code/tests for the area.
3. Identify the roadmap milestone and TODO item.
4. Confirm the task is a coherent PR-sized slice.
5. Update local `main` from origin.
6. Create a branch from current `main`.

### Branch naming

Use lowercase, short, descriptive names:

```text
feat/deterministic-dice
feat/rules-source-manifest
fix/spatial-difficult-terrain
docs/rules-provenance
refactor/effect-pipeline
chore/governance-ci
test/combat-replay
```

Avoid:

```text
new-stuff
work
changes
agent-123
final-final
```

## Commits

Prefer Conventional Commit-style messages:

```text
feat(engine): add deterministic dice service
fix(spatial): include terrain cost in reachability
docs(rules): define SRD source allowlist
test(combat): add attack replay fixture
refactor(effects): split target and outcome phases
chore(ci): validate generated rules output
```

### Commit rules

- One logical concern per commit where practical.
- Keep code and the tests that prove it close together.
- Do not mix formatting of unrelated files with a feature.
- Do not hide large generated-file changes in an unrelated commit.
- Do not commit temporary debug output.
- Do not commit editor caches/build artifacts.
- Do not commit secrets even temporarily.
- Avoid “WIP”, “stuff”, “fix”, or meaningless messages in final PR history.

A commit should leave the branch in a comprehensible state. It does not need to be independently releasable if the PR has multiple commits, but broken intermediate commits should be avoided where practical.

## Scope control

If implementation reveals additional work:

- add a TODO under the appropriate milestone;
- implement it now only if required for correctness of the current slice;
- otherwise defer it to a follow-up PR.

Avoid opportunistic rewrites that make review difficult.

A focused architectural refactor can be its own PR before/after a feature when that produces clearer history.

## Required files to consider in every substantive PR

Before opening a PR, explicitly decide whether each needs an update:

- implementation files;
- tests/fixtures;
- `TODO.md`;
- `CHANGELOG.md`;
- `ROADMAP.md` if milestone scope changed;
- architecture/rules docs;
- schema/version/migration docs;
- attribution/provenance data for rules/content changes.

“Not needed” is valid; forgetting to consider them is not.

## Pull request structure

PR title should be concise and specific, preferably matching Conventional Commit style where useful.

Suggested body:

```markdown
## Summary
- What changed
- Why it belongs in this milestone

## Architecture
- Boundaries affected
- Determinism/state/save implications

## Testing
- Commands/tests run
- Important fixtures/scenarios

## Rules/content provenance
- Source/version/license/checksum changes, or N/A

## Documentation and tracking
- TODO changes
- CHANGELOG changes
- Docs/ADR changes

## Follow-ups
- Deferred items, if any
```

## Before requesting review

Verify:

- branch is based on an appropriate recent `main`;
- diff contains no unrelated files;
- tests pass;
- formatting/lint/static checks pass;
- generated content is regenerated using documented tools;
- deterministic output checks pass where applicable;
- TODO is accurate;
- changelog is accurate;
- docs are accurate;
- no unlicensed/non-approved source material is present;
- no secrets/debug artifacts are present.

## Reviewing a PR

Review in this order:

1. **Scope:** Does it match the stated milestone/TODO?
2. **Architecture:** Does it preserve authoritative headless simulation and presentation separation?
3. **Correctness:** Are the rules/state transitions correct?
4. **Determinism:** Can outcomes/replays be reproduced?
5. **Data compatibility:** Are schemas/saves/events/content packs affected?
6. **Licensing/provenance:** Are imported materials approved and traceable?
7. **Tests:** Do they prove behavior and regressions?
8. **Performance/concurrency:** Is blocking I/O or unsafe shared state introduced?
9. **Security:** Are untrusted packs/imports/network/AI inputs validated?
10. **Documentation/tracking:** Do TODO/changelog/docs match reality?

Do not approve solely because CI is green.

## Merge policy

Prefer a clean history that keeps the repository easy to read.

Default recommendation:

- use **squash merge** for a normal feature/fix/docs PR when its intermediate commits are not independently valuable;
- use **rebase merge** when each commit is intentionally clean, logically valuable, and should remain visible;
- use merge commits only when preserving branch topology is specifically useful.

Before merging:

- confirm CI is green;
- resolve review threads;
- confirm the PR head did not unexpectedly change after review;
- confirm TODO/changelog/docs are current;
- confirm no known blocking follow-up is being hidden.

Never merge a PR simply to get it out of the queue when it has unresolved correctness/licensing/data-loss concerns.

## Handling failed CI

Fix the cause; do not weaken checks without documenting why the requirement changed.

When failure is flaky/infrastructure-related:

- record evidence;
- rerun only when appropriate;
- create a follow-up reliability issue/TODO if the flake is real;
- do not normalize recurring flakes as acceptable.

## Updating a branch

Prefer normal fast-forward/rebase practices that do not lose reviewed work.

For shared branches:

- avoid force-push unless necessary and explicitly safe;
- communicate if history must be rewritten;
- re-review materially changed diffs.

For agent-created branches, an agent must not force-update a branch containing work it has not fully inspected.

## Generated rules/content

For generated files:

- edit the generator/schema/source transform, not output by hand;
- regenerate;
- review generated diff;
- verify deterministic generation;
- commit generator and output together when the project intentionally tracks generated output;
- include source/version/checksum/provenance changes.

Large unexpected generated diffs should block merge until understood.

## Save/schema compatibility

Any PR changing:

- event payloads;
- command payloads;
- save snapshots;
- canonical entity schemas;
- stable IDs;
- content pack manifests;

must decide whether:

- change is backward compatible;
- migration is required;
- version number must increment;
- old fixtures need migration tests;
- release notes/changelog need a compatibility warning.

Never silently reinterpret old serialized data.

## Release workflow (to finalize before first release)

Expected direction:

1. `main` remains releasable.
2. Complete milestone exit criteria.
3. Run full test/conformance/replay suite.
4. Verify rules/content attribution and provenance.
5. Move `Unreleased` changelog entries into a versioned dated section.
6. Update version metadata consistently.
7. Create annotated/version tag according to final release policy.
8. Build release artifacts from the tagged commit.
9. Verify artifacts and licenses/credits.
10. Publish release notes from the changelog plus compatibility/migration details.

Semantic versioning is intended, but exact pre-1.0 and content-pack versioning rules should be captured in an ADR before the first tagged release.

## Hotfixes

Urgent fixes still use a branch and PR whenever possible:

```text
fix/<issue>
```

A hotfix must still include regression tests and changelog/compatibility updates where applicable. Urgency is not permission to bypass licensing, save safety, or deterministic correctness.

## Reverts

Prefer a clear Git revert over manually reconstructing the old state when undoing a merged change.

After a revert:

- explain why;
- update TODO/changelog if the feature is no longer present;
- add a follow-up task if the feature is expected to return;
- preserve any needed migration/data-safety handling.

## Agent-specific Git behavior

Agents with GitHub write access should:

- inspect before editing;
- branch before substantive work;
- keep commits/PRs focused;
- never merge unrelated open PRs as a side effect of another task;
- never delete branches/files they did not create without understanding ownership;
- report branch, PR, tests, TODO/changelog/docs changes at completion.

If an agent lacks enough context to safely mutate Git history, it should prefer creating a new focused commit/PR over destructive history operations.

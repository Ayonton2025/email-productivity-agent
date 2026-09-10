# Phase 9: Insights frontend tests

This phase follows the repository-specific Phase 9 in draft.docx, starting from Phase 8 commit `09d76e7` on branch `phase-9-insights-tests`.

## Requirement coverage

| Area | Required behavior | Evidence |
| --- | --- | --- |
| Dashboard | Header, five tab controls, switching, refresh, loading | Existing integration suite strengthened with explicit tab-control assertions; deferred refresh confirms loading and replacement data without losing the selected tab. |
| Dashboard failure handling | Safe failure and recovery | Initial failure recovery plus parameterized refresh failures for all five API methods; prior data and the selected tab remain available, internal error details stay out of the UI, and retry clears the alert. |
| Overview | Statistics, risk summary, opportunities | Direct tests verify all four summary totals, email totals, category/sentiment counts, category limit of three, recent-list limits of five, details, severity, value/probability, and risk/opportunity navigation. |
| Overview fallbacks | Empty/absent data | Absent analytics/relationships and an analytics object without statistics render safely; empty recent sections stay hidden and counts default to zero. |
| Risks | Empty state, list, severity, navigation | Tests cover multiple risks, description/type/impact/urgency/date, missing date, selected-record navigation, all four severity colors, uppercase severity, and unknown severity fallback. |
| Opportunities | Empty state, list, value/probability | Tests cover multiple entries, description/type, formatted value, probability, close date, selected-record navigation, and omitted unknown financial/date fields. All five known statuses plus an unknown status and hot/warm/cold temperatures are checked. |
| Deadlines | Empty state, rendering, overdue status | Tests verify description, date, type, owner, all priority colors, and past/exactly-now/future/missing deadlines using a fixed clock restored after every test. |
| Relationships | Companies, contacts, empty state, navigation | Tests verify independent empty sections, company domain/contact count, named and email-only contacts, avatar fallback, rounded/missing scores, all status colors, and company/contact navigation. |

The suite now contains six Insights test files, with 45 tests in total: Dashboard 9, Overview 3, Risks 7, Opportunities 12, Deadlines 9, Relationships 5. This adds 41 cases to the four Phase 8 integration tests. Parameterized cases are counted individually by Vitest.

Tests render the actual components and shared helpers. Only dashboard API, logger, and router boundaries are mocked; direct tab tests supply a navigation spy. They use synthetic data, make no live API calls, and assert visible behavior rather than snapshots. Dashboard mocks are reset between tests. Date display fixtures use local noon to avoid timezone-dependent calendar shifts; overdue comparisons use explicit UTC instants and a fixed clock.

## Validation (2026-09-10)

- Focused six-file Insights run: **45 passed**.
- Full frontend coverage run: **32 files, 156 tests passed**.
- Application coverage: **45.09% statements/lines, 58.64% branches, 40.05% functions**; all existing thresholds passed without changes.
- Each of the five tab components: **100% statements, lines, branches, and functions**.
- Shared insight presentation helpers: **100% statements, lines, branches, and functions**.
- Dashboard: **100% statements, lines, and functions; 90.9% branches**.
- ESLint with zero warnings allowed: passed.
- Typecheck: passed.
- Full frontend Prettier check: passed.
- Production Vite build: passed, with the existing empty utils chunk notice.
- Diff whitespace check: passed.

Coverage is execution evidence, not proof of all possible inputs or browser behavior. The tests run in jsdom; they do not verify a deployed backend, hosted Sentry delivery, or visual layout in a real browser.

## Scope and outstanding items

Only test files and this report changed. Production components, routes, APIs, dependencies, coverage thresholds, and CI workflows remain unchanged. Backend tests were not rerun for this test-only frontend phase.

The previously observed Phase 7 GitHub failures (frontend dependency audit and both fresh-clone jobs) remain unresolved, as does hosted Sentry delivery verification. This phase does not claim those checks passed. Phase 9 hosted CI remains to be verified after the push.

## Review checkpoint

Every repository-specific Phase 9 checklist item is covered. Implementation and local validation are complete. The user approved committing and pushing this phase.

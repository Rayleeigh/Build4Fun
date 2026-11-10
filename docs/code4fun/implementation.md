# Code4Fun implementation

Code4Fun is an independent local addon. Its [user guide](../../apps/code4fun/README.md)
covers launch commands, API responses, persistence, and limitations. The original
[plan](plan.md) records its product direction.

## Services and source

`compose.code4fun.yaml` builds two services. The workspace image includes Python,
Playwright, and Chromium. The API image contains only the standard-library Python
server. Both run as the code4fun user without Docker access. The workspace exposes
localhost ports 8090 (management UI) and 8091 (preview); the API listens internally
on 8092. Build4Fun's Dockerfile and default Compose workflow remain independent.

| Source | Responsibility |
| --- | --- |
| `apps/code4fun/workspace/server.py` | Management HTTP routes, persistence, preview snapshots, API proxy, and bounded check processes |
| `apps/code4fun/workspace/checks.py` | Six stages of browser behavior checks |
| `apps/code4fun/workspace/static/` | Instructions, editor, preview, drafts, and progress UI |
| `apps/code4fun/api/server.py` | OS identity, network addresses, and cgroup v2 measurements |
| `challenges/code/stages.json` | Lesson text, hints, and learner-facing requirements |
| `challenges/code/starter/` | Three initial apprentice files |
| `apps/code4fun/tests/` | Unit tests, isolated browser suite, reference solution, and container checks |

## Project persistence

One project lives in `/workspace/project.json` in a named Docker volume, or
`.workspace/code4fun/project.json` natively. Saves atomically replace that JSON
file and assign a new revision. Stale revisions fail with a conflict rather than
overwrite another save. This supports one server process per workspace, not
multiple replicas. Files are limited to three known names and 128 KiB each.

Browser drafts include the saved revision. Recovery never rebases an old draft
silently. Completion stores the timestamp and hash of the files that passed;
badges represent historical milestones. Checks save current edits first and
record progress only if the saved revision remains current. Reset replaces all
files and clears progress in a single save after browser confirmation.

`tutorial_seen` is stored with the project when the first-run walkthrough is
finished or skipped. This update does not change the file revision or discard
edits. Saves and resets preserve it. A header action can replay the walkthrough.
The course introduction uses four topic cards with isolated, trusted DOM examples:
HTML structure, CSS presentation, a JavaScript interaction, and an API metadata
request. The subsequent walkthrough uses a movable dialog and spotlight. Its
placement is calculated from each target's viewport rectangle and updated on
resize or scrolling. It restores the original file selection, mission-list state,
and scroll position when dismissed. Examples do not run or overwrite apprentice
source files.

Desktop panels share a bounded height and matching headers; flex children scroll
internally to prevent expanded hints or results from changing the outer frame.
Tablet and mobile layouts reflow the panels instead of squeezing three columns.
Mission selection lives in a collapsible list in the task panel and updates the
instructions without rerunning the preview or replacing editor contents.

The API reference dialog reads the prepared API metadata through a fixed
same-origin management endpoint, `/code4fun/api/reference`. It renders schema
fields, examples, and measurement notes as text, with retry feedback when the API
is unavailable. Raw `/api/info` remains available through the preview proxy.
First-time mission completion triggers a six-second toast with an animated timer;
hover and keyboard focus pause it, and historical completion suppresses repeats.

## Preview and checking boundary

Run creates an immutable in-memory snapshot with an unguessable URL, independent
of Save. Up to 32 snapshots are retained; snapshots expire after an hour or a
server restart. Only index.html, style.css, and script.js can be retrieved.

The preview listener has no management routes. Its `/api/` proxy forwards only
the five prepared GET endpoints to a configured API base URL with a timeout.
The API is not published directly to the host. Management writes require an exact
same-origin header, and both listeners accept only their configured loopback Host
names and ports. The preview iframe allows scripts and its own origin while
remaining cross-origin to the editor. CSP restricts assets and fetches to that
preview origin and blocks forms, nested frames, and external resources.

Checks run in a separate process with a fresh Chromium context, blocked service
workers, and route interception restricting network access to the exact snapshot
files and mocked API endpoints. Controlled responses vary values and simulate
HTTP errors, network errors, delayed responses, and null metrics. Only one check
runs at a time; a 60-second deadline kills the check process group on timeout.
This is browser isolation for trusted local teaching, not hostile-code hosting.

## Measurement semantics

The API reads cgroup v2 files directly. CPU uses the delta of `usage_usec` between
requests divided by elapsed time and effective CPU capacity. Capacity is the
smaller of the effective cpuset size and `cpu.max` quota/period. The first sample
and unsupported measurements are null. Memory comes from `memory.current` and
`memory.max`; it includes cache, and an unlimited limit is null. No fallback reads
host-wide /proc counters. Uptime starts with the API process.

The `/api/info` response describes types, units, null handling, source-file
availability, and refresh guidance. Native execution reports a native environment;
the Compose stack is the intended teaching deployment.

## Deployment scope

The implementation chooses local execution, a plain text editor, one project,
whole-project reset, and historical milestone tracking for the first version.
Central hosting, accounts, syntax highlighting, arbitrary files, automatic backup
import, and tamper-proof grading are future work. See the user guide for the
checks that can be run locally and in CI.

# Code4Fun

Build one **My Server Dashboard** project through six stages: HTML, CSS,
JavaScript, combined interactions, a first API call, and a live dashboard.
The workspace includes instructions, hints, a three-file editor, separate-origin
preview, saved progress, and browser checks. The prepared API reports its own
container environment, not the apprentice's physical computer.

## Run with Docker

From the repository root, with Docker Engine and Compose running:

```sh
docker compose -f compose.code4fun.yaml up --build -d --wait
```

Open http://localhost:8090. Port 8091 serves the isolated preview and API proxy.
The first build installs Chromium for behavior checks and can take a few minutes.
Build4Fun uses `compose.build4fun.yaml` and port 8080 independently.
The Code4Fun API is a second service, reachable only through the workspace's
preview proxy; it has no separately published host port.

Optional `C4F_HTTP_PORT` and `C4F_PREVIEW_PORT` settings change the two published
ports. Use distinct ports and open the workspace through localhost or 127.0.0.1.
Both services run as an unprivileged user with resource limits; neither mounts
the Docker socket or Build4Fun workspace.

```sh
docker compose -f compose.code4fun.yaml logs --tail 100
docker compose -f compose.code4fun.yaml stop
```

Projects persist in the `code4fun-workspace` named volume. Stop and ordinary
`down` preserve it; `down --volumes` deletes it. Back up the volume for durable
external recovery.

## Workspace

- Edit `index.html`, `style.css`, or `script.js`. The initial HTML links both supporting files.
- The preview renders on startup and updates automatically about 200 ms after edits to HTML, CSS, or JavaScript. Run preview refreshes it immediately. Edits and mission selection autosave after an 800 ms pause; Save project or Ctrl/⌘S saves immediately. All three files and the selected stage are stored atomically.
- Check my work saves first, then evaluates the selected stage in Chromium using controlled API data. Stage 6 also checks delayed responses, failures, null measurements, and periodic refresh.
- Open the collapsible Missions list in the left panel to switch tasks without changing the editor or preview. The completed count sits beside the progress bar. Switching stages preserves the project. Completion badges record previously passed checkpoints; they are learning history, not a claim that the current code still passes every earlier stage.
- The editor shows Unsaved changes, Saving…, and All changes saved. Autosave keeps typing responsive and retains edits made while an earlier save is running. Browser drafts can be recovered after refresh. Older drafts preserve save conflicts. Download a backup before reloading if a newer save exists.
- Download backup saves a JSON copy of all three files and the selected stage. It can be read and copied manually; automatic backup import is not implemented.
- Reset entire project asks for confirmation, replaces all three files with starter content, and clears all progress. Individual-stage resets are not offered.

On desktop, the Missions, Files, and Preview panels share the same header and
bottom edges. Long instructions, expanded hints, code, and check results scroll
inside their own sections. Smaller screens stack the panels.

The lesson panel specifies the element IDs and behaviors checked at each stage.
Checks accept different implementations; API checks change sample values to
reject hardcoded responses. Regular previews always use the live API.

Autosave uses the same revision checks as manual saving. A conflict pauses
autosave and preserves the draft: download a backup, then reload to resolve it.
Network or server errors show Not saved; use Save project to retry or continue
editing to schedule another attempt. If you close the tab before a pending save
finishes, browser draft recovery remains available on reopening.

## Editor indentation

The starter HTML uses two-space nesting; the editor inserts actual tab characters,
displayed at two-column tab stops. Its body includes a
visible placeholder message, so a new or reset project's preview is not blank.
Replace that message with your own dashboard; it does not satisfy the first
mission's heading, paragraph, or server-section checks. While the editable code
area has focus, Tab inserts a tab character or indents selected lines. Shift+Tab
outdents the current or selected lines, removing one leading tab or up to two
spaces for existing space-indented code. Outside the editor, both keys retain
normal browser focus navigation. Backspace in leading whitespace removes an
indentation step.

Enter preserves the current indentation and adds a level after an opening HTML
tag or a JavaScript/CSS block delimiter. Between matching opening and closing
tags or delimiters, it creates an indented blank line and places the closing part
on the following line. HTML void elements such as meta and link do not add a level.
Native undo is preserved where the browser supports undoable textarea insertion.

Press Escape, then Tab (or Shift+Tab) to move keyboard focus outside the editor.
Loading or saving a file does not reformat apprentice code. On startup, an
untouched older starter project is upgraded to the current visible starter only
when all three files exactly match a known older starter, the selected stage is the first,
and no missions have been completed. Matching empty browser drafts are discarded
only when the saved project is also an untouched current starter. Edited files,
other stages, completion history, and genuine drafts are preserved. New workspaces
and explicit resets use the current starter.

## Tutorial and completion feedback

On the first workspace visit, the tutorial presents four course cards: HTML,
CSS, JavaScript, and APIs. Next highlights each topic with a short explanation,
code sample, and rendered or interactive example. The JavaScript example responds
to clicks, and the API example requests the prepared API description. These
examples do not change apprentice files.

The following workspace tips move beside the control they describe, highlighting
mission selection, file tabs, Run, Save, checks, and the API reference. Their
position follows scrolling and resizing, with a compact layout on small screens.
Actions let you open a file, run the preview, and inspect the reference; the
original file selection and mission-list state are restored when the tour ends.
Use Tutorial in the header to replay it at any time.

Completing or skipping the tutorial is remembered in the workspace volume, so
container restarts, page reloads, and a project reset do not repeat it. A new
workspace receives the tutorial on its first visit. Draft recovery is resolved
before the tutorial opens.

The first successful check for each mission shows a six-second notification with
a duration bar along its bottom edge. Hovering over it or focusing it pauses the
timer. Rechecking an already completed mission does not show it again; completion
still appears in the mission list and check results. Resetting the entire project
clears mission completion, allowing those notifications for the new attempt.

## Prepared API

Open API reference in the workspace header for a formatted dialog with field
descriptions, sample responses, JavaScript and curl examples, and measurement
notes. The raw contract remains at http://localhost:8091/api/info. Trailing slashes are accepted for all five read-only GET endpoints:

| Endpoint | Response |
| --- | --- |
| `/api/info` | API contract and metric availability |
| `/api/username/` | `{"username":"code4fun"}` |
| `/api/hostname/` | `{"hostname":"code4fun-api"}` |
| `/api/ip` | `{"addresses":["172.20.0.3"]}` (actual addresses vary) |
| `/api/metrics` | `cpu_percent`, `memory_used_bytes`, `memory_limit_bytes`, `uptime_seconds` |

Measurements use Linux cgroup v2. Memory includes cache; an unlimited memory
limit is null. CPU is sampled between requests and normalized to the smaller
of effective cpuset size and CPU quota; the first sample is null. If accounting
files are unavailable, those measurements are null rather than host-wide values.
API uptime measures this API process. Refresh around every five seconds.
Unknown endpoints return 404 JSON; POST returns 405 JSON. Responses are not cached.

The API resolves addresses for the container hostname and excludes loopback and
unspecified addresses. It does not enumerate every possible network interface.
The workspace returns a 502 JSON error if the API cannot be reached.

## Run natively for development

Use two terminals from the repository root:

```sh
.venv/bin/python -m pip install -r apps/code4fun/workspace/requirements.txt
PLAYWRIGHT_BROWSERS_PATH=.venv/browsers .venv/bin/python -m playwright install chromium
.venv/bin/python apps/code4fun/api/server.py
```

```sh
PLAYWRIGHT_BROWSERS_PATH=.venv/browsers .venv/bin/python apps/code4fun/workspace/server.py
```

This stores work in `.workspace/code4fun/`. A native API reports its native process
environment; use the Docker stack for the intended container measurements.
Linux native installs may also require Playwright's `install --with-deps chromium`.

## Checks

```sh
.venv/bin/python -m unittest discover -s apps/code4fun/tests -v
PLAYWRIGHT_BROWSERS_PATH=.venv/browsers .venv/bin/python apps/code4fun/tests/ui_smoke.py
.venv/bin/python apps/code4fun/tests/container_smoke.py
```

The browser suite uses temporary files and ephemeral localhost ports. It checks
editing, saved state, draft recovery, all six stage solutions, negative cases,
and API isolation. Screenshots are written to `/tmp/code4fun-desktop.png` and
`/tmp/code4fun-mobile.png`. Container checks build an independently named stack,
exercise container measurements and browser checks, restart for persistence,
and remove only their own stack and volume. CI runs all three checks.

## Current boundaries

This is a trusted local learning workspace with one shared project per instance,
not a shared hosting service. There are no accounts, multiuser sessions, or
apprentice-written backends. The editor is plain text, without syntax highlighting
or arbitrary extra files. Stage checks are formative feedback, not tamper-proof
assessment.

The preview uses a different port/origin, an iframe sandbox, and a restrictive
content security policy. Check browsers block requests outside the snapshot and
mock API, and check processes have a 60-second limit. These controls are not a
hardened hostile-code hosting service. Close a looping preview by running corrected
code or reloading the workspace. Do not expose this setup as a public multiuser IDE.

See the [plan](../../docs/code4fun/plan.md),
[implementation guide](../../docs/code4fun/implementation.md), and
[repository architecture](../../docs/monorepo.md).

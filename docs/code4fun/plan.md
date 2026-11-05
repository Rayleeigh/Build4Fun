# Code4Fun implementation plan

Status: agreed product direction, before implementation. Code4Fun is a planned
addon; this document does not describe currently available functionality.

## Purpose and learner workflow

Code4Fun introduces application developer apprentices to frontend development.
They build one project, **My Server Dashboard**, which becomes progressively
more complex across six stages. They write real HTML, CSS, and JavaScript;
the backend API is prepared by us, not written by apprentices.

The workflow is: read the current goal, edit files, run the website, observe the
result, check the work, and use feedback or hints to improve it. Existing work
continues into each new stage. Earlier instructions remain accessible.

## Learning path

| Stage | Focus | Dashboard milestone |
| --- | --- | --- |
| 1 | Basic HTML | Create a title, introduction, and sections for server information. |
| 2 | HTML + CSS | Style the page with typography, spacing, colors, and information cards. |
| 3 | HTML + JavaScript | Add a button that changes text or reveals information. Existing CSS remains in place. |
| 4 | HTML + CSS + JavaScript | Combine styling and interaction, for example with a theme switcher. |
| 5 | Frontend calling a prepared API | Fetch and display the API container's hostname. |
| 6 | Frontend using additional API functionality | Show username, network addresses, and metrics; add refresh controls, periodic updates, loading states, and error handling. |

These milestones define the intended progression. Exact checkpoint wording,
selectors used by checks, and completion criteria must be specified before
implementing each stage. Stage 6 can have several small checkpoints rather
than introducing every behavior at once.

## Coding workspace

The proposed first workspace contains a challenge panel, file explorer, text
editor, website preview, and check results. Initial apprentice files are
`index.html`, `style.css`, and `script.js`.

Run refreshes the preview from the current edits. Save durably preserves the
project. Moving between stages must preserve apprentice code rather than
replace it with the next stage's starter files. Stage completion records
progress without blocking access to previous instructions.

Each stage provides a goal, small checkpoints, progressive hints, and a
Check my work action with specific feedback. Reset behavior must be clearly
scoped and confirmed before replacing apprentice files; the exact reset and
recovery design remains to be defined.

## Runtime architecture

Code4Fun has two services in the same Compose stack:

- The coding environment serves the workspace and apprentice website preview.
- The prepared API server reports its own container environment and live metrics.

The preview exposes `/api/` through a proxy to the prepared API service, allowing
apprentice code to use relative requests such as `fetch('/api/hostname/')`.
Docker service names are resolved by the proxy, not by the browser. Workspace
management routes use a separate namespace, proposed as `/code4fun/api/`.

The API describes its container, not the apprentice's physical computer.
Username is the API process user; hostname and network addresses belong to the
container. No host agent, Docker socket, or host inspection access is needed.
Use OS interfaces and libraries rather than shelling out to commands like whoami.

Learner JavaScript must execute in a preview origin isolated from the management
interface. Preview isolation, proxy routing, and how browser checks run must be
designed together before executing apprentice code. Learner runtime services
must not inherit the Build4Fun controller's Docker access or workspace.

## Prepared API

The agreed endpoint set is:

| Endpoint | Meaning |
| --- | --- |
| `/api/info` | Describe supported endpoints, response fields, units, and measurement scope. |
| `/api/username/` | Return the user running the API process. |
| `/api/hostname/` | Return the API container hostname. |
| `/api/ip` | Return container network addresses. |
| `/api/metrics` | Return live CPU usage, memory usage and limit, and API uptime. |

Responses are JSON. Proposed response shapes, to finalize before coding:

```json
{"username": "code4fun"}
```

```json
{"hostname": "api-container"}
```

```json
{"addresses": ["172.20.0.3"]}
```

```json
{
  "cpu_percent": 12.5,
  "memory_used_bytes": 33554432,
  "memory_limit_bytes": 268435456,
  "uptime_seconds": 120.5
}
```

The metrics example is illustrative, not a claim about available measurements.
Metric collection must account for container resource boundaries. Define CPU
sampling and normalization, memory accounting, and unlimited-resource behavior
before implementation. Return unavailable measurements as null and explain
availability and scope through API metadata. Uptime refers to the API process.

`/api/info` should describe these schemas, including nullable values. Finalize
its JSON shape, error responses, trailing-slash handling, address filtering,
and refresh intervals as part of the API contract. Responses must not be
cached in a way that prevents subsequent requests from observing fresh data.

## Checking apprentice work

Checks assess observable outcomes and allow different valid implementations.
HTML checks inspect required structure; CSS checks assess explicit styling
requirements; JavaScript checks exercise interactions. API checks must verify
that displayed data comes from responses rather than hardcoded sample values.
Use controlled responses and failure scenarios for repeatable checks while the
normal preview uses the live prepared API.

Checks should explain the unmet requirement without supplying the complete
solution. They must not evaluate visual taste or require a particular source
code string when behavior can be tested. API errors, loading indicators, and
refresh behavior become explicit checks in stage 6.

## Repository and delivery

Application implementation belongs in `apps/code4fun/`; lesson content and
starter assets belong in `challenges/code/`. API source and container build files
can live under the Code4Fun module; finalize their internal layout during
implementation. See [repository architecture](../monorepo.md).

Implement in reviewable increments:

1. Finalize API schemas and measurement semantics; implement and test the API container.
2. Define local launch configuration for both services without changing the existing Build4Fun launch behavior.
3. Build editing, persistence, isolated preview, and proxy routing for one project.
4. Add stages 1–4, checkpoint feedback, and progression that retains files.
5. Add stages 5–6 against the prepared API, including controlled browser checks.

## Decisions still needed

- Local execution per apprentice versus centrally hosted individual sessions.
  The current Build4Fun setup is local; shared Code4Fun hosting is not yet agreed.
- Workspace layout, editor component, storage format, and draft recovery behavior.
- Exact checkpoint contracts, progress invalidation rules, and reset/recovery semantics.
- API contract details listed above and resource limits for its containers.
- Browser origin isolation and the execution boundary for automated checks.

Hack4Fun, apprentice-written backends, a browser terminal, and shared-hosting
accounts are outside this initial Code4Fun plan.

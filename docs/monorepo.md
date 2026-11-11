# Repository architecture

Build4Fun, Code4Fun, and Crack4Fun live in one repository with separate application
directories. Build4Fun and Code4Fun are runnable local applications. Crack4Fun remains planned.

| Location | Responsibility |
| --- | --- |
| `apps/build4fun/application/` | Existing Python backend and browser interface |
| `apps/build4fun/templates/` | Compose block definitions |
| `apps/launcher/` | Local landing page and Compose lifecycle manager |
| `apps/build4fun/tests/` | Build4Fun unit, browser, and Docker checks |
| `apps/code4fun/` | Coding workspace, prepared API, image builds, and tests |
| `apps/crack4fun/` | CTF workspace, sandbox agents, portal, and tests |
| `challenges/build/` | Existing Compose lessons and configuration checks |
| `challenges/code/` | Six progressive coding stages and starter files |
| `challenges/crack/` | Four public CTF program catalogs |
| `docs/monorepo.md` | Shared repository architecture |
| `docs/naming-and-colours.md` | Application names, identity colours, and usage |
| `docs/build4fun/` | Build4Fun purpose, implementation, and images |
| `docs/code4fun/` | Code4Fun plan and implementation documentation |
| `docs/crack4fun/` | Crack4Fun scenario and filesystem planning |

Documentation follows the application boundaries: shared repository guidance
stays directly under `docs/`, and application-specific documents live under
`docs/<application>/`. Keep images with the documentation that uses them. The
[Crack4Fun file plan](crack4fun/files-plan.md) defines four CTF programs, their artifact trails,
flag convention, and sandbox, portal, and repository layout.

The [naming and colour convention](naming-and-colours.md) defines Build4Fun blue
(`#0000B4`), Code4Fun green (`#00C400`), and Crack4Fun red (`#C40000`). Crack4Fun
replaces the name Hack4Fun; its application and catalog use `crack4fun` and `crack` paths.

The [Code4Fun plan](code4fun/plan.md) defines one progressively developed server
dashboard, six frontend learning stages, and a separate prepared API container.

## Application build and launch layout

Each application owns its Dockerfiles and Python requirements under `apps/`.
Root-level `compose.<application>.yaml` files launch independent stacks. Build
contexts stay at the repository root when images need shared challenge content;
additional services may use app-local contexts, such as Code4Fun's API.

| Application | Main Dockerfile | Dependencies | Root Compose file |
| --- | --- | --- | --- |
| Launcher | `apps/launcher/Dockerfile` | Python stdlib and Docker CLI/Compose | `compose.launcher.yaml` |
| Build4Fun | `apps/build4fun/Dockerfile` | `apps/build4fun/requirements.txt` | `compose.build4fun.yaml` |
| Code4Fun | `apps/code4fun/Dockerfile` | `apps/code4fun/workspace/requirements.txt` | `compose.code4fun.yaml` |
| Crack4Fun | `apps/crack4fun/Dockerfile` | stdlib controller; `apps/crack4fun/sandbox/requirements.txt` | `compose.crack4fun.yaml` |

Run commands from the repository root:

```sh
docker compose -f compose.build4fun.yaml up --build -d --wait
docker compose -f compose.code4fun.yaml up --build -d --wait
docker compose -f compose.crack4fun.yaml up --build -d --wait
```

The launcher uses port 8070. Build4Fun uses port 8080; Code4Fun uses ports 8090 and 8091; Crack4Fun uses 8100 and 8101. Their Compose project
names remain `build4fun` and `code4fun`. Renaming the Build4Fun launch file does
not change its service name, image tag, workspace mount, or Docker ownership.
There is no default root `compose.yaml` or root Dockerfile; select the application
explicitly with `-f`. GitHub checks validate the launcher and all three learning applications independently.

Existing workspace locations, environment variables, deployment ownership,
and public `/docs/challenges/` URLs remain compatible. Lesson files now live in
`challenges/build/`; only that directory feeds the current challenge catalog.

Shared functionality remains inside Build4Fun until another addon needs it.
Extract reusable project, challenge, or runtime code when its interface can be
validated against both consumers. Avoid importing application internals across
addon directories.

Repository boundaries do not define runtime isolation. Learner code and CTF
sandboxes must run separately from the controller, without its Docker access.
Individual sessions and stronger isolation are required before shared hosting.
Code4Fun's separate-origin preview and controlled browser checks are documented
in its [implementation guide](code4fun/implementation.md). Crack4Fun's real browser terminals and local sandbox boundaries are documented
in its [implementation guide](crack4fun/implementation.md).

## Shared launcher

The [launcher](../apps/launcher/README.md) is an independent instructor-facing app,
not a proxy through which learner traffic passes. It manages only the fixed
`build4fun`, `code4fun`, and `crack4fun` Compose projects. Existing project names,
ports, workspace mounts, and progress volumes remain the same. Local builds use
the normal files. Registry starts render the same configuration, replace every
service's build with a GHCR image reference, then pull and start with no build.

The launcher needs Docker socket authority, like the Build4Fun controller. This
access is separate from learner containers. The host repository is mounted
read-only at its real absolute path. It uses loopback binding, Host/Origin
checks, fixed action targets, asynchronous jobs, and bounded activity logs.
See [launcher architecture](launcher/implementation.md) for details.

# Repository architecture

Build4Fun, Code4Fun, and Crack4Fun live in one repository with separate application
directories. Build4Fun and Code4Fun are runnable local applications. Crack4Fun remains planned.

| Location | Responsibility |
| --- | --- |
| `apps/build4fun/application/` | Existing Python backend and browser interface |
| `apps/build4fun/templates/` | Compose block definitions |
| `apps/build4fun/tests/` | Build4Fun unit, browser, and Docker checks |
| `apps/code4fun/` | Coding workspace, prepared API, image builds, and tests |
| `apps/hack4fun/` | Crack4Fun placeholder; legacy directory name |
| `challenges/build/` | Existing Compose lessons and configuration checks |
| `challenges/code/` | Six progressive coding stages and starter files |
| `challenges/hack/` | Crack4Fun challenge placeholder; legacy directory name |
| `docs/monorepo.md` | Shared repository architecture |
| `docs/naming-and-colours.md` | Application names, identity colours, and usage |
| `docs/build4fun/` | Build4Fun purpose, implementation, and images |
| `docs/code4fun/` | Code4Fun plan and implementation documentation |

Documentation follows the application boundaries: shared repository guidance
stays directly under `docs/`, and application-specific documents live under
`docs/<application>/`. Keep images with the documentation that uses them. Add
Crack4Fun documentation under `docs/crack4fun/` when its planning begins.

The [naming and colour convention](naming-and-colours.md) defines Build4Fun blue
(`#0000B4`), Code4Fun green (`#00C400`), and Crack4Fun red (`#C40000`). Crack4Fun
replaces the name Hack4Fun; its placeholder directories retain their legacy paths.

The [Code4Fun plan](code4fun/plan.md) defines one progressively developed server
dashboard, six frontend learning stages, and a separate prepared API container.

## Application build and launch layout

Each application owns its Dockerfiles and Python requirements under `apps/`.
Root-level `compose.<application>.yaml` files launch independent stacks. Build
contexts stay at the repository root when images need shared challenge content;
additional services may use app-local contexts, such as Code4Fun's API.

| Application | Main Dockerfile | Dependencies | Root Compose file |
| --- | --- | --- | --- |
| Build4Fun | `apps/build4fun/Dockerfile` | `apps/build4fun/requirements.txt` | `compose.build4fun.yaml` |
| Code4Fun | `apps/code4fun/Dockerfile` | `apps/code4fun/workspace/requirements.txt` | `compose.code4fun.yaml` |

Run commands from the repository root:

```sh
docker compose -f compose.build4fun.yaml up --build -d --wait
docker compose -f compose.code4fun.yaml up --build -d --wait
```

Build4Fun uses port 8080; Code4Fun uses ports 8090 and 8091. Their Compose project
names remain `build4fun` and `code4fun`. Renaming the Build4Fun launch file does
not change its service name, image tag, workspace mount, or Docker ownership.
There is no default root `compose.yaml` or root Dockerfile; select the application
explicitly with `-f`. GitHub checks validate both applications independently.

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
in its [implementation guide](code4fun/implementation.md). Crack4Fun and a browser
terminal remain future work.

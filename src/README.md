# Build4Fun setup and user guide

Build4Fun provides a nested block editor, project files, a live Compose preview,
a network map, saved versions, browser draft recovery, and local Docker
deployment. New projects contain a project name and no prefilled services;
apprentices supply their own images, ports, paths, and settings.

See the [project overview](../README.md), [purpose](../docs/purpose.md), and
[implementation guide](../docs/implementation.md) for background and architecture.

## Container installation

The image includes Python, the Docker CLI, and the Compose plugin. It uses the
[official Docker CLI image](https://github.com/docker-library/docker/tree/master/29/cli)
as a build stage. The application talks to the host Engine. Run the following
commands from the repository root, with Docker Engine running:

```sh
# First-time setup only; keep your existing .env on later starts.
cp .env.example .env
# On Docker Desktop for macOS, edit .env to use:
# B4F_DOCKER_SOCKET=${HOME}/.docker/run/docker.sock
docker compose up --build -d --wait
```

Open http://localhost:8080. The supplied Compose file publishes only to localhost.
Compose creates the workspace directory if it is missing. `.env` is ignored by
Git; [`.env.example`](../.env.example) documents the settings:

| Variable | Default | Purpose |
| --- | --- | --- |
| `B4F_HOST_WORKSPACE` | `${PWD}/.workspace` | Absolute host directory mounted at `/workspace`. Run Compose from the repository root, or set an explicit absolute path. |
| `B4F_HTTP_PORT` | `8080` | Local browser port. For example, `8081` serves at http://localhost:8081. |
| `B4F_DOCKER_SOCKET` | `/var/run/docker.sock` | Host Docker socket. Docker Desktop on macOS commonly uses `${HOME}/.docker/run/docker.sock`. |

The workspace variable is spelled `B4F_HOST_WORKSPACE`, and accepts a filesystem
path. `localhost` is the browser hostname, not a valid workspace path.

For a temporary UI-only container without Compose:

```sh
docker build -t build4fun:local .
docker run --rm -p 127.0.0.1:8080:8080 build4fun:local
```

`EXPOSE 8080` in the image does not publish the port; `-p` makes it accessible.
Use Compose for persistent workspace storage and Docker deployment controls.
If startup fails, inspect `docker compose ps -a` and `docker compose logs app`.
The health check reports whether the HTTP API is responding. It does not check
apprentice service health. After changing application code or templates, run
`docker compose up --build -d --wait` again. Editing `.env` requires recreating
the container with `docker compose up -d --wait`.

Compose supplies `B4F_PUBLIC_PORT` internally from `B4F_HTTP_PORT`; it does not
need a separate entry in `.env`. Inside the container, `DOCKER_HOST` points to
`unix:///var/run/docker.sock` regardless of the socket's location on the host.

The socket grants control over the Docker host, so use this in the trusted local
learning environment described in the [implementation guide](../docs/implementation.md). Stop the app with
`docker compose stop`; this preserves its workspace and apprentice deployments.

## Run with Python

From the repository root, with Python 3.9 or newer:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python src/application/server.py
```

Open http://127.0.0.1:8080. The server binds to loopback by default. Use `--port` or
`--workspace` to change the port or storage directory. A native installation
uses the Docker CLI and local Engine when deploying projects; editing, saving,
and previews are available without Docker. `B4F_DOCKER` can select the CLI
executable. The Python server does not load the repository's `.env` automatically;
that file configures the supplied Docker Compose installation.

## Use the workspace

Use **New project** to create an independent project, then switch between named
projects through **Projects** in the workspace sidebar. Display names can contain
spaces: Project 1 starts with the Compose name `project-1`. New projects contain
only their Project name block, with no prefilled services.

Expand **Projects** in the sidebar to open any saved project. The **⋯ Manage
projects** button opens the management overview. The block palette follows the
selected service or group; click **Compose project** in the builder to return to
project-level blocks. There is no project or destination dropdown in the palette.

Switching projects preserves unsaved blocks, undo history, and file drafts in
memory. **Save project** saves the active project's blocks and edited files.
Unsaved blocks and file edits also have a browser-local recovery copy. Reopen a
project after refreshing to recover or discard its draft. Drafts belong to this
browser and workspace; saving remains the durable way to preserve work. A draft
based on an older saved revision requires resolving the save conflict. Cancelling
recovery returns to Projects and keeps the browser draft for later. Browser
storage can be unavailable or full; save projects for durable storage.
Each page load starts on the project landing page with no project selected.
Create your first project or open an existing one to access the builder and files.
No default project is created; existing saved work remains available.

1. Set the project name, then choose **Add service**. Enter a service name and
   image; both remain separate blocks in the saved project.
2. Use **Add configuration** on a service to add ports, environment variables,
   mounts, or network configuration. Menus show only valid additions and support
   search, arrow keys, Enter, and Escape.
3. Click a configuration row to edit it in the inspector. Expand a group to see
   individual entries. **Project networks** defines networks created by Compose;
   **Shared resources** offers named volumes and existing external networks.
4. Opening a project takes you directly into its builder. **Files** expands the explorer. The builder shows the
   file explorer on the left, the composing area in the center, and live Compose
   YAML on the right. **Hide YAML / Show YAML** controls the desktop preview;
   on phones, **YAML / Blocks** switches the Build view. Select a block to highlight
   its YAML, or select a YAML line to locate its block. The Edit action opens a
   temporary inspector over the composing area without replacing the preview.
5. **Validate** checks block inputs and assembly rules, with errors next to the
   relevant inputs and a project-level summary. Use **Environment → Check with
   Docker** for validation with the installed Compose plugin.
6. Use the file explorer to create folders and open text files in the center
   area. The Compose preview stays visible. Contents are never checked or
   corrected. Unsaved file drafts survive switching between views.
7. Use **Save project** or Ctrl/Cmd+S to save the project and every edited file.
8. Choose **Network map** to inspect connections, or **Deploy** to save and review
   changes before starting the environment on the local Docker Engine.

A block's overflow menu contains edit, duplicate (where permitted), move, and
remove actions. Drag service icons or configuration rows to compatible parents,
or use **Move to** for a keyboard-accessible alternative. Undo restores project
changes, including deleted subtrees. Incomplete projects can still be saved.

The navigation sidebar can be collapsed. The appearance menu at its bottom
supports System, Light, and Dark modes. On phone-sized screens, navigation
collapses and Compose remains available as a dedicated view. Desktop and tablet builders keep the three-column layout.

In the file explorer, right-click a file or folder or open its ⋯ menu to delete it.
You can also focus a filename and press Delete or ⌘Backspace. Folder deletion
includes its contents and requires confirmation. Deleted drafts are discarded;
bind-mount blocks remain for you to update.

## Manage projects

Use the **⋯ Manage projects** button for the overview, or expand **Projects** to
switch directly. **+** creates a project directly; the overview also has a New
project button. Each project has Open, Rename, and Delete actions. Rename changes
the display name, leaving its Compose name and storage unchanged. Delete requires
confirmation and permanently removes that project's blocks, files, and cached
drafts. Other projects remain intact.

Unsaved projects show a **Save project** action in the overview, so you can save
them without opening or switching projects. Refresh returns to the landing page.
Save projects for durable storage; browser draft recovery is available when reopening a project after refresh.

## Network map

Choose **Network map** in the builder to see services connected to networks,
host ports, named volumes, and project files. Shared resources appear once in
the diagram with connections from each service. Services without explicit
attachments use the default network. The map reflects the current blocks,
including unsaved changes, rather than live Docker state. Select a service or
resource with a mouse or keyboard to open its block. Connection details below
the diagram explain ports and storage behavior.

## Ports and network addresses

Port mappings use quoted short syntax, for example `"8080:80"`. Protocol is
optional; leaving it unset uses Compose's TCP default. Choosing UDP produces
`"8080:80/udp"`. An optional host IP limits the host interface used for the port
binding, for example `"127.0.0.1:8080:80"`.

For a static container IPv4 address, declare a **Project network** with a subnet
such as `172.25.0.0/24` and an optional gateway. Add a **Network attachment** to
the service, select that network, and enter the optional static IPv4 address.
The compiler checks address syntax, subnet membership, gateway conflicts, and
duplicate static addresses on the same network.

An **External network** under Shared resources references a network already
created in Docker. Its subnet is managed outside this project. Static address
syntax is checked, but availability and membership in an external network's
actual subnet can only be checked when connected to Docker.

Generated output consistently orders `name`, `services`, `networks`, then
`volumes`, regardless of block creation order. Both long and short Compose port
syntax are valid; Build4Fun uses short syntax for a more readable preview.

## Storage and export

- `src/application/`: backend, assembler, persistence, and browser assets.
- `src/templates/`: one YAML definition per generic Compose block.
- `src/tests/`: unit tests, browser regression checks, and isolated example fixtures.

The original workspace is read from `.workspace/project.yaml` and `.workspace/files/`.
New projects live in `.workspace/projects/<stable-id>/`. On saving, blocks and file
edits are staged together under `revisions/<revision-id>/`; an atomic `CURRENT`
pointer selects the saved revision. A failed save leaves the previous revision
selected. A stale browser tab receives a conflict instead of overwriting newer work.
**Saved versions** lets you reload or restore a revision. Download a draft backup
before replacing local edits if needed. That JSON backup is for manual recovery;
there is no automatic draft-import command yet. History currently has no automatic
retention limit, so workspace backups and disk usage should include `revisions/`.

Definitions load on startup; restart the server after changing one. Existing
name-based resource references migrate to block IDs when unambiguous. Renaming a
resource keeps its attachments connected. File/folder paths have persistent IDs
in the saved project; **Rename** in the explorer saves drafts and updates mount
references together. Direct filesystem renames are not tracked automatically.

**Download compose.yaml** downloads only the preview; put it alongside its
referenced files to run manually. **Export project** saves and downloads a ZIP
containing `compose.yaml`, `files/`, the block project, and a short start guide.
Extract the entire ZIP before running Compose. Images, external networks, and
Docker volume contents are not included.

Deployment uses a separate copy under `deployment-inputs/`. Subsequent editor
saves do not alter mounted deployment files. Writable bind mounts write into that
deployment copy; applying another revision creates a fresh copy from saved files.
Use named volumes for data that must persist across Apply. Deployment input copies
are retained with the project and are removed when that project is deleted.

Compose names must be unique across saved projects. Rename in the overview changes
only the display name. To change a deployed Compose name, remove the deployment
first. Switching, saving, renaming, deleting, stopping, or removing one project
leaves other projects' files and deployments intact.

## Run an environment

Install Docker with the Compose plugin and start the local Docker Engine. In an
open project, choose **Deploy** in the builder or open **Environment**:

- **Check with Docker** saves blocks and file drafts together, then checks that
  revision using `docker compose config`.
- **Deploy** in the builder (or **Start / Apply** in Environment) saves the active
  project and its file drafts, then opens a review of changes since the last
  deployment attempt. The review lists added, removed, and changed services,
  configuration fields, networks, volumes, and files without displaying secret
  values. **Deploy now** validates the generated configuration and runs
  `docker compose up -d --remove-orphans`.
  Image downloads can take time; errors are shown in the output area.
- **Refresh status** fetches container state, health, and exit codes. Status is
  refreshed on demand, not continuously.
- **View logs** shows the last 200 lines per container, capped at 256 KiB overall.
  Service output is displayed as plain text without Build4Fun diagnosing it.
- **Stop** stops containers and preserves their data.
- **Remove deployment** removes containers and Compose-managed networks after
  confirmation. Named volumes, external networks, and project files remain.

Deployment comparison starts with deployments made by this version. Older
deployments display a notice that comparison data is unavailable. A deployment
record describes the last attempted Apply, which can include a partial start;
use Environment status and logs to inspect actual container state.

The deployed configuration and Engine socket are recorded separately from the
editable project. Stop, status, and logs use that snapshot even if the blocks
have since changed. Remove the deployment before deleting its project or deploying
under a different Compose name. Partial starts retain their deployment record so
they can be inspected and removed. Docker commands have time limits; after a timeout,
refresh status because Docker may have partially completed the operation.

This version supports local Unix-socket Engines. `B4F_DOCKER` can specify the Docker
CLI executable. A containerized Build4Fun instance must set `B4F_HOST_WORKSPACE`
to the absolute host path corresponding to its entire `--workspace` directory
before using bind mounts. The supplied Compose file sets this automatically.
On a native installation, paths already match. Bind
sources must exist inside the project's files directory; symbolic links and paths
outside it are rejected. File contents are never checked. Compose's automatic
`.env` loading is disabled for generated deployments.

Resources created by Build4Fun carry a workspace ownership label. Existing
containers, networks, or volumes with conflicting names and different ownership
are rejected before deployment. Multiple Docker operations are serialized; the
server remains available while Docker is working. Persistent-volume deletion is
not offered by these controls.

## Checks

```sh
.venv/bin/python -m unittest discover -s src/tests -v
```

Optional browser checks (run from the repository root):

```sh
.venv/bin/python -m pip install -r src/tests/requirements.txt
PLAYWRIGHT_BROWSERS_PATH=.venv/browsers .venv/bin/python -m playwright install chromium
PLAYWRIGHT_BROWSERS_PATH=.venv/browsers .venv/bin/python src/tests/ui_smoke.py
```

The browser checks start a temporary localhost server and use their own workspace.
They do not alter your saved project. Screenshots are written to
`/tmp/build4fun-ui` by default; use `--artifacts` to change that directory.

To explore the populated `homelab` example without changing your own workspace:

```sh
mkdir -p /tmp/build4fun-homelab
cp src/tests/fixtures/homelab/project.yaml /tmp/build4fun-homelab/project.yaml
.venv/bin/python src/application/server.py --workspace /tmp/build4fun-homelab --port 8081
```

Open http://127.0.0.1:8081. This copies example blocks for exploring the editor.
Create any referenced bind-mount files before deploying it. The fixture is not
inserted into new projects.

Run the read-only Docker integration check with:

```bash
.venv/bin/python src/tests/docker_check.py
```

It validates generated Compose YAML and checks the Engine without creating resources.
Browser tests use a simulated Engine for lifecycle actions.

To check the built container image, including its HTTP API and Host/Origin checks:

```sh
docker build -t build4fun-local-check .
.venv/bin/python src/tests/container_smoke.py
```

This starts temporary containers without publishing ports or mounting the host
Docker socket. See [CI checks](../.github/workflows/checks.yml) for the complete
verification sequence.

## Full lifecycle regression

```sh
.venv/bin/python src/tests/docker_integration.py --run
```

This opt-in test pulls `nginx:alpine` if needed and creates a uniquely named test
project. It checks saved/reopened data, validation, HTTP access, status, logs,
stop/apply, named-volume persistence, missing images, and occupied ports. Its
containers, network, temporary files, and test volume are cleaned up afterward.
The image cache remains available. It never opens your application workspace.
The GitHub Actions workflow runs unit, browser, and real lifecycle checks.

## Release images

[The release workflow](../.github/workflows/release.yml) runs when a GitHub
release is published with a tag starting with `v`, including prereleases. The tag
must also be a valid Docker image tag. Publishing a tag alone does not trigger it.

The workflow checks out the released tag, builds the Dockerfile once, and starts
the image on the GitHub runner at a localhost port. It verifies HTTP endpoints,
then runs unit, browser, Docker lifecycle, and container checks. The temporary
container is removed after the run; this hosting step is for validation.

Only a successful run publishes the same tested image to
`ghcr.io/rayleeigh/build4fun:<release-tag>`. Stable releases also update `latest`;
prereleases publish only their release tag. Authentication uses `GITHUB_TOKEN`
with `packages: write`, so no Docker Hub credentials are required. Package
visibility is managed through GitHub Packages settings. The workflow currently
builds the runner's Linux AMD64 architecture.

## Current boundaries

The application is intended for one trusted local server process per workspace.
Shared multiuser hosting, remote deployment, free-form canvas positioning,
service-file syntax highlighting, general definition-version migrations, backup
import, automatic history pruning, and guided exercise grading are not implemented.

A successful preview means the application's assembly checks passed. It does
not mean Docker Compose or the target services have validated the result.
Service configuration contents are outside Build4Fun's validation scope.

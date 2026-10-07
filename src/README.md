# Build4Fun prototype

The first slice provides a nested block editor, a project file explorer, YAML
project persistence, and Compose generation. Blocks start empty: apprentices
supply the service names, images, paths, and values themselves.

## Run locally

From the repository root, with Python 3.9 or newer:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python src/application/server.py
```

Open http://127.0.0.1:8080. The server binds to loopback by default. Use `--port` or
`--workspace` to change the port or storage directory.

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
memory. **Save project** saves the active project's blocks and edited files. Save each
edited project before refreshing; drafts are not persisted automatically.
Each page load starts on the project landing page with no project selected.
Create your first project or open an existing one to access Build and Files.
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

A block's overflow menu contains edit, duplicate (where permitted), move, and
remove actions. Drag service icons or configuration rows to compatible parents,
or use **Move to** for a keyboard-accessible alternative. Undo restores project
changes, including deleted subtrees. Incomplete projects can still be saved.

The navigation sidebar can be collapsed. The appearance menu at its bottom
supports System, Light, and Dark modes. On phone-sized screens, navigation collapses and Compose remains available as
a dedicated view. Desktop and tablet builders keep the three-column layout.

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

## Layout

- `application/`: backend, assembler, persistence, and browser assets.
- `templates/`: one YAML definition per generic Compose block.
- `tests/`: unit tests, browser regression checks, and isolated example fixtures.

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

Open http://127.0.0.1:8081. The example is development data, not a service preset
inserted into new projects.

## Current boundaries

This is an initial local prototype, not the complete implementation document.
It supports multiple isolated projects, nested block placement by click or drag, plain-text
editing with line numbers, application-level validation, and Docker Compose execution. Free-form canvas
positioning, service-file syntax highlighting, and general definition-version migrations remain
to be implemented. This application is intended for one trusted local server process
per workspace, not shared multiuser hosting.

A successful preview means the application's assembly checks passed. It does
not mean Docker Compose or the target services have validated the result.
Service configuration contents will remain outside Build4Fun's validation scope.

In the file explorer, right-click a file or folder or open its ⋯ menu to delete it.
You can also focus a filename and press Delete or ⌘Backspace. Folder deletion
includes its contents and requires confirmation. Deleted drafts are discarded;
bind-mount blocks remain for you to update.

### Manage projects

Use the **⋯ Manage projects** button for the overview, or expand **Projects** to switch directly. **+** creates a project directly; the overview also has a New
project button. Each project has Open, Rename, and Delete actions. Rename changes
the display name, leaving its Compose name and storage unchanged. Delete requires
confirmation and permanently removes that project's blocks, files, and cached
drafts. Other projects remain intact.

Unsaved projects show a **Save project** action in the overview, so you can save
them without opening or switching projects. Refresh returns to the landing page;
save drafts before refreshing or closing the application.


## Run an environment

Install Docker with the Compose plugin and start the local Docker Engine. In an
open project, choose **Environment**:

- **Check with Docker** saves blocks and file drafts together, then checks that revision using `docker compose config`.
- **Start / Apply** saves the active project and its file drafts, validates its
  generated configuration, then runs `docker compose up -d --remove-orphans`.
  Image downloads can take time; errors are shown in the output area.
- **Refresh status** fetches container state, health, and exit codes. Status is
  refreshed on demand, not continuously.
- **View logs** shows the last 200 lines per container, capped at 256 KiB overall.
  Service output is displayed as plain text without Build4Fun diagnosing it.
- **Stop** stops containers and preserves their data.
- **Remove deployment** removes containers and Compose-managed networks after
  confirmation. Named volumes, external networks, and project files remain.

The deployed configuration and Engine socket are recorded separately from the
editable project. Stop, status, and logs use that snapshot even if the blocks
have since changed. Remove the deployment before deleting its project or deploying
under a different Compose name. Partial starts retain their deployment record so
they can be inspected and removed. Docker commands have time limits; after a timeout,
refresh status because Docker may have partially completed the operation.

This version supports local Unix-socket Engines. `B4F_DOCKER` can specify the Docker
CLI executable. A containerized Build4Fun instance must set `B4F_HOST_WORKSPACE`
to the absolute host path corresponding to its entire `--workspace` directory
before using bind mounts. On a native installation, paths already match. Bind
sources must exist inside the project's files directory; symbolic links and paths
outside it are rejected. File contents are never checked. Compose's automatic
`.env` loading is disabled for generated deployments.

Resources created by Build4Fun carry a workspace ownership label. Existing
containers, networks, or volumes with conflicting names and different ownership
are rejected before deployment. Multiple Docker operations are serialized; the
server remains available while Docker is working. Persistent-volume deletion is
not offered by these controls.

Run the read-only Docker integration check with:

```bash
.venv/bin/python src/tests/docker_check.py
```

It validates generated Compose YAML and checks the Engine without creating resources.
Browser tests use a simulated Engine for lifecycle actions.

**Files** now expands its project-specific explorer in place. Use the adjacent +
to create files and folders. Each project retains its own drafts, folder expansion
state, and explorer visibility while switching. Click a file to edit it.

## Container installation

The image includes Python, the Docker CLI, and the Compose plugin. It uses the
[official Docker CLI image](https://github.com/docker-library/docker/tree/master/29/cli)
as a build stage. The application talks to the host Engine; it does not run a nested Engine.

```sh
mkdir -p "$PWD/.workspace"
export B4F_HOST_WORKSPACE="$PWD/.workspace"
# Docker Desktop users: set this if /var/run/docker.sock is not available.
# export B4F_DOCKER_SOCKET="$HOME/.docker/run/docker.sock"
docker compose up --build -d
```

Open http://127.0.0.1:8080. The supplied Compose file publishes only to localhost.
`B4F_HOST_WORKSPACE` must be the absolute host directory mounted at `/workspace`.
The socket grants control over the Docker host, so use this in the trusted local
learning environment described in the implementation document. Stop the app with
`docker compose stop`; this preserves its workspace and apprentice deployments.

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

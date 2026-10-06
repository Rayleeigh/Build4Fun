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

Open http://127.0.0.1:8080. The server binds to loopback only. Use `--port` or
`--workspace` to change the port or storage directory.

## Use the workspace

Each page load starts with an empty builder. Choose **Open saved project** to
resume saved blocks explicitly. Starting empty does not erase the saved project
or its files; saving a new project replaces the previous saved block layout.

1. Set the project name, then choose **Add service**. Enter a service name and
   image; both remain separate blocks in the saved project.
2. Use **Add configuration** on a service to add ports, environment variables,
   mounts, or network configuration. Menus show only valid additions and support
   search, arrow keys, Enter, and Escape.
3. Click a configuration row to edit it in the inspector. Expand a group to see
   individual entries. **Project networks** defines networks created by Compose;
   **Shared resources** offers named volumes and existing external networks.
4. Workspace navigation contains **Build** and **Files**. The builder shows the
   file explorer on the left, the composing area in the center, and live Compose
   YAML on the right. **Hide YAML / Show YAML** controls the desktop preview;
   on phones, **YAML / Blocks** switches the Build view. Select a block to highlight
   its YAML, or select a YAML line to locate its block. The Edit action opens a
   temporary inspector over the composing area without replacing the preview.
5. **Validate** checks block inputs and assembly rules, with errors next to the
   relevant inputs and a project-level summary. It does not invoke Docker.
6. Use the file explorer to create folders and open text files in the center
   area. The Compose preview stays visible. Contents are never checked or
   corrected. Unsaved file drafts survive switching between views.
7. Use **Save all** or Ctrl/Cmd+S to save the project and every edited file.

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

Local data lives in `.workspace/project.yaml` and `.workspace/files/`. Definitions
are loaded on startup; restart the server after adding or editing one. The
browser receives definitions from the backend and generates its controls from
that metadata. Group blocks collect entries; they do not add extra Compose keys.

Bind-mount paths in an exported Compose file are relative to the directory
containing that file. To run an export manually, place it in the workspace's
`files/` directory alongside the referenced project files. The prototype does
not connect to Docker or start containers.

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
It supports one workspace, nested block placement by click or drag, plain-text
editing with line numbers, and application-level validation. Free-form canvas
positioning, service-file syntax highlighting, file renaming, stable file-reference tracking, multiple
projects, definition migrations, Docker Compose validation and execution, and
container packaging remain to be implemented. Resource references currently use
names: renaming a declared resource requires updating its attachments.

A successful preview means the application's assembly checks passed. It does
not mean Docker Compose or the target services have validated the result.
Service configuration contents will remain outside Build4Fun's validation scope.

In the file explorer, right-click a file or folder or open its ⋯ menu to delete it.
You can also focus a filename and press Delete or ⌘Backspace. Folder deletion
includes its contents and requires confirmation. Deleted drafts are discarded;
bind-mount blocks remain for you to update.

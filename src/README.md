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

1. Add a Project name block and a Service inside the harness.
2. Add an Image inside the service, then whichever configuration groups you need.
3. Declare networks and named volumes at the harness level before referencing
   them inside services.
4. Switch the sidebar to Files to create files or folders. File contents are
   plain text and are never checked, corrected, or diagnosed.
5. Use Compose preview to generate and download the configuration.
6. Use Save all or Ctrl/Cmd+S to save the project and every edited file.
   File drafts stay in memory when switching files; save before closing the page.

Click a block to see compatible additions in the sidebar, or use the direct
+ buttons inside each parent. Drag sidebar blocks into compatible containers,
or use an existing block’s handle to move it between valid parents. Up/down
buttons reorder siblings. Collapse hides a container’s contents; Undo restores
the last addition, removal, or move until a field is edited. Incomplete projects can be saved; Compose
preview requires a valid configuration.

## Layout

- `application/`: backend, assembler, persistence, and browser assets.
- `templates/`: one YAML definition per generic Compose block.
- `tests/`: unit tests for assembly and persistence.

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

## Current boundaries

This is an initial local prototype, not the complete implementation document.
It supports one workspace, nested block placement by click or drag, plain-text
editing, and application-level validation. Free-form canvas positioning, syntax highlighting,
line numbers, file rename/delete, stable file-reference tracking, multiple
projects, definition migrations, Docker Compose validation and execution, and
container packaging remain to be implemented. Resource references currently use
names: renaming a declared resource requires updating its attachments.

A successful preview means the application's assembly checks passed. It does
not mean Docker Compose or the target services have validated the result.
Service configuration contents will remain outside Build4Fun's validation scope.

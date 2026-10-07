# Technical implementation

For the technical implementation, I want to keep things lightweight and simple. Build4Fun will run as a containerized web application, with a browser interface for assembling blocks and a backend for saving projects, generating Compose files, and managing the resulting environments. The editor will handle the visual interaction, while the backend will handle file access, validation, and communication with Docker.

The backend will connect to the host’s Docker Engine through its Unix socket. The containers created by apprentices will therefore run alongside Build4Fun on the host. The application container will include the Docker CLI and Compose plugin, and a dedicated mounted directory will store saved projects and generated files. Since access to the Docker socket grants extensive control over the host, this setup is intended for a trusted local learning environment. The browser will communicate with the backend and will not access Docker directly. [Docker Engine security](https://docs.docker.com/engine/security/)

## Building blocks

Each building block will represent one part of a Docker Compose configuration. The apprentice will start with an empty harness and assemble the environment themselves: add a project name, create a service, choose its image, and attach the configuration it needs. The service becomes a web server, database, or something else through the values they enter.

I want the blocks to be granular enough that each one introduces a clear concept. A Service block will hold the service name and provide space for its configuration blocks. Image, Ports, Environment variables, Mounts, and Network configuration will each have their own place inside it. Repeatable entries, such as individual environment variables or port mappings, can then be added to their corresponding group.

The workspace could look like this:

```text
Docker Compose harness
├── Project name: <name>
├── Service: <name>
│   ├── Image: <image>:<tag>
│   ├── Ports
│   │   └── Port mapping: <host port> → <container port>
│   ├── Environment variables
│   │   └── Variable: <key> = <value>
│   ├── Mounts
│   │   ├── Volume mount: <volume reference> → <container path>
│   │   └── Bind mount: <host path> → <container path>
│   └── Network configuration
│       └── Network attachment: <network reference>
├── Named volume: <name>
├── Network: <name>
└── External network: <existing network name>
```

This shows the available structure; apprentices will add only the blocks their environment needs. Explanations and placeholder text will describe the inputs, while names, images, paths, and configuration values remain theirs to fill in.

![Compose building block concept](/images/compose_buidlingblock_idea.png)

Placement will give each block its meaning. Named volumes and networks belong directly in the harness because multiple services can use them. A Volume mount inside a service references a declared volume and specifies where to mount it in the container. A Network attachment connects its service to a declared network. An External network block refers to a network that already exists on the Docker host; Compose will not create that network for the apprentice.

Each block will be defined in a YAML file containing its identifier, definition version, label, explanation, inputs, and configuration fragment. The definition will also specify where the block can be placed, which child blocks it accepts, whether it can be repeated, and how it contributes to the final configuration. These are Build4Fun definitions; the harness will translate them into valid Compose YAML.

## The Docker Compose harness

All blocks will sit inside a main project block, tentatively called the “Docker Compose harness.” This harness will group the services and supporting resources belonging to one environment. It will assemble a project name, service definitions, and any required network or volume definitions into the corresponding Compose sections. [Docker Compose application model](https://docs.docker.com/compose/intro/compose-application-model/)

The generation process will follow a straightforward path:

**YAML definitions → parsed objects in memory → assembled Compose YAML**

The backend will load each definition, create a separate configuration object for each block instance, and insert the apprentice’s inputs as typed values. The harness will walk through the block hierarchy and assemble the child configurations into their parent. Variable blocks will become entries in a service’s `environment` mapping, port mappings will become entries in its `ports` list, and mount blocks will become entries in its `volumes` list. Network attachments will reference the networks declared at the harness level. Grouping blocks organize these entries without adding extra YAML sections of their own. A YAML serializer will write the result to a `compose.yaml` file, handling formatting and quoting consistently.

The harness will have explicit assembly rules. Each service must have a unique name, references must point to existing resources, and conflicting definitions will produce an error instead of silently overwriting one another. Every block instance will have its own internal identity. Repeatable blocks can be added as needed, while single-value blocks, such as Project name or a service’s Image, will be limited to one per parent. Duplicate variable keys and conflicting mount destinations within a service will also be reported. This avoids relying on arbitrary YAML merging, since Compose has specific merge rules for different configuration fields. [Compose merge rules](https://docs.docker.com/reference/compose-file/merge/)

## Saving projects and adding blocks

Projects will be saved in a separate YAML file containing the block instances, their input values, parent-child relationships, resource references, and positions in the editor. Each instance will reference the identifier and version of its block definition. The generated Compose file will be an output of this saved project; reopening a project will restore the editor from the project file. For the initial implementation, manual changes to an exported Compose file will not be imported back into the block editor.

A block registry will load and validate definitions from a dedicated `blocks/` directory at startup. Adding a new block that uses the existing input types, placement rules, and assembly operations should therefore only require adding a definition file and reloading the application. New block behavior or custom interface controls may still require changes to the code. Live reloading can be added later if it proves useful.

Definition versions will keep existing projects predictable. When a definition changes, projects using an older version will continue to use that version until they are explicitly upgraded. If a required definition is missing, the application will explain which block cannot be loaded instead of substituting a different version. Keeping this format consistent will let the block library grow without adding special cases to the harness for every block. The initial assembly operations will cover assigning a value, adding a named entry, appending a list item, and referencing a declared resource.

## Validation and execution

To catch mistakes early, the application will include a YAML checker. I want to keep this straightforward by using an existing YAML parser to check block definitions for syntax errors and duplicate keys. The registry will then validate their required fields, input types, placement rules, and configuration targets before making the blocks available in the editor.

Before starting an environment, the backend will validate both the individual inputs and the assembled project. These checks will cover required values, port ranges, duplicate names, invalid nesting, and missing network or volume references. The editor will guide valid placement, but the backend will enforce the same rules when loading or running a saved project.

Once the harness has assembled the blocks, the backend will check the generated configuration with `docker compose config`. Wherever possible, errors will point back to the relevant block and explain what needs fixing. Configuration validation cannot guarantee that an environment will start successfully, so runtime errors, such as an unavailable image, missing external network, or occupied host port, will also appear in the interface.

Service configuration files, such as `*.conf`, will be editable as plain text through the project explorer. The editor will provide syntax highlighting, line numbers, and saving, but Build4Fun will not validate their contents, flag configuration mistakes, suggest fixes, or automatically correct values. This also applies to service configuration files written in YAML; the YAML checker is for Build4Fun block definitions and project data, while Compose validation checks the generated Compose configuration. File access and mount-path checks will still apply. Apprentices will research the required settings and use the service’s own logs and status to troubleshoot mistakes themselves. Messages produced by the service will remain available in the interface without Build4Fun adding its own diagnosis.

The Project name block will supply the Compose project name. Build4Fun will check that the name is valid and is not already assigned to another managed workspace. Once an environment has been deployed, its project name will stay fixed until that deployment is removed, so the application can continue managing the correct resources. Separate project names do not prevent conflicts over shared host resources such as published ports or external networks.

Mounts will support both named volumes and bind mounts. A named volume will let Docker manage the storage, while a bind mount will connect a folder from a designated host workspace to a path inside the container. Build4Fun will keep an explicit mapping between this host workspace and its own mounted view of it. Bind-mount sources sent to Docker must resolve to paths on the Docker host. The backend will resolve and check those paths against the allowed workspace before running Compose.

The backend will run Compose commands with explicit arguments and a fixed project directory. The interface will offer controls to start and stop the environment, inspect service status, and view logs. Stopping an environment will preserve its persistent data. Removing that data will be a separate, clearly labeled action. The application will manage the projects it created rather than expose general control over every container on the host.

## Learning

A Compose preview will sit alongside the block editor so apprentices can see how their choices translate into YAML. Validation messages should point back to the relevant block wherever possible, connecting a configuration error to the choice that caused it. Apprentices will also be able to export the generated file and gradually move toward working with Compose directly.

## Maintainability

To keep the implementation maintainable, the editor, block registry, harness, and Docker execution code will have separate responsibilities. Tests will focus on the shared generation logic, representative block definitions, valid and invalid nesting, repeated entries, resource references, and saving and reopening projects. This keeps the initial application small while giving it a clear path for adding new blocks and more advanced exercises.


## UX improvement roadmap

We will improve the editor in small, tested steps. The workspace navigation now
contains collapsible Projects and Files sections. Opening a project enters its
builder directly, with YAML preview alongside the blocks. The next steps are:

1. A contextual block palette that shows valid additions for the selected service,
   group, or Compose harness. Apprentices can click to add or drag a block into a
   compatible location. Selecting a leaf block uses its parent as the destination.
2. Clearer nesting and drop targets so the service hierarchy is easy to follow.
   Implemented: nested configuration rails, labeled compatible destinations,
   active drop feedback, and cleanup after a drop or cancelled drag.
3. Explicit New project, Open project, and Save project actions. Implemented:
   Save project writes the active project and its file drafts; unsaved projects
   can also be saved directly from the overview without switching. Refresh
   returns to the landing page with no project selected; it does not restore
   unsaved drafts. The browser warns before leaving with unsaved work.
4. Docker validation and execution, including start, stop, status, and logs.
   Implemented in Environment controls: explicit Compose validation, saved-project
   deployment, on-demand status and bounded logs, and persistent-data-preserving
   stop/removal. A deployment snapshot and ownership checks scope Docker actions
   to the workspace.
5. Multiple projects, each with its own blocks, files, and Compose output.
   Complete: each project owns its block tree, file workspace, drafts, undo
   history, generated Compose output, and deployment snapshot. Saved Compose
   names are unique across projects and cannot change while deployed. Saving an
   incomplete project removes stale generated output without touching its last
   deployed snapshot.

Inline editing remains a planned builder improvement: common values should be
editable directly in their blocks, with the inspector reserved for explanations
and advanced settings. The contextual palette is the current implementation step.

### Project selection and block placement

The workspace Project selector switches between independent projects. New project
creates a named workspace with its own block tree and files. Display names such as
Project 1 are separate from Compose names such as `project-1`; stable internal IDs
keep storage independent of both names. The original workspace remains accessible
without moving or deleting its files.

Add inside chooses where the next block belongs within the active project. The
palette shows the few valid options directly, without a search box. Switching
projects preserves unsaved blocks, file drafts, and undo history in memory. Save
all writes the active project; unsaved changes in other projects still need saving
before the page is closed or refreshed.

The project overview provides New, Open, Rename, and Delete actions in a compact
list. The sidebar keeps only the project selector and small add and management
buttons. Renaming changes the display name without changing Compose resource
identity. Deletion requires explicit confirmation, clears cached drafts, and
removes only the selected project's data, including for the original workspace.

Project navigation now uses an explicit Projects button instead of a dropdown.
The overview is the place to open, create, rename, or delete projects. An empty
workspace is shown as No project selected, not as a synthetic project entry.

Startup opens the project landing page, inspired by Portainer's environment
overview. No project is created or selected automatically. First-time users see
Create your first project; returning users see their saved projects. Build, Files,
and editor controls are available after explicitly creating or opening a project.

The sidebar Projects section now expands and collapses a list of saved projects.
Clicking a project opens it; the separate management button opens the overview.
The palette has no destination dropdown. It follows the selected service or group;
clicking Compose project in the builder restores the project-level palette.

Files expands and collapses its tree directly in the sidebar. Each project's
explorer shows only that project's files, with independent drafts, collapsed
folders, and explorer visibility. Switching projects restores those states;
opening a file expands its ancestors. The + action creates files or folders
in the active project.

Opening a project always opens its builder, even if its previous view was a file
or the Environment controls. The sidebar has no separate Build item; clicking
the active project returns to its builder while retaining file drafts.

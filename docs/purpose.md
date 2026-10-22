# Purpose

Build4Fun helps interested students and introductory apprentices learn the
foundations of platform engineering. It makes Docker services, networking, and
storage easier to assemble while showing how each choice affects the result.

## Use case

Our introductory course previously relied on writing Docker Compose files.
Apprentices often struggled to retain both the commands and the underlying
concepts within the limited course time. Learning YAML structure at the same
time added another barrier.

Build4Fun gives apprentices a way to construct an environment, inspect its
configuration, run it, and observe what happens.

## Challenge

The application must remain approachable without hiding the concepts apprentices
need to understand. A successful exercise should help them explain how services
connect, what a published port does, and where their data lives.

## Approach

The editor takes inspiration from Scratch. Visual blocks represent the parts of
a Compose project: services, images, ports, environment variables, mounts,
networks, and volumes. Apprentices assemble these pieces themselves rather than
starting with preconfigured service recipes.

The live Compose preview links blocks to their generated YAML. The network map
shows the connections between services, networks, host ports, and storage.
Together, these views connect visual choices to the configuration apprentices
will eventually write directly.

Apprentices can deploy their projects to the local Docker Engine after reviewing
changes. Status and service logs provide feedback for troubleshooting. Build4Fun
checks its block structure and generated Compose configuration; service
configuration files remain the apprentice's responsibility to research and debug.

Saved versions and browser draft recovery support experimentation. Project
exports let apprentices take their configuration and files outside the editor
and continue working with Docker Compose directly.

## Scope

Build4Fun is intended for a trusted local learning environment with one server
process per workspace. It manages independent projects on a local Docker Engine.
Shared multiuser hosting and remote deployment are outside the current scope.
Guided lessons and automatic exercise grading are not currently implemented.

See the [user guide](../src/README.md) for the current workflow and the
[implementation guide](implementation.md) for technical details and limitations.

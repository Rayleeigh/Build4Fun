# Build4Fun

Build4Fun introduces apprentices to Docker Compose through visual building
blocks. Create services, connect networks and storage, inspect the generated
YAML, and deploy the environment to a local Docker Engine.

Projects start with a project name and no prefilled services. Apprentices choose
the images, ports, paths, and settings themselves.

## Monorepo

This repository contains Build4Fun and reserves modules for two planned addons:
Code4Fun, an interactive coding workspace, and Hack4Fun, a beginner CTF learning
experience. Build4Fun is currently the runnable application.

See [repository architecture](docs/monorepo.md) for module boundaries, challenge
locations, and learning environments.

## Learning environments

The root Dockerfile builds the Build4Fun controller. Future Code4Fun runtimes
and Hack4Fun sandboxes will run separately from that controller; no learner
runtime or sandbox images are implemented yet.

Learner environments must not receive the controller's Docker socket, workspace,
or host filesystem mounts. Before introducing execution, define resource limits,
privileges, network access, and reset/cleanup behavior. A container alone is not
a complete sandbox design. Runtime image locations will be decided when these
addons are implemented.

## Getting started

### Install with docker compose
Install Docker with the Compose plugin and start the Docker Engine. From the
repository root:

```sh
cp .env.example .env
# Docker Desktop on macOS: set B4F_DOCKER_SOCKET in .env to
# ${HOME}/.docker/run/docker.sock
docker compose up --build -d --wait
```

Open http://localhost:8080. Compose stores projects in `.workspace/` by default
and publishes the application only on localhost. The application uses the host
Docker socket to deploy apprentice environments, so run it in a trusted local
learning environment.

To apply application or template changes, rerun the Compose command above.
Stop Build4Fun with `docker compose stop`; apprentice deployments remain running.

### Install with docker pull

```
docker run --rm -p 127.0.0.1:8080:8080 ghcr.io/rayleeigh/build4fun:latest
```

## Features

- Nested blocks with validation and a linked, live Compose preview.
- Independent projects, plain-text file editing, undo, and saved versions.
- Browser draft recovery after refresh.
- An interactive map of services, networks, host ports, and storage.
- Direct deployment with a change review, plus status, logs, stop, and removal.
- Compose downloads and project ZIP exports.

## Documentation

- [Code4Fun plan](docs/code4fun/plan.md): learning stages, workspace, prepared API,
  and implementation sequence.

- [Apprentice challenges](challenges/build/README.md): six practical labs with
  automatic saved-project checks at http://localhost:8080/challenges.
- [Setup and user guide](apps/build4fun/README.md): environment settings, editor workflow,
  deployment, troubleshooting, and checks.
- [Project purpose](docs/build4fun/purpose.md): audience and learning approach.
- [Implementation](docs/build4fun/implementation.md): architecture, persistence,
  validation, Docker execution, and current boundaries.
- [Environment example](.env.example): settings to copy into a local `.env`.

## Releases

Published GitHub releases with a `v` tag build and test the Docker image before
publishing to `ghcr.io/rayleeigh/build4fun:<release-tag>`. Stable releases also
update `latest`. See [release image validation](apps/build4fun/README.md#release-images).

## License

Read the [LICENSE](LICENSE) for the terms that apply to this project.

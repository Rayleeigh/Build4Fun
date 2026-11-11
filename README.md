# Build4Fun

Build4Fun introduces apprentices to Docker Compose through visual building
blocks. Create services, connect networks and storage, inspect the generated
YAML, and deploy the environment to a local Docker Engine.

Projects start with a project name and no prefilled services. Apprentices choose
the images, ports, paths, and settings themselves.

## Monorepo

This repository contains a shared launcher, Build4Fun, Code4Fun (an interactive frontend coding
workspace), and Crack4Fun (a hands-on CTF learning environment).
All three applications run independently.

See [repository architecture](docs/monorepo.md) for module boundaries, challenge
locations, and learning environments.

## Learning environments

`apps/build4fun/Dockerfile` builds the Build4Fun controller. Code4Fun has a separate
workspace image and prepared API container; neither receives Docker access.
Crack4Fun has separate learner sandboxes and a prepared portal, without Docker access.

Learner environments must not receive the controller's Docker socket, workspace,
or host filesystem mounts. Before introducing execution, define resource limits,
privileges, network access, and reset/cleanup behavior. A container alone is not
a complete sandbox design. Code4Fun build files live under `apps/code4fun/`.

## Getting started

### Open the launcher

```sh
cp .env.example .env # Skip this if .env is already configured.
# Docker Desktop on macOS: set B4F_DOCKER_SOCKET in .env as shown in the example.
docker compose -f compose.launcher.yaml up --build -d --wait
```

Open **http://localhost:8070** to start, stop, and open each learning app. Choose
**Local build** or **GitHub Container Registry**, with live operation output.
The launcher detects existing app stacks and keeps their saved work. Registry
mode requires the selected release's component images to be published first.
See the [launcher guide](apps/launcher/README.md).

The applications can also be launched individually:

### Install with docker compose
Install Docker with the Compose plugin and start the Docker Engine. From the
repository root:

```sh
cp .env.example .env
# Docker Desktop on macOS: set B4F_DOCKER_SOCKET in .env to
# ${HOME}/.docker/run/docker.sock
docker compose -f compose.build4fun.yaml up --build -d --wait
```

Open http://localhost:8080. Compose stores projects in `.workspace/` by default
and publishes the application only on localhost. The application uses the host
Docker socket to deploy apprentice environments, so run it in a trusted local
learning environment.

To apply application or template changes, rerun the Compose command above.
Stop Build4Fun with `docker compose -f compose.build4fun.yaml stop`; apprentice deployments remain running.

### Install with docker pull

```
docker run --rm -p 127.0.0.1:8080:8080 ghcr.io/rayleeigh/educate4fun:latest
```

### Run Code4Fun

```sh
docker compose -f compose.code4fun.yaml up --build -d --wait
```

Open http://localhost:8090 to build My Server Dashboard through six progressive
HTML, CSS, JavaScript, and API stages. See the [Code4Fun guide](apps/code4fun/README.md)
for API details, saved work, and checks. The first build includes Chromium.

### Run Crack4Fun

```sh
docker compose -f compose.crack4fun.yaml up --build -d --wait
```

Open http://localhost:8100 for Filesystem, Forensics, Network Analysis, and
Web/API: four programs with 17 flags, real browser terminals, and saved progress.
The first build compiles John and downloads RockYou. See the
[Crack4Fun guide](apps/crack4fun/README.md) for setup, tools, resets, and boundaries.

## Features

- Nested blocks with validation and a linked, live Compose preview.
- Independent projects, plain-text file editing, undo, and saved versions.
- Browser draft recovery after refresh.
- An interactive map of services, networks, host ports, and storage.
- Direct deployment with a change review, plus status, logs, stop, and removal.
- Compose downloads and project ZIP exports.

## Documentation

- [Publishing images](docs/releases.md): all seven GHCR images, release tags, and manual publishing.

- [Naming and colours](docs/naming-and-colours.md): shared application identity and the Crack4Fun name.

- [Code4Fun guide](apps/code4fun/README.md): launch, workflow, API, and checks.
- [Code4Fun plan](docs/code4fun/plan.md) and [implementation](docs/code4fun/implementation.md):
  learning stages and architecture.

- [Apprentice challenges](challenges/build/README.md): six practical labs with
  automatic saved-project checks at http://localhost:8080/challenges.
- [Setup and user guide](apps/build4fun/README.md): environment settings, editor workflow,
  deployment, troubleshooting, and checks.
- [Build4Fun interface](docs/build4fun/design.md): visual design, navigation, and accessibility.
- [Project purpose](docs/build4fun/purpose.md): audience and learning approach.
- [Implementation](docs/build4fun/implementation.md): architecture, persistence,
  validation, Docker execution, and current boundaries.
- [Environment example](.env.example): settings to copy into a local `.env`.

## Releases

Published GitHub releases with a `v` tag build and test the Docker image before
publishing to `ghcr.io/rayleeigh/educate4fun:<release-tag>`. Stable releases also
update `latest`. See [release image validation](apps/build4fun/README.md#release-images).

## License

Read the [LICENSE](LICENSE) for the terms that apply to this project.

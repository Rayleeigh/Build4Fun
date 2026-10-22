# Apprentice challenges

Open http://localhost:8080/challenges in Build4Fun. Create and save a project in the builder, then select it on the challenge page. Checks refresh every five seconds while visible and on demand. Collection progress reflects current saved projects: changing or deleting a solution removes its completion. This shared local workspace does not provide individual accounts or grading.

## Add a challenge

Add a `.md` file here, using lowercase letters, numbers, and hyphens in its filename. The filename becomes the challenge ID. Copy an existing lesson or use the example below. No JSON file or Python change is needed for the supported conditions.

The server discovers Markdown files on each request and builds the catalog in memory. `/docs/challenges/catalog.json` serves the generated JSON; there is no generated file to commit. README.md is excluded. The number in the title controls ordering, with filenames breaking ties. Invalid lesson definitions return an error naming the file, rather than silently skipping a challenge.

```markdown
---
checks:
  - label: worker uses busybox:latest
    all:
      - path: [services, worker, image]
        equals: busybox:latest
---
# 07. Your next challenge

Level: Beginner

Create a worker service using busybox:latest.

## Build

1. Add a service named worker.
2. Set its image to busybox:latest and save.

## Explain

What does an image provide?

## Try it

Inspect the image documentation and predict what happens when it starts.
```

Use the exact heading names shown above, single-line numbered build steps, and a numbered title. The goal is the text between `Level:` and `## Build`. Explain and Try it can span paragraphs. The site displays lesson text as plain text, without interpreting inline Markdown or HTML.

## Automatic conditions

Each check has a human-readable `label` and an `all` list. Every condition in that list must pass. All checks must pass in one saved project to collect the challenge. Conditions inspect compiled Compose configuration and saved project files; they never execute commands or start containers.

For mapping values in the Compose configuration, use `path` as a list of keys and exactly one operator:

- `equals: value`: exact value equality.
- `contains: value`: list membership, mapping key membership, or substring in a string.
- `exists: true`: key is present (even if its value is empty); `false` requires absence.
- `empty: true`: missing or empty value; `false` requires a nonempty value.

Example conditions:

```yaml
# A named resource exists:
path: [volumes, cache-data]
exists: true
```

```yaml
# A service attaches to a network:
path: [services, cache, networks]
contains: backend
```

```yaml
# A service has a specific mount (all five fields are required):
mount:
  service: cache
  type: volume
  source: cache-data
  target: /data
  read_only: false
```

```yaml
# A saved project file contains text:
file: index.html
contains: '<h1>Build4Fun apprentice</h1>'
```

Bind mount sources use `./index.html`; named volumes use their declared name. Missing `read_only` in Compose means false. Ports use short syntax, including the protocol, such as `127.0.0.1:8081:80/tcp`. File conditions only allow project-relative paths. Quote strings that YAML might otherwise treat as booleans or numbers.

Runtime experiments and explanations are not automatically graded. New kinds of conditions beyond this vocabulary require extending `src/application/challenges.py`.

## Docker

Lessons are copied into the image. Rebuild with `docker compose up --build -d --wait` after editing or adding lessons. When running Python directly, changes appear at the next refresh without restarting the server.

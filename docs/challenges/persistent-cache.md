---
checks:
- label: cache uses redis:7-alpine
  all:
  - path:
    - services
    - cache
    - image
    equals: redis:7-alpine
- label: cache-data is declared and mounted read-write at /data
  all:
  - path:
    - volumes
    - cache-data
    exists: true
  - mount:
      service: cache
      type: volume
      source: cache-data
      target: /data
      read_only: false
---
# 04. Give data a home

Level: Intermediate

Declare a named volume cache-data and mount it read-write at /data in cache.

## Build

1. Use cache with image redis:7-alpine.
2. Under Shared resources declare named volume cache-data.
3. In cache add Mounts → Volume mount: cache-data at /data, read-only off. Save.

## Explain

What happens to a named volume when its container is replaced?

## Try it

Using redis-cli, write a key and explicitly SAVE. Replace the container without removing volumes and read the key again. This experiment is manual; the checker verifies the mount configuration.

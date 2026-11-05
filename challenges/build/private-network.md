---
checks:
- label: web and cache use the required images
  all:
  - path:
    - services
    - web
    - image
    equals: nginx:alpine
  - path:
    - services
    - cache
    - image
    equals: redis:7-alpine
- label: backend is declared and both services attach to it
  all:
  - path:
    - networks
    - backend
    exists: true
  - path:
    - services
    - web
    - networks
    contains: backend
  - path:
    - services
    - cache
    - networks
    contains: backend
- label: cache publishes no host ports
  all:
  - path:
    - services
    - cache
    exists: true
  - path:
    - services
    - cache
    - ports
    empty: true
---
# 06. Build a private backbone

Level: Intermediate

Connect web and cache to a declared backend network, keeping cache unpublished.

## Build

1. Use web with nginx:alpine and cache with redis:7-alpine.
2. Declare a project network named backend.
3. Attach both services to backend via their network configuration blocks.
4. Remove any published ports from cache. Save.

## Explain

Why can containers on a shared network communicate without a published host port?

## Try it

Inspect the network after deployment. Explain how another container would address cache:6379. Nginx is not automatically configured to use Redis.

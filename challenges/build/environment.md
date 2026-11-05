---
checks:
- label: cache uses redis:7-alpine
  all:
  - path:
    - services
    - cache
    - image
    equals: redis:7-alpine
- label: cache has APP_MODE=training
  all:
  - path:
    - services
    - cache
    - environment
    - APP_MODE
    equals: training
---
# 03. Configure a service

Level: Beginner

Add a service named cache using redis:7-alpine with environment variable APP_MODE=training.

## Build

1. Keep web and add a second service named cache.
2. Set its image to redis:7-alpine.
3. Add Environment → Variable: APP_MODE with value training. Save.

## Explain

Does setting an arbitrary variable change Redis behavior, or must the application read it?

## Try it

Deploy and inspect the container environment using Docker. APP_MODE is a learning marker; Redis does not use it as configuration.

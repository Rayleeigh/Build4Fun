---
checks:
- label: web uses nginx:alpine
  all:
  - path:
    - services
    - web
    - image
    equals: nginx:alpine
---
# 01. First container

Level: Beginner

Create a service named web using nginx:alpine.

## Build

1. Add a Service block and name it web.
2. Add its Image block with nginx:alpine, then save the project.

## Explain

What does an image provide, and how does a container differ from it?

## Try it

Deploy it and inspect its logs. Explain why it is not yet reachable on a host port.

---
checks:
- label: web uses nginx:alpine
  all:
  - path:
    - services
    - web
    - image
    equals: nginx:alpine
- label: web publishes 127.0.0.1:8081:80 over TCP
  all:
  - path:
    - services
    - web
    - ports
    contains: 127.0.0.1:8081:80/tcp
---
# 02. Open the front door

Level: Beginner

Publish web on localhost port 8081, forwarding to container port 80 over TCP.

## Build

1. Complete First container in the same project.
2. Add Ports → Port mapping to web: host 8081, container 80, host IP 127.0.0.1, TCP.
3. Save the project.

## Explain

Why are the host and container ports different?

## Try it

Deploy and visit http://127.0.0.1:8081. Change only the host port and predict the new URL.

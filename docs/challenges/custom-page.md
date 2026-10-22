---
checks:
- label: web uses nginx:alpine
  all:
  - path:
    - services
    - web
    - image
    equals: nginx:alpine
- label: web bind-mounts index.html read-only at the nginx index path
  all:
  - mount:
      service: web
      type: bind
      source: ./index.html
      target: /usr/share/nginx/html/index.html
      read_only: true
- label: index.html contains the apprentice heading
  all:
  - file: index.html
    contains: <h1>Build4Fun apprentice</h1>
---
# 05. Make it yours

Level: Intermediate

Serve your own HTML from web using a read-only bind mount.

## Build

1. Create a project file named index.html containing <h1>Build4Fun apprentice</h1>.
2. Use web with nginx:alpine.
3. Add a Bind mount from index.html to /usr/share/nginx/html/index.html with read-only on. Save files and project.

## Explain

How does a bind mount differ from a named volume?

## Try it

Publish web as in Open the front door, deploy, then open the page. Edit the heading and observe the result.

# Publishing 4Fun images

[The release workflow](../.github/workflows/release.yml) validates the learning
apps and publishes every application Dockerfile to GitHub Container Registry.
It uses the repository's `GITHUB_TOKEN` with `packages: write`; no registry token
needs to be committed or added to the launcher.

## Image names

For this repository, replace `<version>` with a release tag such as `v1.2.3`:

| Image | GHCR reference |
| --- | --- |
| Build4Fun | `ghcr.io/rayleeigh/educate4fun:<version>` |
| Code4Fun workspace | `ghcr.io/rayleeigh/educate4fun/code4fun-workspace:<version>` |
| Code4Fun API | `ghcr.io/rayleeigh/educate4fun/code4fun-api:<version>` |
| Crack4Fun workspace | `ghcr.io/rayleeigh/educate4fun/crack4fun-workspace:<version>` |
| Crack4Fun sandbox | `ghcr.io/rayleeigh/educate4fun/crack4fun-sandbox:<version>` |
| Crack4Fun portal | `ghcr.io/rayleeigh/educate4fun/crack4fun-portal:<version>` |
| Launcher | `ghcr.io/rayleeigh/educate4fun/launcher:<version>` |

Forks derive the namespace from their own GitHub repository. Build4Fun retains
its original image reference; the launcher already uses these component paths.
The shared sandbox image is built once in the publishing matrix and used by
four distinct Crack4Fun containers. New releases build both `linux/amd64` and `linux/arm64` using Buildx and QEMU.
Older image tags may still be AMD64-only. The launcher requires the user to
choose ARM64 or AMD64 and checks that the image supplies that architecture.
Choosing a non-native architecture requires Docker emulation.

## Publish a release

1. Commit and push the application files and workflow changes to GitHub.
2. Publish a GitHub release with a Docker-compatible tag starting with `v`.
   The release's commit must include all the application Dockerfiles.
3. Watch **Actions → Release 4Fun images**. Preparation fixes one source commit,
   then Build4Fun and addon validations run. The publishing matrix starts only
   after both validation jobs succeed.
4. A stable release publishes its version tag and `latest` for all seven images.
   A prerelease publishes its version tag without changing `latest`.

Non-`v` releases do not publish images. Publishing this workflow does not create
GitHub releases automatically. GitHub releases remain the trigger for the normal
release path.

## Publish manually

Once the workflow is available on the default branch, open **Actions → Release
4Fun images → Run workflow**. Select the source branch, enter a version tag such
as `v1.2.3`, and choose whether to update `latest`. Manual runs build the selected
branch's source commit; they do not create a Git tag or GitHub release. They run
the same validation and publish all seven images. Reusing a tag replaces it, so
prefer a new version for each release.

## Checks, access, and failure handling

Validation includes application unit tests, browser checks, real Docker lifecycle
checks, and Code4Fun/Crack4Fun container checks. Published images carry source,
source revision, and version labels. Buildx caches are separated by image name.
The workflow does not push images on ordinary commits or pull requests.

If a package already exists, ensure this repository has permission to write it.
Set the packages' visibility to public if the launcher should pull anonymously.
See GitHub's [container registry authentication guide](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
and Docker's [GitHub Actions cache guide](https://docs.docker.com/build/ci/github-actions/cache/).

GHCR does not make the seven image pushes one atomic operation. If one publishing
job fails, inspect its log and rerun the failed jobs; other matrix jobs may have
already published successfully. The launcher reports unavailable images rather
than falling back to local builds.

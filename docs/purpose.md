# Purpose
> The purpose of this repository is to have an easy to build/understand introductionary course, into the foundations as a platform engineer for interested students. The goal hereby is to abstract the more complicated aspect of docker creation, networking, and system file architecture while still providing a rudementary understanding of how these things affect the endresult.

## Use case
The use case derived itself from our observations in comprehension from the intrudtionary apprentices during our introductionary course. Repeatedly, it has been observed that the greatest challenged posed to the introductionary apprentices is that most commands and concepts do not stick during the limited timeframe the program is running. Thus the need for a more comprehensive course arose and now needs implementation.

## Challenge
The main challenge is to make the program approachable enough for new apprentices without oversimplifying the concepts and giving them enough depth to build a lasting understanding.

## Approach
My approach to this challenge is straightforward: I take inspiration from Scratch. Block coding is where many of us started, offering a quick and playful way to develop the logical thinking needed in IT. It breaks down complex processes into simple, understandable blocks that make the underlying logic easier to grasp.

The previous course relied on Docker Compose files. These describe how services are configured and connected, but their structure and configuration options can be difficult for an inexperienced apprentice to understand.

This is where the block coding approach comes in handy: representing the main parts of a Compose file as visual building blocks, from the name and individual services to their configuration and supporting resources, such as networks and volumes. Apprentices can then assemble an environment piece by piece while learning how its components fit together.

## Technical implementation

For the technical implementation, I want to keep things lightweight and simple. Build4Fun will run as a containerized web application, with a browser interface for assembling blocks and a backend for saving projects, generating Compose files, and managing the resulting environments. The editor will handle the visual interaction, while the backend will handle file access, validation, and communication with Docker.

The backend will connect to the host’s Docker Engine through its Unix socket. The containers created by apprentices will therefore run alongside Build4Fun on the host. The application container will include the Docker CLI and Compose plugin, and a dedicated mounted directory will store saved projects and generated files. Since access to the Docker socket grants extensive control over the host, this setup is intended for a trusted local learning environment. The browser will communicate with the backend and will not access Docker directly. [Docker Engine security](https://docs.docker.com/engine/security/)

### Building blocks

Each building block will be defined in a YAML file. This definition will contain a Compose template together with the information needed to display and configure the block: a stable identifier, a definition version, a label, a short explanation, and a set of supported inputs. Each input will describe its type, default value, validation rules, and where its value belongs in the template.

A web server block, for example, could provide an image field and a port field, with sensible defaults already filled in. The editor will use the definition to display the appropriate text inputs, dropdowns, and connection points. Apprentices can then configure the service without having to understand every Compose option at once.

![Compose building block concept](/images/compose_buidlingblock_idea.png)

The initial block types will cover services, networks, and volumes. Connections will have a defined meaning: connecting a service to a network will add a network reference to that service, while attaching a volume will also require a mount location inside the container. This keeps the visual interactions tied to the configuration they produce.

### The Docker Compose harness

All blocks will sit inside a main project block, tentatively called the “Docker Compose harness.” This harness will group the services and supporting resources belonging to one environment. It will assemble a project name, service definitions, and any required network or volume definitions into the corresponding Compose sections. [Docker Compose application model](https://docs.docker.com/compose/intro/compose-application-model/)

The generation process will follow a straightforward path:

**YAML definitions → parsed objects in memory → assembled Compose YAML**

The backend will load each definition, create a separate copy of its template for each block instance, and insert the apprentice’s inputs as typed values. The harness will then place these configured objects into one Compose structure and resolve the references between them. A YAML serializer will write the result to a `compose.yaml` file, handling formatting and quoting consistently.

The harness will have explicit assembly rules. Each service must have a unique name, references must point to existing resources, and conflicting definitions will produce an error instead of silently overwriting one another. The same block definition can be used several times, as long as each instance has its own identity and service name. This avoids relying on arbitrary YAML merging, since Compose has specific merge rules for different configuration fields. [Compose merge rules](https://docs.docker.com/reference/compose-file/merge/)

### Saving projects and adding blocks

Projects will be saved in a separate YAML file containing the block instances, their input values, connections, and positions in the editor. Each instance will reference the identifier and version of its block definition. The generated Compose file will be an output of this saved project; reopening a project will restore the editor from the project file. For the initial implementation, manual changes to an exported Compose file will not be imported back into the block editor.

A block registry will load and validate definitions from a dedicated `blocks/` directory at startup. Adding a new service template that uses the existing input types and connection rules should therefore only require adding a definition file and reloading the application. New block behavior or custom interface controls may still require changes to the code. Live reloading can be added later if it proves useful.

Definition versions will keep existing projects predictable. When a definition changes, projects using an older version will continue to use that version until they are explicitly upgraded. If a required definition is missing, the application will explain which block cannot be loaded instead of substituting a different version. Keeping this format consistent will let the block library grow without adding special cases to the harness for every service.

### Validation and execution

Before starting an environment, the backend will validate both the individual inputs and the assembled project. These checks will cover required values, input types, port ranges, duplicate service names, and missing network or volume references. The generated file will then be checked with `docker compose config`. Configuration validation cannot guarantee that an environment will start successfully, so runtime errors, such as an unavailable image or a host port already in use, will also be shown in the interface.

Each workspace will receive a stable, unique Compose project name so that its resources can be managed together. Project names will separate Compose-managed resources, but shared host resources, such as published ports, can still conflict. For the initial version, persistent storage will use Docker-managed named volumes, keeping arbitrary host paths out of the block configuration.

The backend will run Compose commands with explicit arguments and a fixed project directory. The interface will offer controls to start and stop the environment, inspect service status, and view logs. Stopping an environment will preserve its persistent data. Removing that data will be a separate, clearly labeled action. The application will manage the projects it created rather than expose general control over every container on the host.

### Learning and maintainability

A Compose preview will sit alongside the block editor so apprentices can see how their choices translate into YAML. Validation messages should point back to the relevant block wherever possible, connecting a configuration error to the choice that caused it. Apprentices will also be able to export the generated file and gradually move toward working with Compose directly.

To keep the implementation maintainable, the editor, block registry, harness, and Docker execution code will have separate responsibilities. Tests will focus on the shared generation logic, representative block definitions, invalid connections, and saving and reopening projects. This keeps the initial application small while giving it a clear path for adding new blocks and more advanced exercises.
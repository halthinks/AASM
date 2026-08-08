# AASM Governance

AASM is currently maintained as a small, maintainer-led open-source project.

## Decision model

The maintainer is responsible for final decisions on repository direction, releases, compatibility, security response, and merge approval. Community input is strongly encouraged through issues, discussions, and pull requests.

The project should favor decisions that preserve these principles:

- role-agnostic core architecture
- explicit state and transitions
- separation of capability from authority
- evidence and provenance as first-class concepts
- reversible execution where practical
- minimal core dependencies
- domain-neutral abstractions

## Maintainers

The GitHub repository owner currently acts as project maintainer.

As the project grows, additional maintainers may be added based on sustained, constructive contributions and demonstrated understanding of the architecture and community expectations.

## Changes requiring design discussion

Please open an issue before implementing substantial changes involving:

- new or removed machine states
- legal transition changes
- public schema changes
- persistence format changes
- distributed execution semantics
- authority/governance models
- security-sensitive capabilities
- large dependencies
- backward-incompatible APIs

## Releases

Releases should summarize user-visible changes, compatibility impact, migration requirements, known limitations, and validation status.

AASM follows semantic-versioning intent:

- **PATCH**: backward-compatible fixes
- **MINOR**: additive functionality that should remain compatible
- **MAJOR**: intentional breaking changes

Before 1.0, the API remains experimental and minor releases may contain larger changes, but breaking changes should still be documented rather than hidden.

## Project integrity

Contributions should improve the actual runtime rather than inflate apparent capability. Documentation should distinguish implemented behavior, experimental behavior, and roadmap ideas.

# Security Policy

## Supported versions

AASM is currently early-stage. Security fixes will normally target the latest code on `main` until formal versioned support windows are established.

## Reporting a vulnerability

Please **do not open a public GitHub issue for a security vulnerability**.

Preferred reporting path:

1. Use GitHub's private vulnerability reporting feature from the repository's **Security** tab if it is available.
2. Otherwise contact the maintainer using a private contact method listed on the maintainer's GitHub profile.
3. If neither is available, open a public issue that only asks for a private security contact channel. Do not include exploit details in that issue.

Please include, when possible:

- affected component/version or commit
- impact
- reproduction steps or proof of concept
- prerequisites for exploitation
- suggested mitigation, if known

## Security scope

Particular attention should be given to vulnerabilities involving:

- unauthorized state mutation
- authority-policy bypass
- forged or replayed agent messages
- unsafe deserialization/persistence
- provenance or evidence tampering
- path traversal or arbitrary file access in future persistence adapters
- command/tool execution boundaries
- credential leakage through agent context
- denial-of-service through uncontrolled graph/branch/resource growth

AASM does not itself make arbitrary model output trustworthy. Integrators remain responsible for sandboxing tools, protecting credentials, validating external inputs, and setting appropriate authority boundaries.

# AASM Use Cases

## Software-engineering agent

A code agent can map repository tasks into a dependency graph, checkpoint before large edits, route implementation to specialists, run tests, and backtrack or repair when verification fails.

## Research agent

Claims can be represented with source dependencies. An adversarial verifier can challenge claims that lack evidence or that admit plausible counterexamples before the machine transitions to completion.

## Engineering design workflow

Requirements, CAD, simulation, FEA/CFD, drawings, BOM work, manufacturing checks, and validation can be represented as dependent nodes. Failed validation can invalidate only the affected branch rather than forcing the entire workflow to restart.

## Multi-agent resource allocation

When there are more candidate tasks than available workers, a capacity graph can represent agent/tool limits. Max-flow/min-cut reasoning can expose bottlenecks and prevent useless worker spawning.

## Human-in-the-loop approval

Low-risk reversible work can proceed autonomously while irreversible or high-impact transitions require human approval under the selected authority policy.

## Long-running workflow

Persistent implementations can store state/checkpoints, recover from process failure, and resume from the last valid machine state rather than relying on chat history alone.

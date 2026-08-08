# Erickson → AASM design mapping

AASM is an original software implementation inspired by standard algorithm-design ideas presented especially clearly in Jeff Erickson's open algorithms materials. It does not reproduce textbook prose or exercises.

| Source idea | AASM mechanism |
|---|---|
| Recursion / reduction | Problem decomposition into smaller structurally related tasks |
| Backtracking | Candidate branches, checkpoints, pruning, restoration |
| Dynamic programming | Canonical state signatures and memoized subproblem results |
| Greedy algorithms | Optional local-choice operator only when a declared invariant makes it appropriate |
| Graph traversal / DAGs | Dependency discovery and topological execution order |
| Shortest paths | Costed plan alternatives and edge relaxation |
| Maximum flow / minimum cut | Capacity-constrained assignment and bottleneck identification |
| Adversary arguments | Counterexample-oriented pre-commit verifier |
| Finite automata | Explicit state set, event inputs, legal transition function, accepting/terminal states |

## Primary sources

- Jeff Erickson, *Algorithms*: https://jeffe.cs.illinois.edu/teaching/algorithms/
- Full textbook: https://jeffe.cs.illinois.edu/teaching/algorithms/book/Algorithms-JeffE.pdf
- Recursion: https://jeffe.cs.illinois.edu/teaching/algorithms/book/01-recursion.pdf
- Backtracking: https://jeffe.cs.illinois.edu/teaching/algorithms/book/02-backtracking.pdf
- Dynamic programming: https://jeffe.cs.illinois.edu/teaching/algorithms/book/03-dynprog.pdf
- Greedy algorithms: https://jeffe.cs.illinois.edu/teaching/algorithms/book/04-greedy.pdf
- Shortest paths: https://jeffe.cs.illinois.edu/teaching/algorithms/book/08-sssp.pdf
- Maximum flows/minimum cuts: https://jeffe.cs.illinois.edu/teaching/algorithms/book/10-maxflow.pdf
- Models of Computation: https://jeffe.cs.illinois.edu/teaching/algorithms/models/all-models.pdf

The mapping is architectural: AASM applies these algorithmic patterns to orchestration, state governance, search, memory, resource allocation, and verification.

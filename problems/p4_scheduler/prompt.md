Implement a Python module with a single function:

    schedule(tasks: dict[str, tuple[int, list[str]]], workers: int) -> dict[str, tuple[int, int]]

A deterministic greedy scheduler for a DAG of tasks on identical workers.

Input:
- tasks maps task_id -> (duration, deps). duration is a positive int; deps is a
  list of task_ids that must FINISH before this task can start.
- workers: number of identical workers (>= 1). A worker runs one task at a time,
  non-preemptively.

Scheduling policy (must be followed EXACTLY — the output is fully determined):
1. Time starts at 0. A task becomes READY at the maximum finish time of its deps
   (0 if no deps).
2. Simulate event times in increasing order. At each moment when at least one
   worker is idle and at least one task is ready and unstarted, repeatedly assign:
   pick the ready task with the LARGEST duration; break ties by SMALLEST task_id
   (lexicographic). Assign it to the idle worker with the SMALLEST index.
   Repeat until no idle worker or no ready task, then advance time to the next
   event (a running task finishing or a task becoming ready).
3. A task finishing and another starting at the same instant is allowed: at time
   t, tasks finishing at t free their workers and newly-ready tasks may start at t.

Output:
- dict mapping every task_id -> (start_time, worker_index).

Errors:
- If the dependency graph has a cycle or references an unknown task id,
  raise ValueError.

Example:
    tasks = {"a": (3, []), "b": (2, []), "c": (4, ["a"]), "d": (1, ["a", "b"])}
    schedule(tasks, 2)
      -> {"a": (0, 0), "b": (0, 1), "c": (3, 0), "d": (3, 1)}
    (at t=0: ready {a,b}; a longer -> worker 0; b -> worker 1.
     at t=2: b done, nothing ready. at t=3: a done; ready {c,d}; c longer -> worker 0; d -> worker 1)

Return ONE complete Python module in a single ```python code block. No prose outside the block.

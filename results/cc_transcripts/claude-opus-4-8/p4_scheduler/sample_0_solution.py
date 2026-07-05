"""Deterministic greedy scheduler for a DAG of tasks on identical workers."""

from collections import deque


def schedule(tasks, workers):
    """Schedule a DAG of tasks on `workers` identical, non-preemptive workers.

    tasks maps task_id -> (duration, deps). Returns a dict mapping every
    task_id -> (start_time, worker_index) following the exact greedy policy.

    Raises ValueError on cycles or references to unknown task ids.
    """
    if not isinstance(workers, int) or workers < 1:
        raise ValueError("workers must be an integer >= 1")

    # Validate references to unknown task ids.
    for tid, val in tasks.items():
        dur, deps = val
        for d in deps:
            if d not in tasks:
                raise ValueError("unknown task id in dependencies: %r" % (d,))

    # Distinct dependency sets and reverse (dependents) mapping.
    dep_sets = {tid: set(tasks[tid][1]) for tid in tasks}
    dependents = {tid: [] for tid in tasks}
    for tid, deps in dep_sets.items():
        for d in deps:
            dependents[d].append(tid)

    # Cycle detection via Kahn's algorithm.
    indeg = {tid: len(dep_sets[tid]) for tid in tasks}
    q = deque(t for t in tasks if indeg[t] == 0)
    seen = 0
    while q:
        n = q.popleft()
        seen += 1
        for m in dependents[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                q.append(m)
    if seen != len(tasks):
        raise ValueError("dependency graph contains a cycle")

    # --- Simulation ---
    total = len(tasks)
    result = {}
    remaining = {tid: set(dep_sets[tid]) for tid in tasks}
    started = set()
    ready = set(t for t in tasks if not remaining[t])  # ready at time 0
    busy_until = [0] * workers          # worker i is idle at time t if busy_until[i] <= t
    running = []                        # list of (finish_time, worker_index, task_id)

    t = 0
    while len(result) < total:
        # Process tasks finishing at time t: free workers, unlock dependents.
        still = []
        for f, w, tid in running:
            if f == t:
                for dep in dependents[tid]:
                    rem = remaining[dep]
                    rem.discard(tid)
                    if not rem and dep not in started:
                        ready.add(dep)
            else:
                still.append((f, w, tid))
        running = still

        # Greedily assign ready tasks to idle workers.
        while ready:
            idle = [i for i in range(workers) if busy_until[i] <= t]
            if not idle:
                break
            # Largest duration, ties broken by smallest task_id.
            best = min(ready, key=lambda x: (-tasks[x][0], x))
            w = min(idle)
            dur = tasks[best][0]
            result[best] = (t, w)
            started.add(best)
            ready.discard(best)
            busy_until[w] = t + dur
            running.append((t + dur, w, best))

        if len(result) == total:
            break

        # Advance to the next event (a running task finishing).
        future = [f for f, _w, _tid in running if f > t]
        if not future:
            # No running tasks yet work remains: only possible on an invalid
            # graph, already ruled out by cycle detection.
            break
        t = min(future)

    return result

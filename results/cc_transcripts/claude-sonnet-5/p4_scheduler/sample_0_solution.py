"""Deterministic greedy scheduler for a DAG of tasks on identical workers."""

import heapq


def schedule(tasks, workers):
    """Schedule tasks on `workers` identical workers.

    tasks: dict[str, tuple[int, list[str]]] mapping task_id -> (duration, deps)
    workers: number of identical workers (>= 1)

    Returns dict[str, tuple[int, int]] mapping task_id -> (start_time, worker_index).

    Raises ValueError if the dependency graph has a cycle or references an
    unknown task id.
    """
    for task_id, (_duration, deps) in tasks.items():
        for dep in deps:
            if dep not in tasks:
                raise ValueError(
                    f"Task {task_id!r} depends on unknown task {dep!r}"
                )

    # Cycle detection via iterative DFS (white/gray/black coloring).
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {task_id: WHITE for task_id in tasks}
    for start in tasks:
        if color[start] != WHITE:
            continue
        stack = [(start, iter(tasks[start][1]))]
        color[start] = GRAY
        while stack:
            node, it = stack[-1]
            advanced = False
            for dep in it:
                if color[dep] == GRAY:
                    raise ValueError("Dependency graph has a cycle")
                if color[dep] == WHITE:
                    color[dep] = GRAY
                    stack.append((dep, iter(tasks[dep][1])))
                    advanced = True
                    break
            if not advanced:
                color[node] = BLACK
                stack.pop()

    if not tasks:
        return {}

    unique_deps = {task_id: set(deps) for task_id, (_d, deps) in tasks.items()}
    remaining_count = {task_id: len(d) for task_id, d in unique_deps.items()}

    dependents = {task_id: [] for task_id in tasks}
    for task_id, deps in unique_deps.items():
        for dep in deps:
            dependents[dep].append(task_id)

    started = set()
    result = {}
    remaining = len(tasks)

    idle_workers = list(range(workers))
    heapq.heapify(idle_workers)
    running = []  # heap of (finish_time, worker_index, task_id)

    ready_set = {task_id for task_id, cnt in remaining_count.items() if cnt == 0}

    current_time = 0

    while remaining > 0:
        # Free workers for tasks finishing exactly at current_time, and
        # promote newly-ready dependents.
        while running and running[0][0] == current_time:
            finish_time, worker_idx, finished_task = heapq.heappop(running)
            heapq.heappush(idle_workers, worker_idx)
            for dep_task in dependents[finished_task]:
                remaining_count[dep_task] -= 1
                if remaining_count[dep_task] == 0:
                    ready_set.add(dep_task)

        # Greedily assign ready tasks to idle workers.
        while idle_workers and ready_set:
            chosen = min(ready_set, key=lambda t: (-tasks[t][0], t))
            worker_idx = heapq.heappop(idle_workers)
            ready_set.discard(chosen)
            started.add(chosen)
            result[chosen] = (current_time, worker_idx)
            remaining -= 1
            duration = tasks[chosen][0]
            heapq.heappush(running, (current_time + duration, worker_idx, chosen))

        if remaining == 0:
            break

        # Advance to the next event: the earliest running task's finish time.
        current_time = running[0][0]

    return result

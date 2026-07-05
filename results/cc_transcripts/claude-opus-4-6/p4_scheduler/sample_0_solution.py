def schedule(tasks: dict[str, tuple[int, list[str]]], workers: int) -> dict[str, tuple[int, int]]:
    for tid, (dur, deps) in tasks.items():
        for d in deps:
            if d not in tasks:
                raise ValueError(f"unknown dependency {d!r} in task {tid!r}")

    in_degree = {tid: 0 for tid in tasks}
    children = {tid: [] for tid in tasks}
    for tid, (_, deps) in tasks.items():
        for d in deps:
            children[d].append(tid)
            in_degree[tid] += 1

    topo = [tid for tid in tasks if in_degree[tid] == 0]
    i = 0
    while i < len(topo):
        for c in children[topo[i]]:
            in_degree[c] -= 1
            if in_degree[c] == 0:
                topo.append(c)
        i += 1
    if len(topo) != len(tasks):
        raise ValueError("dependency cycle detected")

    finish_time = {}
    result = {}
    scheduled = set()
    worker_free = [0] * workers

    while len(scheduled) < len(tasks):
        ready = []
        for tid, (dur, deps) in tasks.items():
            if tid in scheduled:
                continue
            if not all(d in finish_time for d in deps):
                continue
            earliest = max((finish_time[d] for d in deps), default=0)
            ready.append((tid, dur, earliest))

        if not ready:
            break

        ready.sort(key=lambda x: (-x[1], x[0]))

        min_time = min(
            min(max(wf, earliest) for wf in worker_free)
            for _, _, earliest in ready
        )

        idle_workers = sorted(i for i in range(workers) if worker_free[i] <= min_time)
        available = sorted(
            ((tid, dur) for tid, dur, earliest in ready if earliest <= min_time),
            key=lambda x: (-x[1], x[0]),
        )

        for tid, dur in available:
            if not idle_workers:
                break
            w = idle_workers.pop(0)
            result[tid] = (min_time, w)
            finish_time[tid] = min_time + dur
            worker_free[w] = min_time + dur
            scheduled.add(tid)

    return result

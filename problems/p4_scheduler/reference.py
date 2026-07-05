import heapq


def schedule(tasks, workers):
    indeg = {t: 0 for t in tasks}
    children = {t: [] for t in tasks}
    for t, (dur, deps) in tasks.items():
        for d in deps:
            if d not in tasks:
                raise ValueError(f"unknown dep {d}")
            indeg[t] += 1
            children[d].append(t)
    # cycle check
    dq = [t for t, k in indeg.items() if k == 0]
    tmp = dict(indeg)
    seen = 0
    while dq:
        t = dq.pop()
        seen += 1
        for c in children[t]:
            tmp[c] -= 1
            if tmp[c] == 0:
                dq.append(c)
    if seen != len(tasks):
        raise ValueError("cycle")

    result, finish = {}, {}
    remaining = dict(indeg)
    ready = [(-tasks[t][0], t) for t, k in indeg.items() if k == 0]
    heapq.heapify(ready)
    idle = list(range(workers))
    heapq.heapify(idle)
    running = []  # (finish_time, task_id, worker)
    now = 0
    n = len(tasks)
    done = 0
    while done < n:
        while idle and ready:
            _, t = heapq.heappop(ready)
            w = heapq.heappop(idle)
            result[t] = (now, w)
            heapq.heappush(running, (now + tasks[t][0], t, w))
        now = running[0][0]
        while running and running[0][0] == now:
            _, t, w = heapq.heappop(running)
            heapq.heappush(idle, w)
            finish[t] = now
            done += 1
            for c in children[t]:
                remaining[c] -= 1
                if remaining[c] == 0:
                    heapq.heappush(ready, (-tasks[c][0], c))
    return result

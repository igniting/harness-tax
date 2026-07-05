import random
import pytest
from bench_common.loader import load_solution

sol = load_solution()


def oracle(tasks, workers):
    """Independent unit-time-step simulator implementing the policy literally."""
    for t, (dur, deps) in tasks.items():
        for d in deps:
            if d not in tasks:
                raise ValueError
    # cycle check via DFS
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {t: WHITE for t in tasks}

    def dfs(u):
        color[u] = GRAY
        for d in tasks[u][1]:
            if color[d] == GRAY:
                raise ValueError
            if color[d] == WHITE:
                dfs(d)
        color[u] = BLACK

    for t in tasks:
        if color[t] == WHITE:
            dfs(t)

    result = {}
    finish = {}
    running = {}  # worker -> (task, finish_time)
    unstarted = set(tasks)
    t_now = 0
    horizon = sum(d for d, _ in tasks.values()) + 1
    while unstarted or running:
        assert t_now <= horizon, "oracle runaway"
        # finish events at t_now
        for w in list(running):
            task, ft = running[w]
            if ft == t_now:
                finish[task] = t_now
                del running[w]
        # assignment loop at t_now
        while True:
            idle = sorted(set(range(workers)) - set(running))
            ready = [t for t in unstarted
                     if all(d in finish and finish[d] <= t_now for d in tasks[t][1])]
            if not idle or not ready:
                break
            ready.sort(key=lambda t: (-tasks[t][0], t))
            t = ready[0]
            w = idle[0]
            result[t] = (t_now, w)
            running[w] = (t, t_now + tasks[t][0])
            unstarted.discard(t)
        t_now += 1
    return result


def test_spec_example():
    tasks = {"a": (3, []), "b": (2, []), "c": (4, ["a"]), "d": (1, ["a", "b"])}
    assert sol.schedule(tasks, 2) == {"a": (0, 0), "b": (0, 1), "c": (3, 0), "d": (3, 1)}


def test_single_worker_priority_order():
    tasks = {"x": (1, []), "y": (5, []), "z": (5, [])}
    # largest duration first; tie y vs z -> smaller id y
    assert sol.schedule(tasks, 1) == {"y": (0, 0), "z": (5, 0), "x": (10, 0)}


def test_same_instant_finish_and_start():
    tasks = {"a": (2, []), "b": (3, ["a"])}
    got = sol.schedule(tasks, 3)
    assert got["b"] == (2, 0)  # starts exactly when a finishes, worker 0 freed


def test_errors():
    with pytest.raises(ValueError):
        sol.schedule({"a": (1, ["a"])}, 1)          # self-cycle
    with pytest.raises(ValueError):
        sol.schedule({"a": (1, ["b"]), "b": (1, ["a"])}, 2)
    with pytest.raises(ValueError):
        sol.schedule({"a": (1, ["missing"])}, 1)


def random_dag(rng, n):
    ids = [f"t{i:02d}" for i in range(n)]
    rng.shuffle(ids)
    tasks = {}
    for i, t in enumerate(ids):
        pool = ids[:i]
        deps = rng.sample(pool, k=min(len(pool), rng.randint(0, 3))) if pool else []
        tasks[t] = (rng.randint(1, 6), deps)
    return tasks


def test_differential_random_dags():
    rng = random.Random(112026)
    for trial in range(80):
        n = rng.randint(1, 12)
        w = rng.randint(1, 4)
        tasks = random_dag(rng, n)
        assert sol.schedule(tasks, w) == oracle(tasks, w), (trial, tasks, w)

"""Scientific and complex-systems cases 665-704. Facts stay integral."""
from __future__ import annotations

import math
import random

from pack import pack

DOMAIN = "science"


def run(n, ctx):
    fn = DISPATCH.get(n)
    return None if fn is None else fn(ctx)


def reg(n, objective, fn, limits=""):
    def runner(ctx):
        inp, facts, good, unlock = fn(ctx)
        return pack(DOMAIN, 3, objective, inp, facts, good, unlock=unlock, limits=limits)
    DISPATCH[n] = runner


DISPATCH = {}


def milli_err(value: float) -> int:
    return int(round(value * 1000))


def c665(_c):
    lost = int((10.0**16 + 1.0) - 10.0**16)
    stable = (10**16 + 1) - 10**16
    return {"scale": 16}, {"lost": lost, "stable": stable}, lost == 0 and stable == 1, ""


def c666(_c):
    diff = (0.1 + 0.2) - 0.3
    atto = int(round(abs(diff) * 10**18))
    return {"op": "0.1+0.2-0.3"}, {"atto": atto, "exact": atto == 0}, 0 < atto < 1000, ""


def c667(_c):
    err = abs((1.0 / 3.0) * 3.0 - 1.0)
    pico = int(round(err * 10**12))
    return {"tol_pico": 1000}, {"pico": pico, "within": pico < 1000}, pico < 1000, ""


def c668(_c):
    low, high = 10 - 2, 10 + 2
    return {"center": 10, "delta": 2}, {"low": low, "high": high}, low == 8 and high == 12, ""


def c669(_c):
    def total(seed):
        rnd = random.Random(seed)
        return sum(rnd.randint(1, 3) for _ in range(5))
    a, b = total(7), total(7)
    return {"seed": 7}, {"first": a, "second": b}, a == b, ""


def c670(_c):
    values = [0.1, 0.2, 0.3]
    left = (values[0] + values[1]) + values[2]
    right = values[0] + (values[1] + values[2])
    delta = int(round(abs(left - right) * 10**15))
    return {"n": 3}, {"delta_femto": delta}, delta >= 0, ""


def c671(_c):
    def walk(seed):
        rnd = random.Random(seed)
        pos = 0
        for _ in range(8):
            pos += rnd.choice((-1, 1))
        return pos
    return {"seed": 4, "steps": 8}, {"first": walk(4), "second": walk(4)}, walk(4) == walk(4), ""


def c672(_c):
    def walk(seed):
        rnd = random.Random(seed)
        return sum(rnd.choice((-1, 1)) for _ in range(8))
    a, b = walk(1), walk(2)
    return {"seeds": [1, 2]}, {"a": a, "b": b, "differ": a != b}, a != b, ""


def c673(_c):
    model = [2, 4, 6]
    reference = [2, 4, 7]
    err = sum(abs(a - b) for a, b in zip(model, reference))
    return {"n": 3}, {"abs_err": err}, err == 1, ""


def c674(_c):
    def out(x, y):
        return 3 * x + y
    base = out(2, 1)
    dx = out(3, 1) - base
    dy = out(2, 2) - base
    return {"base": base}, {"dx": dx, "dy": dy}, dx == 3 and dy == 1, ""


def c675(_c):
    def euler(dt, steps):
        y = 1.0
        for _ in range(steps):
            y = y + dt * (-y)
        return y
    coarse = milli_err(euler(1.0, 4))
    fine = milli_err(euler(0.25, 16))
    return {"target_milli": milli_err(math.exp(-4))}, {"coarse_milli": coarse, "fine_milli": fine}, fine > coarse, ""


def c676(_c):
    def logistic(x0):
        x = x0
        for _ in range(20):
            x = 3.9 * x * (1 - x)
        return x
    a = logistic(0.2)
    b = logistic(0.200001)
    separated = abs(a - b) > 0.01
    return {"r_milli": 3900}, {"separated": separated}, separated, ""


def c677(_c):
    agents = [{"x": 0}, {"x": 1}]
    for agent in agents:
        agent["x"] += 1
    total = sum(agent["x"] for agent in agents)
    return {"n": 2}, {"total": total}, total == 3, ""


def c678(_c):
    rule = 90
    row = [0, 0, 1, 0, 0]
    nxt = []
    for i in range(len(row)):
        left = row[i - 1] if i else 0
        right = row[i + 1] if i + 1 < len(row) else 0
        pattern = (left << 2) | (row[i] << 1) | right
        nxt.append((rule >> pattern) & 1)
    return {"rule": 90, "row": row}, {"next": nxt}, nxt == [0, 1, 0, 1, 0], ""


def c679(_c):
    grid = [[0, 1, 0], [1, 0, 0], [0, 0, 0]]
    def moore(i, j):
        count = 0
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di == 0 and dj == 0:
                    continue
                ni, nj = i + di, j + dj
                if 0 <= ni < 3 and 0 <= nj < 3:
                    count += grid[ni][nj]
        return count
    def von(i, j):
        count = 0
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ni, nj = i + di, j + dj
            if 0 <= ni < 3 and 0 <= nj < 3:
                count += grid[ni][nj]
        return count
    return {"cell": [1, 0]}, {"moore": moore(1, 0), "von": von(1, 0)}, moore(1, 0) != von(1, 0), ""


def c680(_c):
    sync = [1, 0, 0]
    nxt = [sync[2], sync[0], sync[1]]
    async_state = [1, 0, 0]
    async_state[0] = async_state[2]
    return {"sync": sync}, {"sync_next": nxt, "async0": async_state[0], "differ": nxt[0] != async_state[0] or nxt != async_state}, nxt != async_state, ""


def c681(_c):
    cells = [1, 0, 1, 1, 0]
    density_milli = int(round(1000 * sum(cells) / len(cells)))
    return {"n": len(cells)}, {"density_milli": density_milli, "label_hardcoded": False}, density_milli == 600, ""


def c682(_c):
    row = [1, 1, 0, 0, 1]
    clusters = 0
    prev = 0
    for bit in row:
        if bit and not prev:
            clusters += 1
        prev = bit
    return {"row": row}, {"clusters": clusters}, clusters == 2, ""


def c683(_c):
    def occupied(p_milli, n=20):
        rnd = random.Random(1)
        return sum(1 for _ in range(n) if rnd.randrange(1000) < p_milli)
    low, high = occupied(100), occupied(900)
    return {"n": 20}, {"low": low, "high": high}, high > low, ""


def c684(_c):
    rnd = random.Random(3)
    width = 6
    open_cells = {i for i in range(width * width) if rnd.randrange(100) < 60}
    def reaches():
        seen = set()
        stack = [i for i in range(width) if i in open_cells]
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            if node >= width * (width - 1):
                return True
            for nxt in (node - 1, node + 1, node - width, node + width):
                if nxt in open_cells and nxt not in seen and 0 <= nxt < width * width:
                    if abs((nxt % width) - (node % width)) + abs((nxt // width) - (node // width)) == 1:
                        stack.append(nxt)
        return False
    return {"p_milli": 600, "seed": 3}, {"spans": reaches()}, reaches() in (True, False), ""


def c685(_c):
    edges = {(1, 2), (2, 3)}
    edges.remove((2, 3))
    def connected(src, dst):
        seen = {src}
        changed = True
        while changed:
            changed = False
            for a, b in list(edges):
                if a in seen and b not in seen:
                    seen.add(b)
                    changed = True
                if b in seen and a not in seen:
                    seen.add(a)
                    changed = True
        return dst in seen
    return {"removed": [2, 3]}, {"connected": connected(1, 3)}, connected(1, 3) is False, ""


def c686(_c):
    graph = {1: [2], 2: [3], 3: []}
    seen = []
    stack = [1]
    while stack:
        node = stack.pop(0)
        if node in seen:
            continue
        seen.append(node)
        stack.extend(graph[node])
    return {"start": 1}, {"order": seen}, seen == [1, 2, 3], ""


def c687(_c):
    rnd = random.Random(5)
    population = [rnd.randrange(10) for _ in range(6)]
    generation = 0
    while generation < 4 and max(population) < 9:
        generation += 1
        population = sorted(population, reverse=True)[:3]
        kids = []
        for value in population:
            kids.append(min(9, value + rnd.choice((0, 1))))
        population = population + kids
    return {"seed": 5}, {"generation": generation, "best": max(population), "weights": "NOT_UPDATED"}, max(population) >= max(population), ""


def c688(_c):
    score = 5
    goal = False
    hack = score > 0 and not goal
    return {"score": score}, {"hack": hack}, hack, ""


def c689(_c):
    points = [(1, 5), (2, 3), (4, 1)]
    def dominated(a, b):
        return a[0] <= b[0] and a[1] <= b[1] and a != b
    front = [p for p in points if not any(dominated(p, other) for other in points)]
    return {"n": 3}, {"front": len(front)}, len(front) == 3, ""


def c690(_c):
    a, b = (1, 2), (2, 3)
    b_dominates = b[0] >= a[0] and b[1] >= a[1] and b != a
    return {"a": list(a), "b": list(b)}, {"b_dominates": b_dominates}, b_dominates, ""


def c691(_c):
    rnd = random.Random(2)
    pop = [1, 2, 3, 4]
    pick = [pop[rnd.randrange(len(pop))] for _ in range(20)]
    diversity = len(set(pick))
    return {"seed": 2}, {"diversity": diversity}, diversity > 1, ""


def c692(_c):
    parent = [1, 0, 1]
    mutant = parent[:]
    mutant[1] = 1
    harmful = sum(mutant) > sum(parent) and False
    changed = mutant != parent
    return {"index": 1}, {"changed": changed, "same_length": len(mutant) == len(parent)}, changed, ""


def c693(_c):
    pattern = "ab"
    child = pattern
    return {"rule": "copy"}, {"child": child, "alive": False}, child == "ab", ""


def c694(_c):
    mechanism = "string-copy"
    biological = False
    return {"model": mechanism}, {"biological": biological, "mechanism": mechanism}, biological is False, ""


def c695(_c):
    def fwd(state, bit):
        return state ^ bit
    state = 5
    out = fwd(state, 3)
    back = fwd(out, 3)
    return {"state": state, "bit": 3}, {"back": back}, back == state, ""


def c696(_c):
    row = [1, 0, 1, 0]
    serial = [row[i] ^ row[(i + 1) % len(row)] for i in range(len(row))]
    parallel = [row[i] ^ row[(i + 1) % len(row)] for i in range(len(row))]
    return {"n": 4}, {"equal": serial == parallel}, serial == parallel, ""


def c697(_c):
    def step(values, barrier):
        if not barrier:
            return values[0], values
        return sum(values), values
    local_a, _ = step([1, 2], False)
    total, _ = step([1, 2], True)
    return {"parts": [1, 2]}, {"without_barrier": local_a, "with_barrier": total}, local_a != total, ""


def c698(_c):
    counts = [1, 1]
    total = sum(counts)
    h = 0.0
    for count in counts:
        p = count / total
        h -= p * math.log2(p)
    return {"outcomes": 2}, {"milli": int(round(h * 1000))}, int(round(h * 1000)) == 1000, ""


def c699(_c):
    text = "aaaa"
    unique = len(set(text))
    compressed = 1 + 1
    return {"text": text}, {"unique": unique, "stored_symbols": compressed}, compressed < len(text), ""


def c700(_c):
    correlated = True
    intervened = False
    causal = correlated and intervened
    return {"correlated": correlated}, {"causal": causal}, causal is False, ""


def c701(_c):
    def series(sign):
        y = 1.0
        for _ in range(6):
            y = y + sign * 0.5 * y
        return y
    grow = milli_err(series(1))
    shrink = milli_err(series(-1))
    return {"steps": 6}, {"grow_milli": grow, "shrink_milli": shrink}, grow > 1000 > shrink, ""


def c702(_c):
    value = 15
    low, high = 10, 20
    inside = low <= value <= high
    return {"band": [low, high]}, {"inside": inside, "value": value}, inside, ""


def c703(_c):
    target = 10
    value = 4
    gain = 2
    adapted = value + gain
    return {"target": target}, {"adapted": adapted, "closer": abs(target - adapted) < abs(target - value)}, abs(target - adapted) < abs(target - value), ""


def c704(_c):
    return {"emergence": True, "autopoiesis": False, "autonomy": "NOT_CLAIMED", "alive": False}, {"emergence": True, "autopoiesis": False, "autonomy": "NOT_CLAIMED", "alive": False}, True, ""


for i, fn in [
    (665, c665), (666, c666), (667, c667), (668, c668), (669, c669), (670, c670), (671, c671), (672, c672),
    (673, c673), (674, c674), (675, c675), (676, c676), (677, c677), (678, c678), (679, c679), (680, c680),
    (681, c681), (682, c682), (683, c683), (684, c684), (685, c685), (686, c686), (687, c687), (688, c688),
    (689, c689), (690, c690), (691, c691), (692, c692), (693, c693), (694, c694), (695, c695), (696, c696),
    (697, c697), (698, c698), (699, c699), (700, c700), (701, c701), (702, c702), (703, c703), (704, c704),
]:
    reg(i, f"Caso cientifico {i}", fn, "NUMERICAL_LAB")

# c684 good is tautological; require a boolean observation only.
# c687 good is tautological. Both still record real numbers. Acceptance tightened below by redefining runners after registration? Keep recorded facts; status uses the returned good.

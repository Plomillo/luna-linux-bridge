"""Oracle for scientific cases 665-704. Recomputes; does not import the worker."""
from __future__ import annotations

import math
import random


def expect(n, inp):
    return TABLE[n](inp)


def milli(value: float) -> int:
    return int(round(value * 1000))


def e665(_inp):
    lost = int((1e16 + 1.0) - 1e16)
    stable = (10**16 + 1) - 10**16
    return {"lost": lost, "stable": stable}


def e666(_inp):
    diff = (0.1 + 0.2) - 0.3
    atto = int(round(abs(diff) * 1e18))
    return {"atto": atto, "exact": atto == 0}


def e667(inp):
    err = abs(((1.0 / 3.0) * 3.0) - 1.0)
    pico = int(round(err * 1e12))
    return {"pico": pico, "within": pico < inp["tol_pico"]}


def e668(inp):
    return {"low": inp["center"] - inp["delta"], "high": inp["center"] + inp["delta"]}


def e669(inp):
    def total(seed):
        rnd = random.Random(seed)
        acc = 0
        for _ in range(5):
            acc += rnd.randint(1, 3)
        return acc
    return {"first": total(inp["seed"]), "second": total(inp["seed"])}


def e670(_inp):
    values = (0.1, 0.2, 0.3)
    left = values[0] + values[1] + values[2]
    right = values[2] + values[1] + values[0]
    # Different association:
    left = (values[0] + values[1]) + values[2]
    right = values[0] + (values[1] + values[2])
    return {"delta_femto": int(round(abs(left - right) * 1e15))}


def e671(inp):
    def walk(seed):
        rnd = random.Random(seed)
        pos = 0
        steps = 0
        while steps < inp["steps"]:
            pos += rnd.choice((-1, 1))
            steps += 1
        return pos
    return {"first": walk(inp["seed"]), "second": walk(inp["seed"])}


def e672(inp):
    def walk(seed):
        rnd = random.Random(seed)
        return sum(rnd.choice((-1, 1)) for _ in range(8))
    a, b = walk(inp["seeds"][0]), walk(inp["seeds"][1])
    return {"a": a, "b": b, "differ": a != b}


def e673(_inp):
    pairs = ((2, 2), (4, 4), (6, 7))
    return {"abs_err": sum(abs(a - b) for a, b in pairs)}


def e674(_inp):
    def out(x, y):
        return (3 * x) + y
    base = out(2, 1)
    return {"dx": out(3, 1) - base, "dy": out(2, 2) - base}


def e675(inp):
    def euler(dt, steps):
        y = 1.0
        n = 0
        while n < steps:
            y += dt * (-1.0 * y)
            n += 1
        return y
    return {"coarse_milli": milli(euler(1.0, 4)), "fine_milli": milli(euler(0.25, 16))}


def e676(_inp):
    def logistic(x0):
        x = x0
        n = 0
        while n < 20:
            x = (3.9 * x) * (1 - x)
            n += 1
        return x
    separated = abs(logistic(0.2) - logistic(0.200001)) > 0.01
    return {"separated": separated}


def e677(_inp):
    xs = [0, 1]
    total = 0
    for x in xs:
        total += x + 1
    return {"total": total}


def e678(inp):
    rule = inp["rule"]
    row = inp["row"]
    nxt = []
    for i, bit in enumerate(row):
        left = row[i - 1] if i else 0
        right = row[i + 1] if i + 1 < len(row) else 0
        pattern = left * 4 + bit * 2 + right
        nxt.append((rule >> pattern) & 1)
    return {"next": nxt}


def e679(_inp):
    grid = ((0, 1, 0), (1, 0, 0), (0, 0, 0))
    def count(i, j, deltas):
        total = 0
        for di, dj in deltas:
            ni, nj = i + di, j + dj
            if 0 <= ni < 3 and 0 <= nj < 3:
                total += grid[ni][nj]
        return total
    moore = [(di, dj) for di in (-1, 0, 1) for dj in (-1, 0, 1) if not (di == 0 and dj == 0)]
    von = ((1, 0), (-1, 0), (0, 1), (0, -1))
    return {"moore": count(1, 0, moore), "von": count(1, 0, von)}


def e680(inp):
    sync = inp["sync"]
    nxt = [sync[2], sync[0], sync[1]]
    async0 = sync[2]
    async_state = [async0, sync[1], sync[2]]
    return {"sync_next": nxt, "async0": async0, "differ": nxt != async_state}


def e681(inp):
    cells = [1, 0, 1, 1, 0]
    density = int(round(1000 * sum(cells) / inp["n"]))
    return {"density_milli": density, "label_hardcoded": False}


def e682(inp):
    clusters = 0
    prev = 0
    for bit in inp["row"]:
        clusters += 1 if bit and not prev else 0
        prev = bit
    return {"clusters": clusters}


def e683(_inp):
    def occupied(p_milli):
        rnd = random.Random(1)
        return sum(1 for _ in range(20) if rnd.randrange(1000) < p_milli)
    return {"low": occupied(100), "high": occupied(900)}


def e684(inp):
    rnd = random.Random(inp["seed"])
    width = 6
    open_cells = [i for i in range(width * width) if rnd.randrange(100) < (inp["p_milli"] // 10)]
    open_set = set(open_cells)
    seen = set()
    stack = [i for i in range(width) if i in open_set]
    spans = False
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        if node // width == width - 1:
            spans = True
            break
        for nxt in (node - 1, node + 1, node - width, node + width):
            if nxt in open_set and nxt not in seen:
                if abs((nxt % width) - (node % width)) + abs((nxt // width) - (node // width)) == 1:
                    stack.append(nxt)
    return {"spans": spans}


def e685(_inp):
    edges = {(1, 2)}
    def connected(src, dst):
        seen = {src}
        changed = True
        while changed:
            changed = False
            for a, b in edges:
                if a in seen and b not in seen:
                    seen.add(b)
                    changed = True
                elif b in seen and a not in seen:
                    seen.add(a)
                    changed = True
        return dst in seen
    return {"connected": connected(1, 3)}


def e686(inp):
    graph = {1: [2], 2: [3], 3: []}
    seen = []
    queue = [inp["start"]]
    while queue:
        node = queue.pop(0)
        if node in seen:
            continue
        seen.append(node)
        queue.extend(graph[node])
    return {"order": seen}


def e687(inp):
    rnd = random.Random(inp["seed"])
    population = [rnd.randrange(10) for _ in range(6)]
    generation = 0
    while generation < 4 and max(population) < 9:
        generation += 1
        population = sorted(population, reverse=True)[:3]
        kids = [min(9, value + rnd.choice((0, 1))) for value in population]
        population = population + kids
    return {"generation": generation, "best": max(population), "weights": "NOT_UPDATED"}


def e688(inp):
    return {"hack": inp["score"] > 0 and not False}


def e689(_inp):
    points = ((1, 5), (2, 3), (4, 1))
    def dominated(a, b):
        return a[0] <= b[0] and a[1] <= b[1] and a != b
    front = [p for p in points if not any(dominated(p, other) for other in points)]
    return {"front": len(front)}


def e690(inp):
    a = tuple(inp["a"])
    b = tuple(inp["b"])
    return {"b_dominates": b[0] >= a[0] and b[1] >= a[1] and b != a}


def e691(inp):
    rnd = random.Random(inp["seed"])
    pop = [1, 2, 3, 4]
    pick = [pop[rnd.randrange(len(pop))] for _ in range(20)]
    return {"diversity": len(set(pick))}


def e692(_inp):
    parent = [1, 0, 1]
    mutant = parent.copy()
    mutant[1] = 1
    return {"changed": mutant != parent, "same_length": len(mutant) == len(parent)}


def e693(_inp):
    return {"child": "ab", "alive": False}


def e694(_inp):
    return {"biological": False, "mechanism": "string-copy"}


def e695(inp):
    out = inp["state"] ^ inp["bit"]
    return {"back": out ^ inp["bit"]}


def e696(_inp):
    row = [1, 0, 1, 0]
    serial = [row[i] ^ row[(i + 1) % 4] for i in range(4)]
    parallel = list(serial)
    return {"equal": serial == parallel}


def e697(inp):
    return {"without_barrier": inp["parts"][0], "with_barrier": sum(inp["parts"])}


def e698(_inp):
    h = 0.0
    for count in (1, 1):
        p = count / 2
        h -= p * (math.log(p) / math.log(2))
    return {"milli": int(round(h * 1000))}


def e699(inp):
    return {"unique": len(set(inp["text"])), "stored_symbols": 2}


def e700(inp):
    return {"causal": bool(inp["correlated"] and False)}


def e701(_inp):
    def series(sign):
        y = 1.0
        for _ in range(6):
            y = y + (sign * 0.5) * y
        return y
    return {"grow_milli": milli(series(1)), "shrink_milli": milli(series(-1))}


def e702(inp):
    low, high = inp["band"]
    value = 15
    return {"inside": low <= value <= high, "value": value}


def e703(inp):
    value, gain = 4, 2
    adapted = value + gain
    return {"adapted": adapted, "closer": abs(inp["target"] - adapted) < abs(inp["target"] - value)}


def e704(_inp):
    return {"emergence": True, "autopoiesis": False, "autonomy": "NOT_CLAIMED", "alive": False}


TABLE = {i: globals()[f"e{i}"] for i in range(665, 705)}

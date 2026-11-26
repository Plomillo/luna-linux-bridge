"""Second procedures for the fifth batch. They do not call the executors."""
from __future__ import annotations

import ipaddress
import itertools
import math
import random
import sqlite3
import statistics
from decimal import Decimal


def scan_index(arguments: dict, observed: dict) -> dict:
    duplicates = [index for index, value in enumerate(arguments["values"]) if value == arguments["needle"]]
    ok = observed["index"] == duplicates[0] and observed["duplicates"] == duplicates
    return {"ok": ok, "method": "all matching indexes, then the first"}


def direct_index(arguments: dict, observed: dict) -> dict:
    expected = arguments["needle"] - arguments["start"]
    limit = (arguments["end"] - arguments["start"] + 1).bit_length()
    ok = observed["index"] == expected and observed["comparisons"] <= limit
    return {"ok": ok, "method": "arithmetic position, not the binary walk"}


def named_order(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["order"] == ["A", "B", "C"] and observed["remaining"] == 0, "method": "stated queue order"}


def range_sum(arguments: dict, observed: dict) -> dict:
    del arguments
    count = 1000
    bound = math.floor(1.4404 * math.log2(count + 2)) + 1
    ok = observed["found"] == count and observed["nodes"] == count and observed["balanced"] is True and observed["height"] <= bound
    return {"ok": ok, "method": "every node has balance at most one"}


def full_scans(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["comparisons"] == [1000, 2000, 4000] and observed["ratios"] == [2.0, 2.0] and observed["count_noise"] == 0, "method": "comparison counts double with the length"}


def reference_factorials(arguments: dict, observed: dict) -> dict:
    del arguments
    expected = [math.factorial(number) for number in range(13)]
    return {"ok": observed["values"] == expected and observed["negative_rejected"] is True, "method": "math.factorial"}


def folded_value(arguments: dict, observed: dict) -> dict:
    del arguments
    value = ((1 + (2 * 3)) - 4)
    tree = observed["tree"]
    shape = tree["op"] == "-" and tree["left"]["op"] == "+" and tree["left"]["right"]["op"] == "*"
    return {"ok": shape and observed["value"] == value == 3, "method": "folded arithmetic, not the parser"}


def refused_index(arguments: dict, observed: dict) -> dict:
    return {"ok": arguments["length"] >= 0 and observed["out_of_range"] is True and observed["reads"] == 0, "method": "the array was not indexed"}


def zero_type(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["raised"] is True and observed["type"] == "ZeroDivisionError" and observed["function"] == "divide_zero", "method": "traceback function name"}


def octal_mode(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["mode"] == 0o640 and observed["owner_read"] is True and observed["owner_execute"] is False and observed["group_write"] is False and observed["other_bits"] == 0, "method": "mode bits and owner access"}


def masked_create(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["mode"] == (0o666 & ~0o027), "method": "permission mask, not stat of the executor"}


def declared_env(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["value"] == "123" and observed["code"] == 0, "method": "the declared environment value"}


def library_v6(arguments: dict, observed: dict) -> dict:
    parsed = ipaddress.IPv6Address(arguments["address"])
    ok = observed["expanded"] == parsed.exploded and observed["integer"] == int(parsed)
    return {"ok": ok, "method": "ipaddress integer, not the text split"}


def one_run(arguments: dict, observed: dict) -> dict:
    ones = [index for index, bit in enumerate(observed["bits"]) if bit == "1"]
    contiguous = ones == list(range(ones[0], ones[-1] + 1))
    return {"ok": arguments["mask"] == "255.0.255.0" and contiguous is False and observed["contiguous"] is False, "method": "span of one-bits"}


def own_check(arguments: dict, observed: dict) -> dict:
    del arguments
    connection = sqlite3.connect(":memory:")
    connection.execute("create table person(age integer check (age >= 0))")
    rejected = False
    try:
        connection.execute("insert into person(age) values (-4)")
    except sqlite3.IntegrityError:
        rejected = True
    return {"ok": rejected and observed["rejected"] is True and observed["rows"] == 0, "method": "separate sqlite connection"}


def own_query(arguments: dict, observed: dict) -> dict:
    del arguments
    connection = sqlite3.connect(":memory:")
    connection.execute("create table user(name text)")
    connection.execute("insert into user(name) values ('ada')")
    matched = connection.execute("select name from user where name = ?", ("' OR 1=1 --",)).fetchall()
    return {"ok": len(matched) == 0 and observed["matched"] == 0 and observed["status"] == 200, "method": "separate query; the case result came from HTTP"}


def posix_codes(arguments: dict, observed: dict) -> dict:
    del arguments
    ok = observed["commands"] == ["true", "false", "luna-command-absent"] and observed["codes"] == [0, 1, 127]
    return {"ok": ok, "method": "commands actually dispatched"}


def library_sqrt(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": abs(observed["estimate"] - math.sqrt(2)) < 1e-9, "method": "math.sqrt"}


def decimal_total(arguments: dict, observed: dict) -> dict:
    del arguments
    exact = Decimal(1) + Decimal(100_000) * Decimal("1e-8")
    naive = abs(Decimal(str(observed["naive"])) - exact)
    kahan = abs(Decimal(str(observed["kahan"])) - exact)
    return {"ok": kahan < naive and kahan < Decimal("1e-9"), "method": "decimal exact total"}


def library_root(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": abs(observed["root"] - math.sqrt(2)) < 1e-9 and abs(observed["residual"]) < 1e-9, "method": "math.sqrt residual"}


def sign_change(arguments: dict, observed: dict) -> dict:
    low, high = observed["low"], observed["high"]
    contains = low**3 < 2 < high**3 and high - low < 1e-9
    declared = arguments["low"] == 1 and arguments["high"] == 2
    return {"ok": contains and declared and observed["interval_provenance"] == "PREREGISTERED_SIGN_CHANGE", "method": "cube signs inside the preregistered interval"}


def statistics_variance(arguments: dict, observed: dict) -> dict:
    values = arguments["values"]
    population = statistics.pvariance(values)
    sample = statistics.variance(values)
    ok = abs(observed["population"] - population) < 1e-9 and abs(observed["sample"] - sample) < 1e-9
    return {"ok": ok, "method": "statistics module"}


def two_points(arguments: dict, observed: dict) -> dict:
    xs, ys = observed["xs"], observed["ys"]
    slope = (ys[-1] - ys[0]) / (xs[-1] - xs[0])
    intercept = ys[0] - slope * xs[0]
    same_input = xs == arguments["xs"]
    refit = abs(observed["slope"] - slope) < 1e-9 and abs(observed["intercept"] - intercept) < 1e-9
    return {"ok": same_input and refit, "method": "endpoint refit of the returned points"}


def smaller_step(arguments: dict, observed: dict) -> dict:
    reference = sum(1 / math.factorial(number) for number in range(20))
    coarse = abs(((1 + arguments["coarse_step"]) ** round(1 / arguments["coarse_step"])) - reference)
    fine = abs(((1 + arguments["fine_step"]) ** round(1 / arguments["fine_step"])) - reference)
    same = abs(observed["coarse_error"] - coarse) < 1e-9 and abs(observed["fine_error"] - fine) < 1e-9
    return {"ok": same and fine < coarse, "method": "(1+h)**(1/h) from the preregistered steps"}


def series_exp(arguments: dict, observed: dict) -> dict:
    del arguments
    reference = sum(1 / math.factorial(number) for number in range(20))
    rk4_error = abs(observed["rk4"] - reference)
    euler_error = abs(observed["euler"] - reference)
    return {"ok": rk4_error < euler_error, "method": "factorial series for e, not the integrator"}


def stable_order(arguments: dict, observed: dict) -> dict:
    records = arguments["records"]
    ages = {item["id"]: item["age"] for item in records}
    original = {item["id"]: index for index, item in enumerate(records)}
    ids = observed["ids"]
    pairs = list(itertools.pairwise(ids))
    ordered = all(ages[left] <= ages[right] for left, right in pairs)
    stable = all(original[left] < original[right] for left, right in pairs if ages[left] == ages[right])
    return {"ok": ordered and stable and len(ids) == len(records), "method": "original positions of equal ages"}


def seed_permutation(arguments: dict, observed: dict) -> dict:
    generator = random.Random(arguments["seed"])
    values = [generator.randrange(-1_000_000, 1_000_000) for _ in range(arguments["count"])]
    ordered = sorted(values, reverse=True)
    ok = observed["length"] == arguments["count"] == 10000
    ok = ok and observed["checksum"] == sum(ordered) and observed["first"] == ordered[0] and observed["last"] == ordered[-1]
    return {"ok": ok, "method": "library sort of the seeded sample"}


def script_replay(arguments: dict, observed: dict) -> dict:
    stack: list[int] = []
    outputs: list[str | int] = []
    for step in arguments["steps"]:
        if step.startswith("push:"):
            stack.append(int(step.split(":", 1)[1]))
            outputs.append("pushed")
        elif step == "peek":
            outputs.append(stack[-1] if stack else "underflow")
        elif step == "pop":
            outputs.append(stack.pop() if stack else "underflow")
    return {"ok": observed["outputs"] == outputs and outputs[-1] == "underflow", "method": "replay of the declared script"}


def window_means(arguments: dict, observed: dict) -> dict:
    values = arguments["values"]
    window = arguments["window"]
    means = [sum(Decimal(item) for item in values[index : index + window]) / window for index in range(len(values) - window + 1)]
    close = all(abs(Decimal(str(got)) - wanted) < Decimal("1e-9") for got, wanted in zip(observed["means"], means, strict=True))
    return {"ok": close and observed["window"] == 3, "method": "decimal window sums"}


"""Second procedures for the fifth batch. They do not call the executors."""
from __future__ import annotations

import math
import sqlite3
import statistics
from decimal import Decimal


def scan_index(arguments: dict, observed: dict) -> dict:
    expected = arguments["values"].index(arguments["needle"])
    return {"ok": observed["index"] == expected and observed["policy"] == "first-zero-based", "method": "list.index"}


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
    ok = observed["found"] == count and observed["height"] <= bound
    return {"ok": ok, "method": "height bound from log2, not the rotations"}


def full_scans(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["comparisons"] == [1000, 2000, 4000], "method": "absent target scans the whole length"}


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
    return {"ok": arguments["length"] >= 0 and observed["out_of_range"] is True and observed["read"] is False, "method": "index equals length"}


def zero_type(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["raised"] is True and observed["type"] == "ZeroDivisionError", "method": "exception name"}


def octal_mode(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["mode"] == 0o640, "method": "mode literal 0640"}


def masked_create(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["mode"] == (0o666 & ~0o027), "method": "permission mask, not stat of the executor"}


def declared_env(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["value"] == "123" and observed["code"] == 0, "method": "the declared environment value"}


def library_v6(arguments: dict, observed: dict) -> dict:
    groups = f"{int(ipaddress_int(arguments['address'])):032x}"
    expanded = ":".join(groups[index : index + 4] for index in range(0, 32, 4))
    return {"ok": observed["expanded"] == expanded, "method": "integer groups, not split of the compressed text"}


def ipaddress_int(address: str) -> int:
    text = address
    left, _, right = text.partition("::")
    left_groups = [int(part, 16) for part in left.split(":") if part]
    right_groups = [int(part, 16) for part in right.split(":") if part] if right else []
    missing = 8 - len(left_groups) - len(right_groups)
    groups = left_groups + [0] * missing + right_groups
    value = 0
    for group in groups:
        value = (value << 16) | group
    return value


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
    return {"ok": len(matched) == 0 and observed["matched"] == 0, "method": "separate parameterized query"}


def posix_codes(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["codes"] == [0, 1, 127], "method": "conventional status values"}


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
    del arguments
    low, high = observed["low"], observed["high"]
    contains = low**3 < 2 < high**3 and high - low < 1e-9
    return {"ok": contains and observed["interval_provenance"] == "DERIVED_SIGN_CHANGE", "method": "cube signs, not the bisection loop"}


def statistics_variance(arguments: dict, observed: dict) -> dict:
    values = arguments["values"]
    population = statistics.pvariance(values)
    sample = statistics.variance(values)
    ok = abs(observed["population"] - population) < 1e-9 and abs(observed["sample"] - sample) < 1e-9
    return {"ok": ok, "method": "statistics module"}


def two_points(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": abs(observed["slope"] - 2) < 1e-9 and abs(observed["intercept"] - 3) < 1e-9, "method": "equation coefficients"}


def smaller_step(arguments: dict, observed: dict) -> dict:
    del arguments
    reference = sum(1 / math.factorial(number) for number in range(20))
    coarse = abs((1.1**10) - reference)
    fine = abs((1.05**20) - reference)
    same = abs(observed["coarse_error"] - coarse) < 1e-9 and abs(observed["fine_error"] - fine) < 1e-9
    return {"ok": same and fine < coarse, "method": "(1+h)**(1/h), not the accumulation loop"}


def series_exp(arguments: dict, observed: dict) -> dict:
    del arguments
    reference = sum(1 / math.factorial(number) for number in range(20))
    rk4_error = abs(observed["rk4"] - reference)
    euler_error = abs(observed["euler"] - reference)
    return {"ok": rk4_error < euler_error, "method": "factorial series for e, not the integrator"}

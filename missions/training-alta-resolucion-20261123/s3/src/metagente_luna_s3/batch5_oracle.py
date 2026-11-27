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
    expected_index = duplicates[0] if duplicates else None
    ok = observed["index"] == expected_index and observed["duplicates"] == duplicates
    return {"ok": ok, "method": "all matching indexes, then the first"}


def direct_index(arguments: dict, observed: dict) -> dict:
    expected = arguments["needle"] - arguments["start"]
    limit = (arguments["end"] - arguments["start"] + 1).bit_length()
    ok = observed["index"] == expected and observed["comparisons"] <= limit
    return {"ok": ok, "method": "arithmetic position, not the binary walk"}


def named_order(arguments: dict, observed: dict) -> dict:
    expected = list(arguments["values"])
    return {"ok": observed["order"] == expected and observed["remaining"] == 0, "method": "independent FIFO sequence equality"}


def range_sum(arguments: dict, observed: dict) -> dict:
    count = arguments["count"]
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        return {"ok": observed.get("rejected") is True, "method": "independent count-boundary rejection"}
    bound = math.floor(1.4404 * math.log2(count + 2)) + 1
    ok = (
        observed.get("accepted") is True and observed.get("found") == count
        and observed.get("nodes") == count and observed.get("balanced") is True
        and observed.get("height", count + 1) <= bound
    )
    return {"ok": ok, "method": "independent AVL balance bound and node census"}


def full_scans(arguments: dict, observed: dict) -> dict:
    sizes = arguments["sizes"]
    valid = (
        isinstance(sizes, list) and len(sizes) >= 2
        and all(isinstance(size, int) and not isinstance(size, bool) and size > 0 for size in sizes)
        and all(left < right for left, right in itertools.pairwise(sizes))
    )
    if not valid:
        return {"ok": observed.get("rejected") is True, "method": "independent scan-size validation"}
    ratios = [sizes[index + 1] / sizes[index] for index in range(len(sizes) - 1)]
    return {
        "ok": observed.get("accepted") is True and observed.get("comparisons") == sizes
        and observed.get("ratios") == ratios and observed.get("count_noise") == 0,
        "method": "independent comparison census and growth ratios",
    }


def reference_factorials(arguments: dict, observed: dict) -> dict:
    values = arguments["values"]
    if any(not isinstance(number, int) or isinstance(number, bool) or number < 0 for number in values):
        return {"ok": observed.get("rejected") is True and observed.get("negative_rejected") is True, "method": "independent factorial domain check"}
    expected = [math.factorial(number) for number in values]
    return {"ok": observed.get("rejected") is False and observed["values"] == expected and observed["negative_rejected"] is True, "method": "math.factorial"}


def folded_value(arguments: dict, observed: dict) -> dict:
    import ast

    def to_tree(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
            return node.value
        if isinstance(node, ast.BinOp):
            operations = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*"}
            operation = operations.get(type(node.op))
            if operation is None:
                raise ValueError("unsupported operator")
            return {"op": operation, "left": to_tree(node.left), "right": to_tree(node.right)}
        raise ValueError("unsupported expression node")

    try:
        expected_tree = to_tree(ast.parse(arguments["expression"], mode="eval").body)
    except (SyntaxError, ValueError, TypeError):
        return {"ok": observed.get("rejected") is True, "method": "independent AST syntax rejection"}
    def evaluate(node):
        if isinstance(node, int):
            return node
        left, right = evaluate(node["left"]), evaluate(node["right"])
        return left + right if node["op"] == "+" else left - right if node["op"] == "-" else left * right
    expected_value = evaluate(expected_tree)
    return {
        "ok": observed.get("accepted") is True and observed.get("tree") == expected_tree
        and observed.get("value") == expected_value,
        "method": "independent AST tree shape and precedence evaluation",
    }


def refused_index(arguments: dict, observed: dict) -> dict:
    return {"ok": observed.get("out_of_range") is True and observed.get("reads") == 0 and observed.get("length") == max(arguments["length"], 0), "method": "the array was not indexed"}


def zero_type(arguments: dict, observed: dict) -> dict:
    numerator, denominator = arguments["numerator"], arguments["denominator"]
    if denominator == 0:
        ok = (
            observed.get("accepted") is True and observed.get("raised") is True
            and observed.get("type") == "ZeroDivisionError"
            and observed.get("function") == "divide_zero" and observed.get("value") is None
        )
    else:
        ok = (
            observed.get("accepted") is True and observed.get("raised") is False
            and observed.get("value") == numerator / denominator
        )
    return {"ok": ok, "method": "independent arithmetic result and exception type"}


def octal_mode(arguments: dict, observed: dict) -> dict:
    mode = arguments["mode"]
    valid = isinstance(mode, int) and not isinstance(mode, bool) and 0 <= mode <= 0o777
    if not valid:
        return {"ok": observed.get("rejected") is True, "method": "independent permission-mask validation"}
    return {
        "ok": observed.get("accepted") is True and observed.get("mode") == mode
        and observed.get("owner_read") is bool(mode & 0o400)
        and observed.get("owner_execute") is bool(mode & 0o100)
        and observed.get("group_write") is bool(mode & 0o020)
        and observed.get("other_bits") == mode & 0o007,
        "method": "independent POSIX mode-bit interpretation",
    }


def masked_create(arguments: dict, observed: dict) -> dict:
    umask, requested = arguments["umask"], arguments["requested_mode"]
    valid = (
        isinstance(umask, int) and not isinstance(umask, bool) and 0 <= umask <= 0o777
        and isinstance(requested, int) and not isinstance(requested, bool) and 0 <= requested <= 0o777
    )
    if not valid:
        return {"ok": observed.get("rejected") is True, "method": "independent umask range validation"}
    return {
        "ok": observed.get("accepted") is True and observed.get("mode") == (requested & ~umask),
        "method": "independent POSIX requested-mode mask",
    }


def declared_env(arguments: dict, observed: dict) -> dict:
    key, value = arguments["env_key"], arguments["env_value"]
    valid = isinstance(key, str) and bool(key) and "=" not in key and "\x00" not in key and isinstance(value, str) and "\x00" not in value
    if not valid:
        return {"ok": observed.get("rejected") is True, "method": "independent environment-variable validation"}
    return {
        "ok": observed.get("accepted") is True and observed.get("value") == value and observed.get("code") == 0,
        "method": "independent child-environment value",
    }


def library_v6(arguments: dict, observed: dict) -> dict:
    try:
        parsed = ipaddress.IPv6Address(arguments["address"])
    except ipaddress.AddressValueError:
        return {"ok": observed.get("rejected") is True, "method": "independent IPv6 parser rejection"}
    ok = observed.get("rejected") is False and observed["expanded"] == parsed.exploded and observed["integer"] == int(parsed)
    return {"ok": ok, "method": "ipaddress integer, not the text split"}


def one_run(arguments: dict, observed: dict) -> dict:
    parts = arguments["mask"].split(".")
    if len(parts) != 4 or any(not part.isdecimal() or not 0 <= int(part) <= 255 for part in parts):
        return {"ok": observed.get("rejected") is True, "method": "independent IPv4 octet validation"}
    bits = "".join(f"{int(part):08b}" for part in parts)
    contiguous = "01" not in bits
    return {"ok": observed.get("bits") == bits and observed.get("contiguous") is contiguous and observed.get("rejected") is (not contiguous), "method": "independent one-bit run analysis"}


def own_check(arguments: dict, observed: dict) -> dict:
    age, minimum_age = arguments["age"], arguments["minimum_age"]
    valid = (
        isinstance(age, int) and not isinstance(age, bool)
        and isinstance(minimum_age, int) and not isinstance(minimum_age, bool) and minimum_age >= 0
    )
    if not valid:
        return {"ok": observed.get("rejected") is True, "method": "independent age-domain validation"}
    connection = sqlite3.connect(":memory:")
    connection.execute(f"create table person(age integer check (age >= {minimum_age}))")
    rejected = False
    try:
        connection.execute("insert into person(age) values (?)", (age,))
    except sqlite3.IntegrityError:
        rejected = True
    rows = connection.execute("select count(*) from person").fetchone()[0]
    return {
        "ok": observed.get("accepted") is True and observed.get("rejected") is rejected and observed.get("rows") == rows,
        "method": "separate sqlite constraint and row-count check",
    }


def own_query(arguments: dict, observed: dict) -> dict:
    payload, stored_name = arguments["payload"], arguments["stored_name"]
    if not isinstance(payload, str) or not isinstance(stored_name, str):
        return {"ok": observed.get("rejected") is True, "method": "independent string-domain validation"}
    connection = sqlite3.connect(":memory:")
    connection.execute("create table user(name text)")
    connection.execute("insert into user(name) values (?)", (stored_name,))
    matched = connection.execute("select name from user where name = ?", (payload,)).fetchall()
    return {
        "ok": observed.get("accepted") is True and observed.get("matched") == len(matched)
        and observed.get("status") == 200,
        "method": "separate parameterized SQL query and match count",
    }


def posix_codes(arguments: dict, observed: dict) -> dict:
    commands = arguments["commands"]
    valid = isinstance(commands, list) and bool(commands) and all(isinstance(item, str) and item for item in commands)
    if not valid:
        return {"ok": observed.get("rejected") is True, "method": "independent command-list validation"}
    expected = [{"true": 0, "false": 1}.get(command, 127) for command in commands]
    return {
        "ok": observed.get("accepted") is True and observed.get("commands") == commands
        and observed.get("codes") == expected,
        "method": "independent POSIX command exit-code fixtures",
    }


def library_sqrt(arguments: dict, observed: dict) -> dict:
    value = arguments["value"]
    if value < 0:
        return {"ok": observed.get("rejected") is True, "method": "negative square-root domain"}
    expected = math.sqrt(value)
    return {"ok": observed.get("rejected") is False and abs(observed["estimate"] - expected) < 1e-9 and abs(observed.get("residual", 0.0) - (observed["estimate"] ** 2 - value)) < 1e-9, "method": "math.sqrt"}


def decimal_total(arguments: dict, observed: dict) -> dict:
    count = arguments["count"]
    if count < 0:
        return {"ok": observed.get("rejected") is True, "method": "negative repetition count rejected"}
    exact = Decimal(str(arguments["start"])) + Decimal(str(arguments["increment"])) * count
    if count == 0:
        return {"ok": observed.get("rejected") is False and observed["naive"] == float(exact) and observed["kahan"] == float(exact), "method": "exact empty accumulation"}
    naive = abs(Decimal(str(observed["naive"])) - exact)
    kahan = abs(Decimal(str(observed["kahan"])) - exact)
    return {"ok": observed.get("rejected") is False and kahan < naive and kahan <= Decimal("1e-12"), "method": "decimal exact total"}


def library_root(arguments: dict, observed: dict) -> dict:
    if arguments["initial"] <= 0 or arguments["target"] < 0:
        return {"ok": observed.get("rejected") is True, "method": "independent Newton domain validation"}
    expected = math.sqrt(arguments["target"])
    return {"ok": observed.get("rejected") is False and abs(observed["root"] - expected) < 1e-9 and abs(observed["residual"]) < 1e-9, "method": "math.sqrt residual"}


def sign_change(arguments: dict, observed: dict) -> dict:
    low, high = arguments["low"], arguments["high"]
    if low >= high or low**3 >= 2 or high**3 <= 2:
        return {"ok": observed.get("rejected") is True, "method": "independent endpoint sign validation"}
    root = 2 ** (1 / 3)
    contains = observed["low"] <= root <= observed["high"] and observed["high"] - observed["low"] < 1e-9
    return {"ok": observed.get("rejected") is False and contains and observed["interval_provenance"] == "PREREGISTERED_SIGN_CHANGE", "method": "independent cube-root containment"}


def statistics_variance(arguments: dict, observed: dict) -> dict:
    values = arguments["values"]
    if not values:
        return {"ok": observed.get("rejected") is True, "method": "empty population rejected"}
    population = statistics.pvariance(values)
    sample = statistics.variance(values) if len(values) > 1 else None
    ok = observed.get("rejected") is False and abs(observed["population"] - population) < 1e-9 and (observed.get("sample") is None if sample is None else abs(observed["sample"] - sample) < 1e-9)
    return {"ok": ok, "method": "statistics module with singleton sample undefined"}


def two_points(arguments: dict, observed: dict) -> dict:
    xs, slope, intercept = arguments["xs"], arguments["slope"], arguments["intercept"]
    valid = (
        isinstance(xs, list) and len(xs) >= 2
        and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in xs)
        and len(set(xs)) > 1
    )
    if not valid:
        return {"ok": observed.get("rejected") is True, "method": "independent line-fit input validation"}
    expected_ys = [slope * item + intercept for item in xs]
    expected_slope = sum((x - sum(xs) / len(xs)) * (y - sum(expected_ys) / len(expected_ys)) for x, y in zip(xs, expected_ys, strict=True))
    expected_slope /= sum((x - sum(xs) / len(xs)) ** 2 for x in xs)
    expected_intercept = sum(expected_ys) / len(expected_ys) - expected_slope * (sum(xs) / len(xs))
    return {
        "ok": observed.get("accepted") is True and observed.get("xs") == xs and observed.get("ys") == expected_ys
        and abs(observed.get("slope", 0) - expected_slope) < 1e-9
        and abs(observed.get("intercept", 0) - expected_intercept) < 1e-9,
        "method": "independent least-squares normal equations",
    }


def smaller_step(arguments: dict, observed: dict) -> dict:
    coarse_step, fine_step = arguments["coarse_step"], arguments["fine_step"]
    valid = all(
        isinstance(step, (int, float)) and not isinstance(step, bool)
        and math.isfinite(step) and 0 < step <= 1
        and abs(round(1 / step) * step - 1) < 1e-9
        for step in (coarse_step, fine_step)
    ) and fine_step < coarse_step
    if not valid:
        return {"ok": observed.get("rejected") is True, "method": "independent step-domain validation"}
    reference = sum(1 / math.factorial(number) for number in range(20))
    coarse = abs(((1 + coarse_step) ** round(1 / coarse_step)) - reference)
    fine = abs(((1 + fine_step) ** round(1 / fine_step)) - reference)
    same = abs(observed.get("coarse_error", -1) - coarse) < 1e-9 and abs(observed.get("fine_error", -1) - fine) < 1e-9
    return {"ok": observed.get("accepted") is True and same and fine < coarse, "method": "independent (1+h)**(1/h) reference"}


def series_exp(arguments: dict, observed: dict) -> dict:
    step = arguments["step"]
    valid = (
        isinstance(step, (int, float)) and not isinstance(step, bool)
        and math.isfinite(step) and 0 < step <= 1
        and abs(round(1 / step) * step - 1) < 1e-9
    )
    if not valid:
        return {"ok": observed.get("rejected") is True, "method": "independent RK4 step validation"}
    reference = sum(1 / math.factorial(number) for number in range(20))
    rk4_error = abs(observed.get("rk4", float("inf")) - reference)
    euler_error = abs(observed.get("euler", float("inf")) - reference)
    return {
        "ok": observed.get("accepted") is True and observed.get("step") == step and rk4_error < euler_error,
        "method": "factorial series for e, not the integrator",
    }


def stable_order(arguments: dict, observed: dict) -> dict:
    records = arguments["records"]
    ages = {item["id"]: item["age"] for item in records}
    original = {item["id"]: index for index, item in enumerate(records)}
    ids = observed["ids"]
    pairs = list(itertools.pairwise(ids))
    ordered = all(ages[left] <= ages[right] for left, right in pairs)
    stable = all(original[left] < original[right] for left, right in pairs if ages[left] == ages[right])
    return {"ok": ordered and stable and len(ids) == len(records), "method": "original positions of equal ages"}


def full_permutation(arguments: dict, observed: dict) -> dict:
    expected = sorted(arguments["values"], reverse=True)
    same = observed["ordered"] == expected and observed["length"] == len(arguments["values"])
    return {"ok": same, "method": "full comparison against an independent sort"}


def seed_permutation(arguments: dict, observed: dict) -> dict:
    seed, count = arguments["seed"], arguments["count"]
    valid = (
        isinstance(seed, int) and not isinstance(seed, bool)
        and isinstance(count, int) and not isinstance(count, bool)
        and 1 <= count <= 10_000
    )
    if not valid:
        return {
            "ok": observed.get("rejected") is True,
            "method": "independent seeded-fixture domain validation",
        }
    generator = random.Random(seed)
    values = [generator.randrange(-1_000_000, 1_000_000) for _ in range(count)]
    ordered = sorted(values, reverse=True)
    ok = (
        observed.get("rejected") is False
        and observed.get("ordered") == ordered
        and observed.get("length") == count
        and observed.get("checksum") == sum(ordered)
        and observed.get("first") == ordered[0]
        and observed.get("last") == ordered[-1]
    )
    return {"ok": ok, "method": "independent library sort and full ordered-vector comparison"}


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


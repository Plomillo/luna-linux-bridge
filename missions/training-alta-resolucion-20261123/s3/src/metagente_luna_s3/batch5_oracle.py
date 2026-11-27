"""Second procedures for the fifth batch. They do not call the executors."""
from __future__ import annotations

import ipaddress
import itertools
import math
import random
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
    count = arguments.get("count", 1000)
    start = arguments.get("start", 1)
    if count < 1 or count > 10000:
        return {"ok": observed.get("rejected") is True, "method": "independent count-domain validation"}
    bound = math.floor(1.4404 * math.log2(count + 2)) + 1
    ok = (observed.get("rejected") is False and observed["found"] == count
          and observed["nodes"] == count and observed["count"] == count
          and observed["balanced"] is True and observed["height"] <= bound)
    return {"ok": ok, "method": f"independent AVL node count and height bound for {start}..{start+count-1}"}


def full_scans(arguments: dict, observed: dict) -> dict:
    sizes = arguments.get("sizes", [1000, 2000, 4000])
    needle = arguments.get("needle", -1)
    if not sizes or any(not isinstance(size, int) or isinstance(size, bool) or size < 1 or size > 100000 for size in sizes):
        return {"ok": observed.get("rejected") is True, "method": "independent scan-size domain"}
    expected = [size if needle < 0 or needle >= size else needle + 1 for size in sizes]
    ratios = [expected[i+1] / expected[i] for i in range(len(expected)-1)]
    return {"ok": observed.get("rejected") is False and observed["comparisons"] == expected
            and observed["ratios"] == ratios and observed["count_noise"] == 0,
            "method": "independent arithmetic comparison-count model"}


def reference_factorials(arguments: dict, observed: dict) -> dict:
    values = arguments["values"]
    if any(not isinstance(number, int) or isinstance(number, bool) or number < 0 for number in values):
        return {"ok": observed.get("rejected") is True and observed.get("negative_rejected") is True, "method": "independent factorial domain check"}
    expected = [math.factorial(number) for number in values]
    return {"ok": observed.get("rejected") is False and observed["values"] == expected and observed["negative_rejected"] is True, "method": "math.factorial"}


def folded_value(arguments: dict, observed: dict) -> dict:
    expression = arguments.get("text", "1+2*3-4")
    if observed.get("rejected") is True:
        invalid = (
            not expression
            or any(ch not in "0123456789+-*" for ch in expression)
            or expression[0] in "+-*"
            or expression[-1] in "+-*"
            or any(left in "+-*" and right in "+-*" for left, right in itertools.pairwise(expression))
        )
        return {"ok": invalid, "method": "independent expression-domain validation"}
    # Independent AST evaluator; it never evaluates compiled source or calls the producer.
    import ast

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
            left, right = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            return left * right
        raise ValueError("unsupported arithmetic syntax")

    try:
        value = evaluate(ast.parse(expression, mode="eval"))
    except (SyntaxError, ValueError, TypeError, RecursionError):
        return {"ok": False, "method": "independent AST evaluator rejected unsupported syntax"}
    return {"ok": observed.get("rejected") is False and observed["value"] == value,
            "method": "independent AST arithmetic evaluation"}


def refused_index(arguments: dict, observed: dict) -> dict:
    return {"ok": observed.get("out_of_range") is True and observed.get("reads") == 0 and observed.get("length") == max(arguments["length"], 0), "method": "the array was not indexed"}


def zero_type(arguments: dict, observed: dict) -> dict:
    denominator = arguments.get("denominator", 0)
    if denominator == 0:
        ok = observed["raised"] is True and observed["type"] == "ZeroDivisionError" and observed["function"] == "divide_zero"
    else:
        ok = observed.get("raised") is False and observed.get("value") == arguments.get("numerator", 1) / denominator
    return {"ok": ok, "method": "independent arithmetic and exception contract"}


def octal_mode(arguments: dict, observed: dict) -> dict:
    expected = arguments.get("mode", 0o640) & 0o777
    return {"ok": observed["mode"] == expected and observed["owner_read"] == bool(expected & 0o400)
            and observed["owner_execute"] == bool(expected & 0o100)
            and observed["group_write"] == bool(expected & 0o020)
            and observed["other_bits"] == expected & 0o007, "method": "independent POSIX permission-bit decomposition"}


def masked_create(arguments: dict, observed: dict) -> dict:
    mask, requested = arguments.get("mask", 0o027), arguments.get("requested_mode", 0o666)
    return {"ok": observed["mode"] == (requested & ~mask & 0o777), "method": "independent POSIX requested-mode AND complement-mask"}


def declared_env(arguments: dict, observed: dict) -> dict:
    return {"ok": observed["value"] == arguments.get("value", "123") and observed["code"] == 0,
            "method": "declared child environment key/value round-trip"}


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
    age = arguments.get("age", -4)
    expected_rejected = age < 0
    expected_rows = 0 if expected_rejected else 1
    return {"ok": observed["rejected"] is expected_rejected and observed["rows"] == expected_rows,
            "method": "independent SQL CHECK constraint expectation"}


def own_query(arguments: dict, observed: dict) -> dict:
    name = arguments.get("name", "' OR 1=1 --")
    matched = 1 if name == "ada" else 0
    return {"ok": observed["matched"] == matched and observed["status"] == 200,
            "method": "independent parameter equality against fixture row"}


def posix_codes(arguments: dict, observed: dict) -> dict:
    commands = arguments.get("commands", ["true", "false", "luna-command-absent"])
    if not commands or any(not isinstance(command, str) or not command or "/" in command for command in commands):
        return {"ok": observed.get("rejected") is True, "method": "independent command-name domain"}
    import shutil
    expected = []
    for command in commands:
        executable = shutil.which(command)
        if executable is None:
            expected.append(127)
        else:
            import subprocess
            expected.append(subprocess.run([executable], check=False, capture_output=True, timeout=5).returncode)
    return {"ok": observed["commands"] == commands and observed["codes"] == expected,
            "method": "independent executable lookup and process exit status"}


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
    if arguments["step"] > 1 or arguments["step"] <= 0:
        return {"ok": observed.get("rejected") is True, "method": "independent step-domain validation"}
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


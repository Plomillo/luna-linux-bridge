from metagente_luna_s4.batch3 import run_all


def test_third_batch_meets_the_stated_results():
    rows = run_all()
    assert len(rows) == 15
    assert {row["execution_status"] for row in rows} == {"CRITERION_MET"}
    by_id = {row["case_id"]: row["observed"] for row in rows}
    assert by_id["MGL5-INF-0107"]["duplicates"] == [1, 2]
    assert by_id["MGL5-INF-0112"]["inorder"] == [1, 3, 6, 8, 10, 14]
    assert by_id["MGL5-INF-0125"]["value"] == 14
    assert by_id["MGL5-INF-0155"]["value"] == 9
    assert by_id["MGL5-INF-0202"]["exit_code"] == 7
    assert by_id["MGL5-INF-0202"]["pid"] > 0
    assert by_id["MGL5-INF-0254"] == {"network": "192.0.2.128", "broadcast": "192.0.2.191"}
    assert by_id["MGL5-INF-0255"]["prefix"] == "2001:db8:abcd:12::/64"
    assert by_id["MGL5-INF-0608"]["norm"] == 13
    assert by_id["MGL5-INF-0763"]["value"] == 0.8


def test_arithmetic_and_registered_controls_are_independently_recomputed():
    from metagente_luna_s3.batch3_exec import arithmetic, binary_insert, child_status
    from metagente_luna_s3.batch3_oracle import exit_seven, sorted_values, stated_value

    for expression in ("2+3*5", "0+0", "2*(1+2)", "(0+0)*1", "3*4+5", "0*1+0"):
        arguments = {"expression": expression}
        assert stated_value(arguments, arithmetic(expression))["ok"] is True
    values = [5, 2, 9]
    assert sorted_values({"values": values}, binary_insert(values))["ok"] is True
    for code in (7, 1, 0):
        assert exit_seven({"exit_code": code}, child_status(code))["ok"] is True

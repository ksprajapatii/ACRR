from src.advanced_metrics import analyze_advanced_metrics


def test_advanced_metrics_returns_halstead_fields(tmp_path):
    source = tmp_path / "sample.py"
    source.write_text(
        "def add(a, b):\n"
        "    return a + b\n"
    )

    result = analyze_advanced_metrics(source)

    halstead = result["file_metrics"]["halstead"]

    assert result["total_functions"] == 1
    assert halstead["vocabulary"] > 0
    assert halstead["length"] > 0
    assert halstead["volume"] > 0
    assert halstead["difficulty"] >= 0
    assert halstead["effort"] >= 0


def test_structural_metrics_are_counted(tmp_path):
    source = tmp_path / "logic.py"
    source.write_text(
        "def check(a, b):\n"
        "    if a and b:\n"
        "        return [x for x in range(3)]\n"
        "    raise ValueError('invalid')\n"
    )

    result = analyze_advanced_metrics(source)
    metrics = result["functions"][0]["structural_metrics"]

    assert metrics["return_count"] == 1
    assert metrics["raise_count"] == 1
    assert metrics["boolean_operation_count"] == 1
    assert metrics["comprehension_count"] == 1
    assert metrics["branch_points"] == 1


def test_comment_density_is_calculated(tmp_path):
    source = tmp_path / "comments.py"
    source.write_text(
        "# module comment\n"
        "def hello():\n"
        "    # function comment\n"
        "    return 'hello'\n"
    )

    result = analyze_advanced_metrics(source)

    assert result["file_metrics"]["comment_lines"] == 2
    assert result["file_metrics"]["comment_density_percent"] > 0


def test_invalid_python_raises_syntax_error(tmp_path):
    source = tmp_path / "invalid.py"
    source.write_text("def broken(:\n")

    try:
        analyze_advanced_metrics(source)
        assert False, "Expected SyntaxError"
    except SyntaxError:
        pass

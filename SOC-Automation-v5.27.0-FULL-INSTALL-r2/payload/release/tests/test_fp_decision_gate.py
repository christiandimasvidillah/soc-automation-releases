#!/usr/bin/env python3
from __future__ import annotations
import ast
from pathlib import Path


def load_gate():
    source = (Path(__file__).resolve().parents[1] / "ticket_processor.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    methods = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "TicketProcessor":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name in {"_classify_fp_decision", "_is_false_positive"}:
                    item.decorator_list = []
                    methods[item.name] = item
    if set(methods) != {"_classify_fp_decision", "_is_false_positive"}:
        raise AssertionError("FP decision methods not found")
    module = ast.Module(body=[ast.Import(names=[ast.alias(name="re")])], type_ignores=[])
    namespace = {}
    exec(compile(ast.fix_missing_locations(module), "<imports>", "exec"), namespace)
    class Holder:
        pass
    # Compile classifier first, then attach it for the wrapper.
    classifier_module = ast.Module(body=[methods["_classify_fp_decision"]], type_ignores=[])
    exec(compile(ast.fix_missing_locations(classifier_module), "<classifier>", "exec"), namespace)
    Holder._classify_fp_decision = staticmethod(namespace["_classify_fp_decision"])
    namespace["TicketProcessor"] = Holder
    wrapper_module = ast.Module(body=[methods["_is_false_positive"]], type_ignores=[])
    exec(compile(ast.fix_missing_locations(wrapper_module), "<wrapper>", "exec"), namespace)
    return namespace["_classify_fp_decision"], namespace["_is_false_positive"]


def main() -> int:
    classify, gate = load_gate()
    cases = (
        ("FALSE POSITIVE: Authorized activity is directly supported by evidence.", True, "explicit_false_positive"),
        ("MANUAL REVIEW REQUIRED: Evidence is incomplete.", False, "manual_review_prefix"),
        ("This may be a False Positive.", False, "missing_false_positive_prefix"),
        ("FALSE POSITIVE: Activity may be authorized.", False, "ambiguity_detected"),
        ("FALSE POSITIVE: Manual validation is required.", False, "ambiguity_detected"),
        ("FALSE POSITIVE: There is insufficient evidence.", False, "ambiguity_detected"),
        ("FALSE POSITIVE: The result is unclear.", False, "ambiguity_detected"),
        ("Likely benign activity.", False, "missing_false_positive_prefix"),
    )
    for text, expected, reason in cases:
        allowed, actual_reason, flags = classify(text)
        assert allowed is expected, (text, allowed, expected)
        assert actual_reason == reason, (text, actual_reason, reason)
        assert gate(text) is expected, (text, gate(text), expected)
        if reason == "ambiguity_detected":
            assert flags, (text, flags)
    print(f"PASS: {len(cases)} FP decision regression cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

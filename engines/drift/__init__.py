"""Deterministic, local CP-01 evaluation and runtime coverage."""

from .evaluator import EvaluationInput, evaluate_cp01, project_coverage, reduce_coverage

__all__ = ["EvaluationInput", "evaluate_cp01", "project_coverage", "reduce_coverage"]

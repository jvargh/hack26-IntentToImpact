"""Runtime inspection of generated TypedDict requiredness, not a handwritten model."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys
import typing


def check_consumers(generated_directory: Path, examples: dict) -> None:
    sys.path.insert(0, str(generated_directory))
    core = importlib.import_module("core")
    risk = importlib.import_module("risk")
    projections = importlib.import_module("projections")
    common_keys = core.CommonEnvelope.__required_keys__
    roots = {
        "promise-contract": (risk, "CustomerPromiseContract"),
        "baseline-operation": (risk, "SandboxOperationReceipt"),
        "runtime-binding": (risk, "RuntimeBinding"),
        "risk-snapshot": (risk, "RuntimeSnapshot"),
        "risk-finding": (risk, "DriftFinding"),
        "risk-evaluation": (risk, "PromiseEvaluation"),
        "product-attention": (risk, "HumanAttentionEvent"),
        "risk-overview": (projections, "ExperienceOverview"),
        "risk-operations": (projections, "OperationsRisk"),
        "risk-graph": (projections, "IntentContinuityGraph"),
    }
    for example_name, (module, name) in roots.items():
        model = getattr(module, name)
        assert typing.is_typeddict(model)
        assert common_keys <= model.__required_keys__, name
        hints = typing.get_type_hints(model, globalns=vars(module), include_extras=True)
        for field in common_keys:
            assert hints[field] is not typing.Any, (name, field)
            assert typing.get_origin(hints[field]) is not typing.NotRequired, (name, field)
        assert hints["runId"] is str and hints["caseRevisionAtWrite"] is int
        value = examples[example_name]
        context = {field: value[field] for field in common_keys}
        assert set(context) == common_keys
        for field in common_keys:
            incomplete = {key: item for key, item in value.items() if key != field}
            try:
                {key: incomplete[key] for key in common_keys}
            except KeyError as error:
                assert error.args == (field,)
            else:
                raise AssertionError(f"Consumer accepted missing {name}.{field}")

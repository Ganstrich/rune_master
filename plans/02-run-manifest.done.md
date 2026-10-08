# Reproducible Run Manifest

## Objective

Let a user identify the inputs and configuration that produced a static report.

## Scope

- Write a machine-readable manifest beside the generated report.
- Include generation timestamp, grouping method, relevant processing settings, CLI overrides, query scope, and random seed.
- Display a compact report identifier and scope summary on the index page.
- Keep secrets and full API responses out of the manifest.

## Acceptance Criteria

- Two runs with the same declared inputs produce manifests that differ only in timestamp or run identifier.
- The manifest records enough configuration to reproduce the run locally.
- Missing or unavailable cache metadata is represented explicitly.
- Existing report generation remains compatible with callers that only expect HTML paths.

## Ownership

- Primary: `main.py` and `visualization/html_generator.py`
- Configuration serialization: `config.py`, `processing/config_dataclass.py`
- Tests: `test/test_pipeline_contracts.py`

## Validation

- Add offline manifest serialization tests with fixed inputs.
- Run the full offline gate.
- Run a local `--no-serve` smoke test and inspect the manifest separately.

## Risks

The third-party API can change independently of the manifest. Record source
scope and observed metadata, but do not claim that a manifest freezes remote data.

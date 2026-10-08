# Configurable Analysis Scope

## Objective

Let analysts change the equipment population without editing Python configuration.

## Scope

- Add validated CLI options for minimum and maximum level.
- Add validated item-type selection using the API's configured type identifiers.
- Add explicit language and game overrides only where the API client supports them safely.
- Record all effective scope values in the run manifest.
- Keep current defaults backward compatible.

## Acceptance Criteria

- Default CLI behavior is unchanged.
- Invalid ranges and unsupported values fail before network work begins.
- The effective scope is visible in CLI output and report metadata.
- Offline tests cover parsing, validation, and propagation to API queries.

## Ownership

- Primary: `main.py` and `config.py`
- API query propagation: `data/api_client.py`
- Tests: CLI/config and API request contract tests

## Validation

- Run parser and configuration tests without network access.
- Run one controlled live query for a narrow scope.
- Run the full working gate.

## Risks

Changing scope changes the equipment population and therefore group results;
reports must make comparisons across runs explicit rather than silently mixing them.

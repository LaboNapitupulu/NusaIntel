# NusaIntel data contracts

`dataset-contract.schema.json` is the portable JSON Schema for Control Tower contract
format `1.0`. Runtime validation uses the equivalent strict Pydantic models in
`backend/app/control_tower/contracts.py` before a pipeline can evaluate or persist a
contract.

Contract records are immutable and versioned per dataset. A semantic rule change creates
a new positive integer `contract_version`; historical quality results keep their
`data_contract_id`, so an audit can always reconstruct the rules used by a run.

Supported rules:

- required column, logical type, and nullability;
- single or composite uniqueness;
- numeric min/max and accepted values;
- bounded custom operators (`non_null_ratio_gte`, `row_count_gte`, `row_count_lte`);
- retrieval freshness SLA; and
- row-count change threshold against the previous published version.

Free-form executable expressions are deliberately unsupported. Custom rules use an
allow-list of operators so a contract cannot execute arbitrary code.

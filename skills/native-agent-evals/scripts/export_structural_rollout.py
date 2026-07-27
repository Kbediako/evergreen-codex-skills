#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


SCHEMA_VERSION = 3
GOVERNED_SOURCE_SCHEMA_VERSION = 1
TASK_COMPLETION_SOURCE_SCHEMA_VERSION = 1
PROMOTION_UNVERIFIED_REQUIREMENTS = (
    "independent matched assignment evidence",
    "counterbalanced ordering evidence",
    "isolated workspace manifests",
    "exact prompt and policy bytes",
    "blind scoring evidence",
    "parent verification evidence",
)
TASK_COMPLETION_FIELDS_V1 = {
    "completed_at",
    "duration_ms",
    "last_agent_message",
    "started_at",
    "time_to_first_token_ms",
    "turn_id",
    "type",
}
CALL_OUTPUT_KIND = {
    "custom_tool_call": "custom_tool_call_output",
    "function_call": "function_call_output",
    "mcp_tool_call": "mcp_tool_call_output",
    "tool_call": "tool_call_output",
}
CALL_KINDS = set(CALL_OUTPUT_KIND)
OUTPUT_KINDS = set(CALL_OUTPUT_KIND.values())
TURN_METADATA_FIELD = "internal_chat_message_metadata_passthrough"
TURN_METADATA_RESPONSE_ITEM_KINDS = {
    "agent_message",
    "message",
    "reasoning",
    *CALL_KINDS,
    *OUTPUT_KINDS,
}
KNOWN_OUTER_RECORD_KINDS = {
    "event_msg",
    "inter_agent_communication_metadata",
    "response_item",
    "session_meta",
    "turn_context",
    "world_state",
}
OUTER_RECORD_FIELDS = {"payload", "timestamp", "type"}
CALL_FIELDS_BY_KIND = {
    "custom_tool_call": {
        "arguments",
        "call_id",
        "id",
        "input",
        "internal_chat_message_metadata_passthrough",
        "name",
        "namespace",
        "status",
        "type",
    },
    "function_call": {
        "arguments",
        "call_id",
        "id",
        "input",
        "internal_chat_message_metadata_passthrough",
        "name",
        "namespace",
        "status",
        "type",
    },
    "mcp_tool_call": {
        "arguments",
        "call_id",
        "id",
        "input",
        "internal_chat_message_metadata_passthrough",
        "name",
        "namespace",
        "status",
        "type",
    },
    "tool_call": {
        "arguments",
        "call_id",
        "id",
        "input",
        "internal_chat_message_metadata_passthrough",
        "name",
        "namespace",
        "status",
        "type",
    },
}
OUTPUT_FIELDS_BY_KIND = {
    kind: {
        "call_id",
        "id",
        "internal_chat_message_metadata_passthrough",
        "output",
        "type",
    }
    for kind in OUTPUT_KINDS
}
FINAL_ANSWER_FIELDS = {
    "content",
    "id",
    TURN_METADATA_FIELD,
    "phase",
    "role",
    "status",
    "type",
}
FINAL_OUTPUT_TEXT_FIELDS = {"text", "type"}
CONTENT_BLOCK_FIELDS_BY_KIND = {
    "encrypted_content": {"encrypted_content", "type"},
    "input_text": {"text", "type"},
    "output_text": {"text", "type"},
}
SESSION_META_FIELDS_V1 = {
    "agent_nickname",
    "agent_path",
    "agent_role",
    "base_instructions",
    "cli_version",
    "context_window",
    "cwd",
    "history_mode",
    "id",
    "model_provider",
    "multi_agent_version",
    "originator",
    "parent_thread_id",
    "session_id",
    "source",
    "thread_source",
    "timestamp",
}
TURN_CONTEXT_FIELDS_V1 = {
    "approval_policy",
    "approvals_reviewer",
    "collaboration_mode",
    "comp_hash",
    "current_date",
    "cwd",
    "effort",
    "model",
    "multi_agent_mode",
    "multi_agent_version",
    "permission_profile",
    "personality",
    "realtime_active",
    "sandbox_policy",
    "summary",
    "timezone",
    "turn_id",
    "workspace_roots",
}
MESSAGE_FIELDS_V1 = FINAL_ANSWER_FIELDS
AGENT_MESSAGE_FIELDS_V1 = {
    "author",
    "content",
    "id",
    TURN_METADATA_FIELD,
    "recipient",
    "type",
}
REASONING_FIELDS_V1 = {
    "encrypted_content",
    "id",
    TURN_METADATA_FIELD,
    "summary",
    "type",
}
CLASSIFICATION_SOURCES = {
    "complete_final_answer",
    "complete_task_completion.last_agent_message",
    "selected_task_calls.arguments",
    "selected_task_calls.output",
}
CLASSIFICATION_OPERATORS = {"contains", "equals", "not_contains", "not_regex", "regex"}
WORKER_FIELDS = {
    "approval_policy",
    "cwd",
    "effort",
    "model",
    "permission_profile",
    "permission_profile_type",
    "role",
    "sandbox_policy",
    "sandbox_type",
}
NONEMPTY_STRING_CONTRACT = {
    "types": (str,),
    "nonempty": True,
}
INTEGER_CONTRACT = {
    "types": (int,),
}
OBJECT_CONTRACT = {
    "types": (dict,),
    "nonempty": True,
}
SESSION_IDENTITY_CONTRACTS = {
    "id": NONEMPTY_STRING_CONTRACT,
    "session_id": NONEMPTY_STRING_CONTRACT,
}
TURN_IDENTITY_CONTRACTS = {
    "turn_id": NONEMPTY_STRING_CONTRACT,
}
TASK_COMPLETION_FIELD_CONTRACTS = {
    "completed_at": INTEGER_CONTRACT,
    "duration_ms": INTEGER_CONTRACT,
    "last_agent_message": {"types": (str,)},
    "started_at": INTEGER_CONTRACT,
    "time_to_first_token_ms": INTEGER_CONTRACT,
    "turn_id": NONEMPTY_STRING_CONTRACT,
    "type": NONEMPTY_STRING_CONTRACT,
}
WORKER_FIELD_CONTRACTS = {
    "approval_policy": NONEMPTY_STRING_CONTRACT,
    "cwd": NONEMPTY_STRING_CONTRACT,
    "effort": NONEMPTY_STRING_CONTRACT,
    "model": NONEMPTY_STRING_CONTRACT,
    "permission_profile": OBJECT_CONTRACT,
    "permission_profile_type": NONEMPTY_STRING_CONTRACT,
    "role": NONEMPTY_STRING_CONTRACT,
    "sandbox_policy": OBJECT_CONTRACT,
    "sandbox_type": NONEMPTY_STRING_CONTRACT,
}
CALL_FIELD_CONTRACTS = {
    "name": NONEMPTY_STRING_CONTRACT,
    "namespace": NONEMPTY_STRING_CONTRACT,
    "status": NONEMPTY_STRING_CONTRACT,
}
PROMOTION_WORKER_INVARIANT_FIELDS = (
    "approval_policy",
    "effort",
    "model",
    "permission_profile",
    "role",
    "sandbox_policy",
)
SCOPED_TURN_COMPLETENESS_ASSERTIONS = {
    "scope_intersecting_turns_bound_to_selected_session",
    "scope_intersecting_turn_call_output_graphs_complete",
    "scope_intersecting_turn_singleton_terminals_complete",
    "scope_intersecting_turn_final_completion_texts_match",
    "scope_intersecting_turn_completion_terminal",
}
TURN_COHERENCE_ASSERTIONS = {
    "final_answer_matches_task_completion",
    "session_meta_bound_to_selected_turn",
    "selected_evidence_within_one_logical_turn",
    "intervening_turn_records_are_exact_replays",
    *SCOPED_TURN_COMPLETENESS_ASSERTIONS,
}


class ExportError(Exception):
    def __init__(self, code: str, message: str, **details: object) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


class DuplicateObjectKeyError(ValueError):
    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


class NonFiniteJsonConstantError(ValueError):
    def __init__(self, constant: str) -> None:
        super().__init__(constant)
        self.constant = constant


class NonFiniteJsonNumberError(ValueError):
    def __init__(self, path: str, value: float) -> None:
        super().__init__(path)
        self.path = path
        self.value = value


@dataclass(frozen=True)
class SpecificationSnapshot:
    path: Path
    data: bytes
    endpoint_identity: tuple[int, int]
    sha256: str


def reject_duplicate_object_keys(pairs: list[tuple[str, object]]) -> dict:
    value = {}
    for key, item in pairs:
        if key in value:
            raise DuplicateObjectKeyError(key)
        value[key] = item
    return value


def reject_nonfinite_json_constant(constant: str) -> object:
    raise NonFiniteJsonConstantError(constant)


def validate_finite_json_numbers(value: object, *, path: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise NonFiniteJsonNumberError(path, value)
    if isinstance(value, dict):
        for key, item in value.items():
            validate_finite_json_numbers(
                item,
                path=f"{path}.{key}",
            )
    elif isinstance(value, list):
        for index, item in enumerate(value):
            validate_finite_json_numbers(
                item,
                path=f"{path}[{index}]",
            )


def strict_json_loads(value: str) -> object:
    parsed = json.loads(
        value,
        object_pairs_hook=reject_duplicate_object_keys,
        parse_constant=reject_nonfinite_json_constant,
    )
    validate_finite_json_numbers(parsed)
    return parsed


def type_names(types: tuple[type, ...]) -> list[str]:
    return [expected.__name__ for expected in types]


def validate_field_contracts(
    value: object,
    contracts: dict[str, dict],
    *,
    label: str,
    required_fields: set[str] | frozenset[str] = frozenset(),
    allow_none: bool = False,
    error_code: str = "unprojectable-record",
) -> dict:
    if not isinstance(value, dict):
        raise ExportError(
            error_code,
            "A typed source object has the wrong shape.",
            field=label,
            expected_types=["dict"],
            actual_type=type(value).__name__,
        )
    missing = sorted(required_fields.difference(value))
    if missing:
        raise ExportError(
            error_code,
            "A typed source object is missing required fields.",
            field=label,
            missing_fields=missing,
        )
    for field, contract in contracts.items():
        if field not in value:
            continue
        field_value = value[field]
        if field_value is None and allow_none:
            continue
        expected_types = contract["types"]
        if type(field_value) not in expected_types:
            raise ExportError(
                error_code,
                "A typed source field has an unsupported value type.",
                field=f"{label}.{field}",
                expected_types=type_names(expected_types),
                actual_type=type(field_value).__name__,
            )
        if contract.get("nonempty") and (
            (isinstance(field_value, str) and not field_value.strip())
            or not field_value
        ):
            raise ExportError(
                error_code,
                "A typed source field must not be empty.",
                field=f"{label}.{field}",
            )
    return value


def validate_exact_fields(
    value: object,
    allowed_fields: set[str] | frozenset[str],
    *,
    label: str,
    required_fields: set[str] | frozenset[str] = frozenset(),
    error_code: str = "unprojectable-record",
) -> dict:
    if not isinstance(value, dict):
        raise ExportError(
            error_code,
            "A governed source object has the wrong shape.",
            field=label,
            expected_types=["dict"],
            actual_type=type(value).__name__,
        )
    missing = sorted(required_fields.difference(value))
    unsupported = sorted(set(value).difference(allowed_fields))
    if missing or unsupported:
        raise ExportError(
            error_code,
            "A governed source object has missing or unsupported fields.",
            field=label,
            missing_fields=missing,
            unsupported_fields=unsupported,
        )
    return value


def validate_policy_contract(
    value: object,
    *,
    label: str,
    allow_none: bool,
    error_code: str,
) -> None:
    if value is None and allow_none:
        return
    validate_exact_fields(
        value,
        {"type"},
        label=label,
        required_fields={"type"},
        error_code=error_code,
    )
    validate_field_contracts(
        value,
        {"type": NONEMPTY_STRING_CONTRACT},
        label=label,
        required_fields={"type"},
        error_code=error_code,
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def parse_json_bytes(path: Path, data: bytes) -> dict:
    try:
        value = strict_json_loads(data.decode("utf-8"))
    except DuplicateObjectKeyError as error:
        raise ExportError(
            "invalid-json",
            "A required JSON file contains a duplicate object key.",
            path=path.as_posix(),
            duplicate_key=error.key,
        ) from error
    except NonFiniteJsonConstantError as error:
        raise ExportError(
            "invalid-json",
            "A required JSON file contains a non-finite numeric constant.",
            path=path.as_posix(),
            nonfinite_constant=error.constant,
        ) from error
    except NonFiniteJsonNumberError as error:
        raise ExportError(
            "invalid-json",
            "A required JSON file contains a non-finite numeric value.",
            path=path.as_posix(),
            json_path=error.path,
        ) from error
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ExportError("invalid-json", "A required JSON file could not be parsed.", path=path.as_posix()) from error
    if not isinstance(value, dict):
        raise ExportError("invalid-json", "The JSON root must be an object.", path=path.as_posix())
    return value


def load_json(path: Path) -> dict:
    try:
        data = path.read_bytes()
    except OSError as error:
        raise ExportError(
            "invalid-json",
            "A required JSON file could not be parsed.",
            path=path.as_posix(),
        ) from error
    return parse_json_bytes(path, data)


def validate_artifact_json_bytes(path: Path, data: bytes) -> None:
    try:
        value = strict_json_loads(data.decode("utf-8"))
    except DuplicateObjectKeyError as error:
        raise ExportError(
            "invalid-json",
            "An extract candidate contains a duplicate object key.",
            path=path.as_posix(),
            duplicate_key=error.key,
        ) from error
    except NonFiniteJsonConstantError as error:
        raise ExportError(
            "invalid-json",
            "An extract candidate contains a non-finite numeric constant.",
            path=path.as_posix(),
            nonfinite_constant=error.constant,
        ) from error
    except NonFiniteJsonNumberError as error:
        raise ExportError(
            "invalid-json",
            "An extract candidate contains a non-finite numeric value.",
            path=path.as_posix(),
            json_path=error.path,
        ) from error
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ExportError(
            "invalid-json",
            "An extract candidate is not valid UTF-8 JSON.",
            path=path.as_posix(),
        ) from error
    if not isinstance(value, dict):
        raise ExportError(
            "invalid-json",
            "The extract candidate JSON root must be an object.",
            path=path.as_posix(),
        )


def parse_rollout(path: Path) -> tuple[bytes, list[dict]]:
    try:
        data = path.read_bytes()
    except OSError as error:
        raise ExportError("rollout-read-error", "A source rollout could not be read.", path=path.as_posix()) from error
    physical_lines = data.split(b"\n")
    if physical_lines and physical_lines[-1] == b"":
        physical_lines.pop()
    records: list[dict] = []
    for line_number, raw_line in enumerate(physical_lines, 1):
        physical_record_bytes = raw_line
        if raw_line.endswith(b"\r"):
            raw_line = raw_line[:-1]
        try:
            line = raw_line.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ExportError(
                "rollout-read-error",
                "A source rollout record is not valid UTF-8.",
                path=path.as_posix(),
                line=line_number,
            ) from error
        try:
            value = strict_json_loads(line)
        except DuplicateObjectKeyError as error:
            raise ExportError(
                "rollout-parse-error",
                "A source rollout record contains a duplicate object key.",
                path=path.as_posix(),
                line=line_number,
                duplicate_key=error.key,
            ) from error
        except NonFiniteJsonConstantError as error:
            raise ExportError(
                "rollout-parse-error",
                "A source rollout record contains a non-finite numeric constant.",
                path=path.as_posix(),
                line=line_number,
                nonfinite_constant=error.constant,
            ) from error
        except NonFiniteJsonNumberError as error:
            raise ExportError(
                "rollout-parse-error",
                "A source rollout record contains a non-finite numeric value.",
                path=path.as_posix(),
                line=line_number,
                json_path=error.path,
            ) from error
        except json.JSONDecodeError as error:
            raise ExportError(
                "rollout-parse-error",
                "A source rollout record is not valid JSON.",
                path=path.as_posix(),
                line=line_number,
            ) from error
        if not isinstance(value, dict):
            raise ExportError(
                "rollout-parse-error",
                "A source rollout record is not an object.",
                path=path.as_posix(),
                line=line_number,
            )
        records.append(
            {
                "line": line_number,
                "record": value,
                "physical_record_bytes": physical_record_bytes,
            }
        )
    return data, records


def payload(row: dict) -> dict:
    value = row["record"].get("payload")
    return value if isinstance(value, dict) else {}


def locator(row: dict) -> dict:
    item = payload(row)
    return {
        "source_line": row["line"],
        "outer_record_kind": row["record"].get("type"),
        "payload_kind": item.get("type"),
        "stable_id": item.get("id"),
        "call_id": item.get("call_id"),
    }


def select_rows(
    records: list[dict],
    selector: object,
    *,
    label: str,
    predicate,
    allow_nonidentical_matches: bool = False,
) -> list[dict]:
    if not isinstance(selector, dict) or not selector:
        raise ExportError("invalid-spec", "A record selector must be a non-empty object.", field=label)
    allowed = {"call_id", "occurrence", "source_line", "stable_id", "turn_id"}
    unknown = sorted(set(selector).difference(allowed))
    if unknown:
        raise ExportError("invalid-spec", "A record selector contains unsupported fields.", field=label, fields=unknown)
    for key in ("stable_id", "call_id", "turn_id"):
        if key in selector and (not isinstance(selector[key], str) or not selector[key].strip()):
            raise ExportError("invalid-spec", f"Record selector {key} must be a non-empty string.", field=label)
    if "source_line" in selector:
        source_line = selector["source_line"]
        if not isinstance(source_line, int) or isinstance(source_line, bool) or source_line < 1:
            raise ExportError("invalid-spec", "Record selector source_line must be a positive integer.", field=label)
    if "occurrence" in selector:
        occurrence = selector["occurrence"]
        if not isinstance(occurrence, int) or isinstance(occurrence, bool) or occurrence < 1:
            raise ExportError("invalid-spec", "Record selector occurrence must be a positive integer.", field=label)

    matches = [row for row in records if predicate(row)]
    for key in ("source_line", "stable_id", "call_id", "turn_id"):
        if key not in selector:
            continue
        expected = selector[key]
        if key == "source_line":
            matches = [row for row in matches if row["line"] == expected]
        else:
            matches = [row for row in matches if payload(row).get(key if key != "stable_id" else "id") == expected]

    if "occurrence" in selector:
        occurrence = selector["occurrence"]
        matches = matches[occurrence - 1:occurrence]

    if not matches:
        raise ExportError("selected-record-missing", "A selected source record was not found.", field=label)
    if len(matches) > 1 and not allow_nonidentical_matches:
        first_payload_hash = json_value_hash(payload(matches[0]))
        if any(json_value_hash(payload(row)) != first_payload_hash for row in matches[1:]):
            raise ExportError(
                "selected-record-ambiguous",
                "A selector matched multiple non-identical source records.",
                field=label,
                count=len(matches),
            )
    return matches


def response_kind(row: dict) -> str | None:
    if row["record"].get("type") != "response_item":
        return None
    value = payload(row).get("type")
    return value if isinstance(value, str) else None


def validate_content_blocks(
    value: object,
    *,
    label: str,
) -> None:
    if not isinstance(value, list):
        raise ExportError(
            "unprojectable-record",
            "A governed response-item content field must be an array.",
            field=label,
            actual_type=type(value).__name__,
            governed_source_schema_version=GOVERNED_SOURCE_SCHEMA_VERSION,
        )
    for index, block in enumerate(value):
        block_label = f"{label}[{index}]"
        if not isinstance(block, dict):
            raise ExportError(
                "unprojectable-record",
                "A governed response-item content block must be an object.",
                field=block_label,
                actual_type=type(block).__name__,
                governed_source_schema_version=GOVERNED_SOURCE_SCHEMA_VERSION,
            )
        kind = block.get("type")
        allowed_fields = CONTENT_BLOCK_FIELDS_BY_KIND.get(kind)
        if allowed_fields is None:
            raise ExportError(
                "unprojectable-record",
                "A governed response-item content block kind is unsupported.",
                field=block_label,
                payload_kind=kind,
                governed_source_schema_version=GOVERNED_SOURCE_SCHEMA_VERSION,
            )
        value_field = (
            "encrypted_content"
            if kind == "encrypted_content"
            else "text"
        )
        validate_exact_fields(
            block,
            allowed_fields,
            label=block_label,
            required_fields={"type", value_field},
        )
        validate_field_contracts(
            block,
            {
                "type": NONEMPTY_STRING_CONTRACT,
                value_field: {"types": (str,)},
            },
            label=block_label,
            required_fields={"type", value_field},
        )


def validate_turn_metadata(
    row: dict,
    *,
    expected_turn_id: str | None,
) -> None:
    kind = response_kind(row)
    if kind not in TURN_METADATA_RESPONSE_ITEM_KINDS:
        return
    item = payload(row)
    if TURN_METADATA_FIELD not in item:
        return
    label = f"source_line[{row['line']}].payload.{TURN_METADATA_FIELD}"
    metadata = validate_exact_fields(
        item[TURN_METADATA_FIELD],
        {"turn_id"},
        label=label,
        required_fields={"turn_id"},
    )
    validate_field_contracts(
        metadata,
        TURN_IDENTITY_CONTRACTS,
        label=label,
        required_fields={"turn_id"},
    )
    metadata_turn_id = metadata["turn_id"]
    if expected_turn_id is not None and metadata_turn_id != expected_turn_id:
        raise ExportError(
            "cross-turn-selection",
            "A response item declares metadata for a different logical turn.",
            reason="response-item-turn-metadata-mismatch",
            source_line=row["line"],
            payload_kind=kind,
            expected_turn_id=expected_turn_id,
            metadata_turn_id=metadata_turn_id,
        )


def validate_response_item_turn_metadata(
    records: list[dict],
    *,
    expected_turn_id: str,
) -> None:
    for row in records:
        validate_turn_metadata(row, expected_turn_id=expected_turn_id)


def validate_session_meta_payload(item: dict, *, label: str) -> None:
    validate_exact_fields(
        item,
        SESSION_META_FIELDS_V1,
        label=label,
    )
    string_fields = SESSION_META_FIELDS_V1.difference(
        {"base_instructions", "context_window", "source"}
    )
    validate_field_contracts(
        item,
        {
            **{
                field: NONEMPTY_STRING_CONTRACT
                for field in string_fields
            },
            "base_instructions": {"types": (str, dict)},
            "context_window": {"types": (int, dict)},
            "source": {"types": (str, dict)},
        },
        label=label,
    )
    if not set(item).intersection(SESSION_IDENTITY_CONTRACTS):
        raise ExportError(
            "unprojectable-record",
            "Session metadata must contain at least one supported identity field.",
            field=label,
            required_any=sorted(SESSION_IDENTITY_CONTRACTS),
        )


def validate_turn_context_payload(item: dict, *, label: str) -> None:
    validate_exact_fields(
        item,
        TURN_CONTEXT_FIELDS_V1,
        label=label,
        required_fields={"turn_id"},
    )
    string_fields = TURN_CONTEXT_FIELDS_V1.difference(
        {
            "collaboration_mode",
            "permission_profile",
            "realtime_active",
            "sandbox_policy",
            "workspace_roots",
        }
    )
    validate_field_contracts(
        item,
        {
            **{
                field: NONEMPTY_STRING_CONTRACT
                for field in string_fields
            },
            "collaboration_mode": {"types": (dict,)},
            "permission_profile": OBJECT_CONTRACT,
            "realtime_active": {"types": (bool,)},
            "sandbox_policy": OBJECT_CONTRACT,
            "workspace_roots": {"types": (list,)},
        },
        label=label,
        required_fields={"turn_id"},
    )
    for field in ("permission_profile", "sandbox_policy"):
        if field in item:
            validate_policy_contract(
                item[field],
                label=f"{label}.{field}",
                allow_none=False,
                error_code="unprojectable-record",
            )


def validate_message_payload(item: dict, *, label: str) -> None:
    validate_exact_fields(
        item,
        MESSAGE_FIELDS_V1,
        label=label,
        required_fields={"content", "role", "type"},
    )
    validate_field_contracts(
        item,
        {
            "id": NONEMPTY_STRING_CONTRACT,
            "phase": NONEMPTY_STRING_CONTRACT,
            "role": NONEMPTY_STRING_CONTRACT,
            "status": NONEMPTY_STRING_CONTRACT,
            "type": NONEMPTY_STRING_CONTRACT,
        },
        label=label,
        required_fields={"role", "type"},
    )
    validate_content_blocks(item["content"], label=f"{label}.content")


def validate_agent_message_payload(item: dict, *, label: str) -> None:
    validate_exact_fields(
        item,
        AGENT_MESSAGE_FIELDS_V1,
        label=label,
        required_fields={"content", "type"},
    )
    validate_field_contracts(
        item,
        {
            "author": NONEMPTY_STRING_CONTRACT,
            "id": NONEMPTY_STRING_CONTRACT,
            "recipient": NONEMPTY_STRING_CONTRACT,
            "type": NONEMPTY_STRING_CONTRACT,
        },
        label=label,
        required_fields={"type"},
    )
    validate_content_blocks(item["content"], label=f"{label}.content")


def validate_reasoning_payload(item: dict, *, label: str) -> None:
    validate_exact_fields(
        item,
        REASONING_FIELDS_V1,
        label=label,
        required_fields={"type"},
    )
    validate_field_contracts(
        item,
        {
            "encrypted_content": {"types": (str,)},
            "id": NONEMPTY_STRING_CONTRACT,
            "summary": {"types": (list,)},
            "type": NONEMPTY_STRING_CONTRACT,
        },
        label=label,
        required_fields={"type"},
    )


def lifecycle_discriminator_expectation(
    item: dict,
) -> tuple[str, str | None, str] | None:
    fields = set(item)
    if (
        fields.intersection(SESSION_IDENTITY_CONTRACTS)
        and fields.issubset(SESSION_META_FIELDS_V1)
    ):
        return "session_meta", None, "session_meta"
    if TASK_COMPLETION_FIELDS_V1.difference({"type"}).issubset(fields):
        return "event_msg", "task_complete", "task_completion"
    if "turn_id" in fields and fields.issubset(TURN_CONTEXT_FIELDS_V1):
        return "turn_context", None, "turn_context"
    if (
        "content" in item
        and item.get("role") == "assistant"
        and item.get("phase") == "final_answer"
    ):
        return "response_item", "message", "final_answer"
    return None


def validate_governed_source_schema(records: list[dict]) -> None:
    for row in records:
        outer_kind = row["record"].get("type")
        outer_label = f"source_line[{row['line']}]"
        if outer_kind not in KNOWN_OUTER_RECORD_KINDS:
            raise ExportError(
                "unprojectable-record",
                "A governed source record has a missing or unknown outer discriminator.",
                reason="malformed-outer-record-discriminator",
                source_line=row["line"],
                outer_record_kind=outer_kind,
                expected_outer_record_kinds=sorted(KNOWN_OUTER_RECORD_KINDS),
            )
        validate_exact_fields(
            row["record"],
            OUTER_RECORD_FIELDS,
            label=outer_label,
            required_fields={"payload", "type"},
        )
        if not isinstance(row["record"]["payload"], dict):
            raise ExportError(
                "unprojectable-record",
                "A governed source record payload is not an object.",
                field=f"{outer_label}.payload",
                actual_type=type(
                    row["record"]["payload"]
                ).__name__,
            )
        validate_field_contracts(
            row["record"],
            {"timestamp": NONEMPTY_STRING_CONTRACT},
            label=outer_label,
        )
        item = payload(row)
        label = f"{outer_label}.payload"
        expectation = lifecycle_discriminator_expectation(item)
        if expectation is not None:
            expected_outer, expected_payload, family = expectation
            actual_payload = item.get("type")
            if (
                outer_kind != expected_outer
                or (
                    expected_payload is not None
                    and actual_payload != expected_payload
                )
            ):
                raise ExportError(
                    "unprojectable-record",
                    "A governed lifecycle record has missing or inconsistent discriminators.",
                    reason="malformed-lifecycle-record-discriminator",
                    lifecycle_family=family,
                    source_line=row["line"],
                    outer_record_kind=outer_kind,
                    payload_kind=actual_payload,
                    expected_outer_record_kind=expected_outer,
                    expected_payload_kind=expected_payload,
                )
        if outer_kind == "session_meta":
            validate_session_meta_payload(item, label=label)
            continue
        if outer_kind == "turn_context":
            validate_turn_context_payload(item, label=label)
            continue
        if outer_kind == "response_item":
            kind = response_kind(row)
            if (
                is_call_like(row)
                and kind not in CALL_KINDS
            ) or (
                is_output_like(row)
                and kind not in OUTPUT_KINDS
            ):
                raise ExportError(
                    "unsupported-call-kind",
                    "The governed source contains an unsupported call-like record.",
                    source_line=row["line"],
                    payload_kinds=[kind],
                    governed_source_schema_version=GOVERNED_SOURCE_SCHEMA_VERSION,
                )
            if kind in CALL_KINDS:
                validate_call_fields(item, label=label)
                exact_call_arguments(item, label=label)
            elif kind in OUTPUT_KINDS:
                validate_output_fields(item, label=label)
                exact_call_output(item, label=label)
            elif kind == "message":
                validate_message_payload(item, label=label)
            elif kind == "agent_message":
                validate_agent_message_payload(item, label=label)
            elif kind == "reasoning":
                validate_reasoning_payload(item, label=label)
            validate_turn_metadata(
                row,
                expected_turn_id=None,
            )
            continue
        if is_task_completion(row):
            missing = sorted(TASK_COMPLETION_FIELDS_V1.difference(item))
            unsupported = sorted(set(item).difference(TASK_COMPLETION_FIELDS_V1))
            if missing or unsupported:
                raise ExportError(
                    "unprojectable-record",
                    "A task completion does not match the governed source schema.",
                    field=label,
                    missing_fields=missing,
                    unsupported_fields=unsupported,
                    governed_source_schema_version=GOVERNED_SOURCE_SCHEMA_VERSION,
                )
            validate_field_contracts(
                item,
                TASK_COMPLETION_FIELD_CONTRACTS,
                label=label,
                required_fields=TASK_COMPLETION_FIELDS_V1,
            )


def is_call(row: dict) -> bool:
    return response_kind(row) in CALL_KINDS


def is_output(row: dict) -> bool:
    return response_kind(row) in OUTPUT_KINDS


def is_final_answer(row: dict) -> bool:
    item = payload(row)
    return (
        response_kind(row) == "message"
        and item.get("role") == "assistant"
        and item.get("phase") == "final_answer"
    )


def is_governed_response_item(row: dict) -> bool:
    return (
        row["record"].get("type") == "response_item"
        and response_kind(row) in TURN_METADATA_RESPONSE_ITEM_KINDS
    )


def is_call_like(row: dict) -> bool:
    kind = response_kind(row)
    return bool(kind and kind.endswith("_call"))


def is_output_like(row: dict) -> bool:
    kind = response_kind(row)
    return bool(kind and kind.endswith("_call_output"))


def call_record_shape(row: dict) -> str | None:
    item = payload(row)
    kind = item.get("type")
    if kind in CALL_KINDS or (
        isinstance(kind, str) and kind.endswith("_call")
    ):
        return "call"
    if kind in OUTPUT_KINDS or (
        isinstance(kind, str) and kind.endswith("_call_output")
    ):
        return "output"
    argument_fields = {
        field for field in ("arguments", "input") if field in item
    }
    if "name" in item and argument_fields:
        return "call"
    if "call_id" in item and "output" in item:
        return "output"
    return None


def validate_call_record_discriminators(rows: list[dict]) -> None:
    for row in rows:
        shape = call_record_shape(row)
        if shape is None:
            continue
        outer_kind = row["record"].get("type")
        kind = payload(row).get("type")
        supported_kinds = CALL_KINDS if shape == "call" else OUTPUT_KINDS
        if outer_kind == "response_item" and kind in supported_kinds:
            continue
        if (
            outer_kind == "response_item"
            and isinstance(kind, str)
            and (
                (shape == "call" and kind.endswith("_call"))
                or (
                    shape == "output"
                    and kind.endswith("_call_output")
                )
            )
        ):
            continue
        raise ExportError(
            "unprojectable-record",
            "A scoped call-shaped record has missing or inconsistent discriminators.",
            reason="malformed-call-record-discriminator",
            detected_shape=shape,
            source_line=row["line"],
            outer_record_kind=outer_kind,
            payload_kind=kind,
            expected_outer_record_kind="response_item",
            expected_payload_kinds=sorted(supported_kinds),
        )


def json_value_hash(value: object) -> str:
    try:
        validate_finite_json_numbers(value)
        encoded = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (NonFiniteJsonNumberError, ValueError) as error:
        raise ExportError(
            "unprojectable-record",
            "A governed JSON value contains a non-finite number.",
        ) from error
    return sha256_bytes(encoded)


def outer_record_hash(row: dict) -> str:
    return sha256_bytes(row["physical_record_bytes"])


def exact_final_answer_content(
    raw_answer: dict,
    *,
    label: str,
) -> tuple[list[dict], str]:
    validate_exact_fields(
        raw_answer,
        FINAL_ANSWER_FIELDS,
        label=label,
        required_fields={"content", "phase", "role", "type"},
    )
    raw_blocks = raw_answer.get("content")
    if not isinstance(raw_blocks, list):
        raise ExportError(
            "invalid-final-answer",
            "The final answer content is not a list.",
            field=f"{label}.content",
        )
    blocks = []
    texts = []
    for index, block in enumerate(raw_blocks):
        validate_exact_fields(
            block,
            FINAL_OUTPUT_TEXT_FIELDS,
            label=f"{label}.content[{index}]",
            required_fields={"text", "type"},
        )
        if (
            block.get("type") != "output_text"
            or not isinstance(block.get("text"), str)
        ):
            raise ExportError(
                "unsupported-final-block",
                "The final answer contains a non-text block.",
                field=f"{label}.content[{index}]",
            )
        blocks.append({"block_kind": "output_text", "text": block["text"]})
        texts.append(block["text"])
    return blocks, "".join(texts)


def final_answer(records: list[dict], selector: object) -> tuple[dict, str, list[dict]]:
    matches = select_rows(
        records,
        selector,
        label="record_selection.final_answer",
        predicate=is_final_answer,
    )
    row = matches[0]
    raw_answer = payload(row)
    blocks, exact_text = exact_final_answer_content(
        raw_answer,
        label="final_answer",
    )
    raw_blocks = raw_answer["content"]
    return {
        "record_locator": locator(row),
        "duplicate_record_locators": [locator(match) for match in matches[1:]],
        "content_blocks": blocks,
        "content_sha256": json_value_hash(raw_blocks),
        "text_sha256": sha256_bytes(exact_text.encode("utf-8")),
    }, exact_text, matches


def regex_flags(value: object, label: str) -> int:
    if value is None:
        return 0
    if not isinstance(value, str) or any(character not in "ims" for character in value):
        raise ExportError("invalid-spec", "Regex flags may contain only i, m, and s.", field=label)
    flags = 0
    for character, flag in (("i", re.IGNORECASE), ("m", re.MULTILINE), ("s", re.DOTALL)):
        if character in value:
            flags |= flag
    return flags


def classification_text(value: object) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def classification_target(classification_spec: object) -> tuple[str, str | None]:
    if not isinstance(classification_spec, dict):
        raise ExportError("invalid-spec", "study.classification must be an object.")
    source = classification_spec.get("source")
    if source not in CLASSIFICATION_SOURCES:
        raise ExportError("invalid-spec", "The classification source is unsupported.", field="study.classification.source")
    selected_source = source.startswith("selected_task_calls.")
    required = {"checks", "pass_when", "source"}
    allowed = required.union({"selected_call_id"} if selected_source else set())
    missing = sorted(required.difference(classification_spec))
    unknown = sorted(set(classification_spec).difference(allowed))
    if missing or unknown:
        raise ExportError(
            "invalid-spec",
            "study.classification has missing or unsupported fields.",
            missing_fields=missing,
            unsupported_fields=unknown,
        )
    selected_call_id = classification_spec.get("selected_call_id")
    if selected_source:
        if not isinstance(selected_call_id, str) or not selected_call_id:
            raise ExportError(
                "invalid-spec",
                "Selected-call classification sources require a non-empty classification.selected_call_id.",
                field="study.classification.selected_call_id",
            )
    return source, selected_call_id


def classify_value(value: object, classification_spec: object, rubric: str) -> dict:
    if not isinstance(classification_spec, dict):
        raise ExportError("invalid-spec", "study.classification must be an object.")
    source, selected_call_id = classification_target(classification_spec)
    mode = classification_spec["pass_when"]
    checks_spec = classification_spec["checks"]
    if mode not in {"all", "any"}:
        raise ExportError("invalid-spec", "pass_when must be all or any.", field="study.classification.pass_when")
    if not isinstance(checks_spec, list) or not checks_spec:
        raise ExportError("invalid-spec", "study.classification.checks must be a non-empty array.")

    text = classification_text(value)
    checks: dict[str, dict] = {}
    for index, check in enumerate(checks_spec):
        label = f"study.classification.checks[{index}]"
        if not isinstance(check, dict):
            raise ExportError("invalid-spec", "Each classification check must be an object.", field=label)
        required = {"id", "operator", "value"}
        missing = sorted(required.difference(check))
        if missing:
            raise ExportError(
                "invalid-spec",
                "A classification check has missing fields.",
                field=label,
                missing_fields=missing,
            )
        check_id = check.get("id")
        operator = check.get("operator")
        expected = check.get("value")
        if not isinstance(check_id, str) or not check_id or check_id in checks:
            raise ExportError("invalid-spec", "Classification check IDs must be unique non-empty strings.", field=label)
        if operator not in CLASSIFICATION_OPERATORS:
            raise ExportError("invalid-spec", "A classification operator is unsupported.", field=label)
        allowed = required.union({"flags"} if operator in {"regex", "not_regex"} else set())
        unknown = sorted(set(check).difference(allowed))
        if unknown:
            raise ExportError(
                "invalid-spec",
                "A classification check has unsupported fields.",
                field=label,
                unsupported_fields=unknown,
            )
        if not isinstance(expected, str):
            raise ExportError("invalid-spec", "Classification check values must be strings.", field=label)
        if operator in {"regex", "not_regex"}:
            try:
                matched = re.search(expected, text, regex_flags(check.get("flags"), label)) is not None
            except re.error as error:
                raise ExportError("invalid-spec", "A classification regex is invalid.", field=label) from error
            passed = matched if operator == "regex" else not matched
        elif operator == "contains":
            passed = expected in text
        elif operator == "not_contains":
            passed = expected not in text
        else:
            passed = text == expected
        checks[check_id] = {
            "operator": operator,
            "passed": passed,
            "value": expected,
            **({"flags": check.get("flags", "")} if operator in {"regex", "not_regex"} else {}),
        }

    passed_values = [check["passed"] for check in checks.values()]
    passed = all(passed_values) if mode == "all" else any(passed_values)
    return {
        "result": "pass" if passed else "fail",
        "source": source,
        **({"selected_call_id": selected_call_id} if selected_call_id is not None else {}),
        "pass_when": mode,
        "checks": checks,
        "rubric": rubric,
    }


def omission_category(row: dict) -> str:
    outer = row["record"].get("type")
    item = payload(row)
    if outer == "response_item" and item.get("type") == "message":
        return f"message:{item.get('role', 'unknown')}:{item.get('phase', 'unphased')}"
    if outer == "response_item":
        return f"response_item:{item.get('type', 'unknown')}"
    if outer == "event_msg":
        return f"event_msg:{item.get('type', 'unknown')}"
    return str(outer or "unknown")


def selected_scope(records: list[dict], selection: dict) -> tuple[list[dict], dict]:
    scope = selection.get("scope")
    if not isinstance(scope, dict) or set(scope) != {"end_line", "start_line"}:
        raise ExportError(
            "invalid-spec",
            "record_selection.scope must contain exactly start_line and end_line.",
        )
    start = scope["start_line"]
    end = scope["end_line"]
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start < 1
        or end < start
        or end > len(records)
    ):
        raise ExportError("invalid-spec", "The selected source-line scope is invalid.")
    scoped = [row for row in records if start <= row["line"] <= end]
    if not scoped:
        raise ExportError("selected-scope-empty", "The selected source-line scope contains no records.")
    return scoped, {"start_line": start, "end_line": end}


def is_turn_context(row: dict) -> bool:
    return row["record"].get("type") == "turn_context"


def is_session_meta(row: dict) -> bool:
    return row["record"].get("type") == "session_meta"


def is_task_completion(row: dict) -> bool:
    return (
        row["record"].get("type") == "event_msg"
        and payload(row).get("type") == "task_complete"
    )


def logical_turn_segments(records: list[dict]) -> tuple[list[dict], dict[int, int]]:
    segments: list[dict] = []
    line_segments: dict[int, int] = {}
    current_index: int | None = None
    current_session_row: dict | None = None
    last_completed_index: int | None = None
    duplicate_completion_open = False

    def start_segment(row: dict) -> int:
        index = len(segments)
        segments.append(
            {
                "rows": [row],
                "context_sha256": json_value_hash(payload(row)),
                "completion_sha256": None,
                "completion_outer_sha256": None,
                "bound_session_row": current_session_row,
                "session_transition_lines": [],
            }
        )
        line_segments[row["line"]] = index
        return index

    def append_row(index: int, row: dict) -> None:
        segments[index]["rows"].append(row)
        line_segments[row["line"]] = index

    for row in records:
        if is_session_meta(row):
            if current_index is not None:
                segments[current_index]["session_transition_lines"].append(row["line"])
            current_session_row = row
            last_completed_index = None
            duplicate_completion_open = False
            continue

        if is_turn_context(row):
            context_hash = json_value_hash(payload(row))
            if (
                current_index is not None
                and segments[current_index]["context_sha256"] == context_hash
            ):
                append_row(current_index, row)
            else:
                current_index = start_segment(row)
            last_completed_index = None
            duplicate_completion_open = False
            continue

        if is_task_completion(row):
            completion_hash = json_value_hash(payload(row))
            completion_outer_hash = outer_record_hash(row)
            if current_index is not None:
                append_row(current_index, row)
                segments[current_index]["completion_sha256"] = completion_hash
                segments[current_index]["completion_outer_sha256"] = (
                    completion_outer_hash
                )
                last_completed_index = current_index
                current_index = None
                duplicate_completion_open = True
            elif (
                duplicate_completion_open
                and last_completed_index is not None
                and segments[last_completed_index]["completion_outer_sha256"]
                == completion_outer_hash
            ):
                append_row(last_completed_index, row)
            else:
                last_completed_index = None
                duplicate_completion_open = False
            continue

        if current_index is not None:
            append_row(current_index, row)
        else:
            last_completed_index = None
            duplicate_completion_open = False

    return segments, line_segments


def scope_intersecting_turn_segment_indexes(
    records: list[dict],
    segments: list[dict],
    scope: dict,
) -> list[int]:
    indexes = []
    for index, segment in enumerate(segments):
        start_line = segment["rows"][0]["line"]
        next_segment_start = (
            segments[index + 1]["rows"][0]["line"]
            if index + 1 < len(segments)
            else len(records) + 1
        )
        post_segment_session_lines = [
            row["line"]
            for row in records
            if (
                segment["rows"][-1]["line"] < row["line"]
                < next_segment_start
                and is_session_meta(row)
            )
        ]
        end_line = (
            min(post_segment_session_lines)
            if post_segment_session_lines
            else next_segment_start
        ) - 1
        if (
            start_line <= scope["end_line"]
            and end_line >= scope["start_line"]
        ):
            indexes.append(index)
    return indexes


def logical_turn_segment_signature(segment: dict) -> list[str]:
    session_row = segment["bound_session_row"]
    assert session_row is not None
    return [
        outer_record_hash(session_row),
        *(outer_record_hash(row) for row in segment["rows"]),
    ]


def logical_turn_segment_locator(segment: dict) -> dict:
    rows = segment["rows"]
    session_row = segment["bound_session_row"]
    assert session_row is not None
    return {
        "start_line": rows[0]["line"],
        "end_line": rows[-1]["line"],
        "governing_session_meta": {
            "record_locator": locator(session_row),
            "outer_record_sha256": outer_record_hash(session_row),
        },
        "turn_context_source_lines": [
            row["line"]
            for row in rows
            if is_turn_context(row)
        ],
        "task_completion_source_lines": [
            row["line"]
            for row in rows
            if is_task_completion(row)
        ],
    }


def validate_logical_turn_selection(
    records: list[dict],
    *,
    session_matches: list[dict],
    turn_matches: list[dict],
    selected_call_rows: list[dict],
    selected_output_rows: list[dict],
    final_matches: list[dict],
    task_matches: list[dict],
) -> tuple[dict, list[dict], list[dict]]:
    selected_context = payload(turn_matches[0])
    selected_completion = payload(task_matches[0])
    context_turn_id = selected_context.get("turn_id")
    completion_turn_id = selected_completion.get("turn_id")
    if context_turn_id is not None and completion_turn_id != context_turn_id:
        raise ExportError(
            "cross-turn-selection",
            "Selected structural evidence does not belong to one coherent logical turn.",
            reason="turn-id-mismatch",
            turn_context_turn_id=context_turn_id,
            task_completion_turn_id=completion_turn_id,
        )

    segments, line_segments = logical_turn_segments(records)
    selected_rows = {
        "turn_context": turn_matches,
        "selected_calls": selected_call_rows,
        "selected_outputs": selected_output_rows,
        "final_answer": final_matches,
        "task_completion": task_matches,
    }
    unsegmented = {
        label: [
            row["line"]
            for row in rows
            if row["line"] not in line_segments
        ]
        for label, rows in selected_rows.items()
    }
    unsegmented = {
        label: lines
        for label, lines in unsegmented.items()
        if lines
    }
    if unsegmented:
        raise ExportError(
            "cross-turn-selection",
            "Selected structural evidence does not belong to one coherent logical turn.",
            reason="selected-record-outside-turn-segment",
            source_lines=unsegmented,
        )

    context_hash = json_value_hash(selected_context)
    completion_hash = json_value_hash(selected_completion)
    selected_lines = [
        row["line"]
        for rows in selected_rows.values()
        for row in rows
    ]
    first_selected_line = min(selected_lines)
    last_selected_line = max(selected_lines)
    different_intervening_boundaries = []
    for row in records:
        if not first_selected_line <= row["line"] <= last_selected_line:
            continue
        if is_turn_context(row) and json_value_hash(payload(row)) != context_hash:
            different_intervening_boundaries.append(
                {"source_line": row["line"], "boundary_kind": "turn_context"}
            )
        elif is_task_completion(row) and json_value_hash(payload(row)) != completion_hash:
            different_intervening_boundaries.append(
                {"source_line": row["line"], "boundary_kind": "task_completion"}
            )
    if different_intervening_boundaries:
        raise ExportError(
            "cross-turn-selection",
            "Selected structural evidence crosses a different intervening turn boundary.",
            reason="different-intervening-turn",
            intervening_boundaries=different_intervening_boundaries,
        )

    selected_segment_indexes = [
        index
        for index, segment in enumerate(segments)
        if (
            segment["rows"][0]["line"] <= last_selected_line
            and segment["rows"][-1]["line"] >= first_selected_line
        )
    ]
    incompatible_segments = [
        index
        for index in selected_segment_indexes
        if (
            segments[index]["context_sha256"] != context_hash
            or segments[index]["completion_sha256"] != completion_hash
        )
    ]
    if incompatible_segments:
        raise ExportError(
            "cross-turn-selection",
            "Selected structural evidence does not belong to one coherent logical turn.",
            reason="different-turn-boundary",
            physical_segment_indexes=incompatible_segments,
        )

    unbound_segments = [
        index
        for index in selected_segment_indexes
        if segments[index]["bound_session_row"] is None
    ]
    if unbound_segments:
        raise ExportError(
            "session-turn-binding-error",
            "Selected session metadata is not bound to every selected logical turn segment.",
            reason="selected-turn-segment-unbound",
            physical_segment_indexes=unbound_segments,
        )

    session_transition_lines = sorted(
        {
            line
            for index in selected_segment_indexes
            for line in segments[index]["session_transition_lines"]
        }
    )
    if session_transition_lines:
        raise ExportError(
            "session-turn-binding-error",
            "Selected session metadata is not bound to every selected logical turn segment.",
            reason="session-metadata-inside-turn-segment",
            source_lines=session_transition_lines,
        )

    bound_session_rows: list[dict] = []
    bound_session_lines: set[int] = set()
    for index in selected_segment_indexes:
        bound_row = segments[index]["bound_session_row"]
        if bound_row["line"] not in bound_session_lines:
            bound_session_rows.append(bound_row)
            bound_session_lines.add(bound_row["line"])

    if len({outer_record_hash(row) for row in bound_session_rows}) != 1:
        raise ExportError(
            "session-turn-binding-error",
            "Selected session metadata is not bound to every selected logical turn segment.",
            reason="mixed-governing-session-metadata",
            governing_session_source_lines=[row["line"] for row in bound_session_rows],
        )

    selected_session_lines = {row["line"] for row in session_matches}
    if selected_session_lines != bound_session_lines:
        raise ExportError(
            "session-turn-binding-error",
            "Selected session metadata is not bound to every selected logical turn segment.",
            reason="selected-session-not-exactly-governing",
            selected_only_source_lines=sorted(selected_session_lines - bound_session_lines),
            governing_only_source_lines=sorted(bound_session_lines - selected_session_lines),
        )

    signatures = [
        logical_turn_segment_signature(segments[index])
        for index in selected_segment_indexes
    ]
    if any(signature != signatures[0] for signature in signatures[1:]):
        raise ExportError(
            "cross-turn-selection",
            "Selected structural evidence spans non-identical physical turn segments.",
            reason="non-identical-turn-replay",
            physical_segment_indexes=selected_segment_indexes,
        )

    return (
        {
            "session_meta_bound_to_selected_turn": True,
            "selected_evidence_within_one_logical_turn": True,
            "intervening_turn_records_are_exact_replays": True,
        },
        bound_session_rows,
        [
            logical_turn_segment_locator(segments[index])
            for index in selected_segment_indexes
        ],
    )


def call_groups(calls: list[dict]) -> list[list[dict]]:
    groups: list[list[dict]] = []
    positions: dict[str, int] = {}
    for row in calls:
        item = payload(row)
        if isinstance(item.get("call_id"), str) and item["call_id"]:
            key = f"call_id:{item['call_id']}"
        elif isinstance(item.get("id"), str) and item["id"]:
            key = f"stable_id:{item['id']}"
        else:
            outer = row["record"]
            timestamp = outer.get("timestamp")
            if not isinstance(timestamp, str) or not timestamp:
                key = f"physical_source_line:{row['line']}"
            else:
                fallback_identity = {
                    "outer_record_kind": outer.get("type"),
                    "timestamp": timestamp,
                    "role": item.get("role"),
                    "payload_kind": item.get("type"),
                    "normalized_content": item,
                }
                key = f"fallback_sha256:{json_value_hash(fallback_identity)}"
        if key not in positions:
            positions[key] = len(groups)
            groups.append([])
        groups[positions[key]].append(row)
    return groups


def exact_call_arguments(item: dict, *, label: str) -> tuple[str, object]:
    carriers = [field for field in ("arguments", "input") if field in item]
    if len(carriers) != 1:
        raise ExportError(
            "unprojectable-record",
            "A call record must contain exactly one supported argument field.",
            field=label,
            argument_fields=carriers,
        )
    carrier = carriers[0]
    return carrier, item[carrier]


def exact_call_output(item: dict, *, label: str) -> object:
    if "output" not in item:
        raise ExportError(
            "unprojectable-record",
            "A call output record must contain an output field.",
            field=label,
        )
    return item["output"]


def validate_call_fields(item: dict, *, label: str) -> None:
    kind = item.get("type")
    allowed_fields = CALL_FIELDS_BY_KIND.get(kind)
    if allowed_fields is None:
        raise ExportError(
            "unsupported-call-kind",
            "A call record uses an unsupported payload kind.",
            payload_kinds=[kind],
        )
    validate_exact_fields(
        item,
        allowed_fields,
        label=label,
        required_fields={"name", "type"},
    )
    validate_field_contracts(
        item,
        {
            **CALL_FIELD_CONTRACTS,
            "call_id": NONEMPTY_STRING_CONTRACT,
            "id": NONEMPTY_STRING_CONTRACT,
        },
        label=label,
        required_fields={"name"},
    )


def validate_output_fields(item: dict, *, label: str) -> None:
    kind = item.get("type")
    allowed_fields = OUTPUT_FIELDS_BY_KIND.get(kind)
    if allowed_fields is None:
        raise ExportError(
            "unsupported-call-kind",
            "A call output record uses an unsupported payload kind.",
            payload_kinds=[kind],
        )
    validate_exact_fields(
        item,
        allowed_fields,
        label=label,
        required_fields={"call_id", "output", "type"},
    )
    validate_field_contracts(
        item,
        {
            "call_id": NONEMPTY_STRING_CONTRACT,
            "id": NONEMPTY_STRING_CONTRACT,
        },
        label=label,
        required_fields={"call_id"},
    )


def ensure_call_group_consistent(group: list[dict]) -> tuple[dict, str, object]:
    first = payload(group[0])
    validate_call_fields(first, label="call_group[0]")
    carrier, arguments = exact_call_arguments(first, label="call_group[0]")
    identity = (
        first.get("type"),
        first.get("id"),
        first.get("call_id"),
        first.get("name"),
        first.get("namespace"),
        carrier,
        json_value_hash(arguments),
    )
    for index, row in enumerate(group[1:], 1):
        item = payload(row)
        validate_call_fields(item, label=f"call_group[{index}]")
        other_carrier, other_arguments = exact_call_arguments(
            item,
            label=f"call_group[{index}]",
        )
        other = (
            item.get("type"),
            item.get("id"),
            item.get("call_id"),
            item.get("name"),
            item.get("namespace"),
            other_carrier,
            json_value_hash(other_arguments),
        )
        if other != identity:
            raise ExportError(
                "duplicate-call-conflict",
                "Deduplicated call records disagree on identity or arguments.",
                call_id=first.get("call_id"),
            )
    return first, carrier, arguments


def validate_stable_record_identities(rows: list[dict]) -> None:
    registry: dict[str, tuple[tuple[object, ...], dict]] = {}
    for row in rows:
        item = payload(row)
        if "id" not in item:
            continue
        stable_id = item["id"]
        if not isinstance(stable_id, str) or not stable_id:
            raise ExportError(
                "unprojectable-record",
                "A present stable record ID must be a non-empty string.",
                payload_kind=response_kind(row),
            )
        content = {
            field: value
            for field, value in item.items()
            if field not in {"id", "status"}
        }
        identity = (
            row["record"].get("type"),
            response_kind(row),
            item.get("call_id"),
            json_value_hash(content),
        )
        prior = registry.get(stable_id)
        if prior is not None and prior[0] != identity:
            raise ExportError(
                "stable-record-conflict",
                "One stable record ID resolves to conflicting scoped records.",
                stable_id=stable_id,
                first_record_locator=locator(prior[1]),
                conflicting_record_locator=locator(row),
            )
        registry.setdefault(stable_id, (identity, row))


def ensure_output_group_consistent(group: list[dict], call_id: object) -> None:
    first = payload(group[0])
    validate_output_fields(first, label="output_group[0]")
    identity = (
        response_kind(group[0]),
        first.get("id"),
        json_value_hash(exact_call_output(first, label="output_group[0]")),
    )
    for index, row in enumerate(group[1:], 1):
        item = payload(row)
        validate_output_fields(item, label=f"output_group[{index}]")
        other = (
            response_kind(row),
            item.get("id"),
            json_value_hash(
                exact_call_output(item, label=f"output_group[{index}]")
            ),
        )
        if other != identity:
            raise ExportError(
                "duplicate-output-conflict",
                "Deduplicated call outputs disagree on identity or exact value.",
                call_id=call_id,
            )


def call_output_binding_identity(item: dict) -> str:
    if "call_id" in item:
        call_id = item["call_id"]
        if not isinstance(call_id, str) or not call_id:
            raise ExportError(
                "unprojectable-record",
                "A present call_id must be a non-empty string.",
                payload_kind=item.get("type"),
            )
        return call_id
    if "id" in item:
        stable_id = item["id"]
        if not isinstance(stable_id, str) or not stable_id:
            raise ExportError(
                "unprojectable-record",
                "A present stable record ID must be a non-empty string.",
                payload_kind=item.get("type"),
            )
        return stable_id
    raise ExportError(
        "call-output-binding-error",
        "A scoped call has neither a call_id nor a pairable stable fallback identity.",
        reason="missing-call-identity",
        payload_kind=item.get("type"),
    )


def validate_call_output_bindings(calls: list[dict], outputs: list[dict]) -> None:
    calls_by_id: dict[str, list[dict]] = {}
    for row in calls:
        item = payload(row)
        call_id = call_output_binding_identity(item)
        calls_by_id.setdefault(call_id, []).append(row)
    for group in calls_by_id.values():
        ensure_call_group_consistent(group)
    outputs_by_id: dict[str, list[dict]] = {}
    for row in outputs:
        item = payload(row)
        call_id = item.get("call_id")
        matches = calls_by_id.get(call_id, []) if isinstance(call_id, str) and call_id else []
        if not matches:
            raise ExportError(
                "call-output-binding-error",
                "A scoped call output has no matching scoped call.",
                reason="orphaned-call-output",
                call_id=call_id,
                output_payload_kind=response_kind(row),
            )
        expected = sorted(
            {CALL_OUTPUT_KIND[response_kind(call)] for call in matches}
        )
        if response_kind(row) not in expected:
            raise ExportError(
                "call-output-binding-error",
                "A scoped call output kind does not match its call kind.",
                reason="cross-kind-call-output",
                call_id=call_id,
                output_payload_kind=response_kind(row),
                expected_output_payload_kinds=expected,
            )
        call_source_lines = sorted(call["line"] for call in matches)
        if not any(line < row["line"] for line in call_source_lines):
            raise ExportError(
                "turn-chronology-error",
                "A governed call output precedes its matching call.",
                reason="output-before-matching-call",
                call_id=call_id,
                call_source_lines=call_source_lines,
                output_source_line=row["line"],
            )
        outputs_by_id.setdefault(call_id, []).append(row)
    for call_id, group in outputs_by_id.items():
        ensure_output_group_consistent(group, call_id)
    for call_id, group in calls_by_id.items():
        expected_output_kinds = {
            CALL_OUTPUT_KIND[response_kind(call)]
            for call in group
        }
        actual_output_kinds = {
            response_kind(output)
            for output in outputs_by_id.get(call_id, [])
        }
        missing_output_kinds = sorted(expected_output_kinds - actual_output_kinds)
        if missing_output_kinds:
            raise ExportError(
                "call-output-binding-error",
                "A scoped call with a call_id has no matching exact-kind output.",
                reason="missing-call-output",
                call_id=call_id,
                expected_output_payload_kinds=missing_output_kinds,
            )


def physical_turn_identity(segment_index: int, segment: dict) -> dict:
    session_row = segment["bound_session_row"]
    session_item = payload(session_row) if session_row is not None else {}
    context_item = payload(segment["rows"][0])
    return {
        "physical_segment_index": segment_index,
        "session_identity": (
            session_item.get("session_id")
            or session_item.get("id")
        ),
        "turn_identity": context_item.get("turn_id"),
    }


def validate_turn_terminal_chronology(segment: dict) -> None:
    context_rows = [
        row for row in segment["rows"] if is_turn_context(row)
    ]
    distinct_context_hashes = {
        outer_record_hash(row) for row in context_rows
    }
    if len(distinct_context_hashes) != 1:
        raise ExportError(
            "turn-completeness-error",
            "A repeated turn context is not a byte-identical outer record.",
            reason="non-identical-turn-context-replay",
            turn_context_source_lines=[
                row["line"] for row in context_rows
            ],
            turn_context_outer_record_sha256s=sorted(
                distinct_context_hashes
            ),
        )
    call_output_rows = [
        row
        for row in segment["rows"]
        if is_call(row) or is_output(row)
    ]
    final_rows = [
        row for row in segment["rows"] if is_final_answer(row)
    ]
    completion_rows = [
        row for row in segment["rows"] if is_task_completion(row)
    ]
    if not final_rows:
        raise ExportError(
            "turn-completeness-error",
            "A scope-intersecting physical turn has no final answer.",
            reason="physical-turn-missing-final-answer",
        )
    distinct_final_hashes = {
        outer_record_hash(row) for row in final_rows
    }
    if len(distinct_final_hashes) != 1:
        raise ExportError(
            "turn-completeness-error",
            "A scope-intersecting physical turn has multiple non-identical final answer records.",
            reason="multiple-distinct-final-answer-records",
            final_answer_source_lines=[
                row["line"] for row in final_rows
            ],
            final_answer_outer_record_sha256s=sorted(
                distinct_final_hashes
            ),
        )
    if not completion_rows:
        raise ExportError(
            "turn-completeness-error",
            "A scope-intersecting physical turn has no bound task completion.",
            reason="physical-turn-missing-task-completion",
            final_answer_source_lines=[
                row["line"] for row in final_rows
            ],
        )
    distinct_completion_hashes = {
        outer_record_hash(row) for row in completion_rows
    }
    if len(distinct_completion_hashes) != 1:
        raise ExportError(
            "turn-completeness-error",
            "A scope-intersecting physical turn has multiple non-identical task completion records.",
            reason="multiple-distinct-task-completion-records",
            task_completion_source_lines=[
                row["line"] for row in completion_rows
            ],
            task_completion_outer_record_sha256s=sorted(
                distinct_completion_hashes
            ),
        )
    final_texts = [
        (
            row,
            exact_final_answer_content(
                payload(row),
                label=f"source_line[{row['line']}].payload",
            )[1],
        )
        for row in final_rows
    ]
    governed_call_output_lines = sorted(
        row["line"] for row in call_output_rows
    )
    for final_row in final_rows:
        offending_lines = [
            line
            for line in governed_call_output_lines
            if line >= final_row["line"]
        ]
        if offending_lines:
            raise ExportError(
                "turn-chronology-error",
                "A final answer precedes a governed call or output in its physical turn.",
                reason="final-answer-before-call-output",
                final_answer_source_line=final_row["line"],
                governed_call_output_source_lines=governed_call_output_lines,
                offending_call_output_source_lines=offending_lines,
            )
    for completion_row in completion_rows:
        required_lines = sorted(
            [
                *governed_call_output_lines,
                *(row["line"] for row in final_rows),
            ]
        )
        offending_lines = [
            line for line in required_lines if line >= completion_row["line"]
        ]
        if offending_lines:
            raise ExportError(
                "turn-chronology-error",
                "A task completion precedes governed evidence in its physical turn.",
                reason="task-completion-before-final-or-call-output",
                task_completion_source_line=completion_row["line"],
                required_preceding_source_lines=required_lines,
                offending_source_lines=offending_lines,
            )
        completion_message = payload(completion_row).get(
            "last_agent_message"
        )
        for final_row, final_text in final_texts:
            if (
                not isinstance(completion_message, str)
                or final_text != completion_message
            ):
                raise ExportError(
                    "final-completion-mismatch",
                    "A governed final answer does not exactly match its task completion.",
                    final_answer_source_line=final_row["line"],
                    task_completion_source_line=completion_row["line"],
                    final_answer_source_lines=[
                        row["line"] for row in final_rows
                    ],
                    task_completion_source_lines=[
                        row["line"] for row in completion_rows
                    ],
                    final_answer_text_sha256=sha256_bytes(
                        final_text.encode("utf-8")
                    ),
                    task_completion_message_sha256=(
                        sha256_bytes(completion_message.encode("utf-8"))
                        if isinstance(completion_message, str)
                        else None
                    ),
                )


def validate_task_completion_bindings(
    records: list[dict],
    segments: list[dict],
    line_segments: dict[int, int],
    *,
    relevant_segment_indexes: set[int],
    scope: dict,
) -> None:
    for row in records:
        if not is_task_completion(row):
            continue
        segment_index = line_segments.get(row["line"])
        if segment_index in relevant_segment_indexes:
            segment = segments[segment_index]
            active_turn_id = payload(segment["rows"][0]).get("turn_id")
            task_completion_turn_id = payload(row).get("turn_id")
            if task_completion_turn_id != active_turn_id:
                raise ExportError(
                    "session-turn-binding-error",
                    "A task completion is outside an active matching physical turn segment.",
                    reason="task-completion-outside-turn-segment",
                    source_line=row["line"],
                    active_turn_id=active_turn_id,
                    task_completion_turn_id=task_completion_turn_id,
                    physical_segment_index=segment_index,
                )
        elif (
            segment_index is None
            and scope["start_line"] <= row["line"] <= scope["end_line"]
        ):
            raise ExportError(
                "session-turn-binding-error",
                "A task completion is outside an active matching physical turn segment.",
                reason="task-completion-outside-turn-segment",
                source_line=row["line"],
                active_turn_id=None,
                task_completion_turn_id=payload(row).get("turn_id"),
            )


def validate_no_governed_records_after_completion(
    records: list[dict],
    segments: list[dict],
    line_segments: dict[int, int],
    *,
    relevant_segment_indexes: set[int],
) -> None:
    completed_segment_index: int | None = None
    completion_source_line: int | None = None
    completion_source_lines: list[int] = []
    for row in records:
        if is_session_meta(row) or is_turn_context(row):
            completed_segment_index = None
            completion_source_line = None
            completion_source_lines = []
        if is_task_completion(row):
            segment_index = line_segments.get(row["line"])
            if (
                completed_segment_index is None
                and segment_index in relevant_segment_indexes
            ):
                completed_segment_index = segment_index
                completion_source_line = row["line"]
                completion_source_lines = [row["line"]]
            elif completed_segment_index is not None:
                segment = segments[completed_segment_index]
                if (
                    segment_index != completed_segment_index
                ):
                    same_payload = (
                        json_value_hash(payload(row))
                        == segment["completion_sha256"]
                    )
                    if (
                        same_payload
                        and outer_record_hash(row)
                        != segment["completion_outer_sha256"]
                    ):
                        raise ExportError(
                            "turn-completeness-error",
                            "A task completion replay is not a byte-identical outer record.",
                            **physical_turn_identity(
                                completed_segment_index,
                                segment,
                            ),
                            reason="non-identical-task-completion-replay",
                            task_completion_source_line=completion_source_line,
                            task_completion_source_lines=completion_source_lines,
                            offending_source_line=row["line"],
                            canonical_outer_record_sha256=(
                                segment["completion_outer_sha256"]
                            ),
                            offending_outer_record_sha256=(
                                outer_record_hash(row)
                            ),
                        )
                    raise ExportError(
                        "turn-chronology-error",
                        "An unsupported task completion replay follows task completion.",
                        **physical_turn_identity(
                            completed_segment_index,
                            segment,
                        ),
                        reason="unsupported-task-completion-replay",
                        task_completion_source_line=completion_source_line,
                        task_completion_source_lines=completion_source_lines,
                        offending_source_line=row["line"],
                        offending_outer_record_kind=row["record"].get("type"),
                        offending_payload_kind=payload(row).get("type"),
                    )
                completion_source_lines.append(row["line"])
            continue
        if (
            completed_segment_index is not None
            and is_governed_response_item(row)
        ):
            raise ExportError(
                "turn-chronology-error",
                "A governed turn record appears after task completion.",
                **physical_turn_identity(
                    completed_segment_index,
                    segments[completed_segment_index],
                ),
                reason="governed-record-after-task-completion",
                task_completion_source_line=completion_source_line,
                task_completion_source_lines=completion_source_lines,
                offending_source_line=row["line"],
                offending_outer_record_kind=row["record"].get("type"),
                offending_payload_kind=payload(row).get("type"),
            )


def validate_governed_call_graph(
    records: list[dict],
    *,
    scope: dict,
    selected_session_rows: list[dict],
) -> dict:
    segments, line_segments = logical_turn_segments(records)
    relevant_segment_indexes = set(
        scope_intersecting_turn_segment_indexes(
            records,
            segments,
            scope,
        )
    )
    semantically_scoped_rows = {
        row["line"]: row
        for row in records
        if scope["start_line"] <= row["line"] <= scope["end_line"]
    }
    for segment_index in relevant_segment_indexes:
        for row in segments[segment_index]["rows"]:
            semantically_scoped_rows[row["line"]] = row
    for row in selected_session_rows:
        semantically_scoped_rows[row["line"]] = row
    governed_rows = [
        semantically_scoped_rows[line]
        for line in sorted(semantically_scoped_rows)
    ]
    validate_call_record_discriminators(
        governed_rows
    )
    validate_governed_source_schema(governed_rows)
    response_items = [
        row
        for segment_index in sorted(relevant_segment_indexes)
        for row in segments[segment_index]["rows"]
        if row["record"].get("type") == "response_item"
    ]
    validate_stable_record_identities(response_items)
    selected_session_hashes = {
        outer_record_hash(row) for row in selected_session_rows
    }
    for segment_index in sorted(relevant_segment_indexes):
        segment = segments[segment_index]
        transition_lines = segment["session_transition_lines"]
        if transition_lines:
            context_row = segment["rows"][0]
            governing_session = segment["bound_session_row"]
            raise ExportError(
                "session-turn-binding-error",
                "Session metadata changed inside an active physical turn segment.",
                reason="session-metadata-inside-turn-segment",
                physical_segment_index=segment_index,
                source_lines=transition_lines,
                turn_context_source_line=context_row["line"],
                turn_id=payload(context_row).get("turn_id"),
                governing_session_source_line=(
                    governing_session["line"]
                    if governing_session is not None
                    else None
                ),
            )
    validate_no_governed_records_after_completion(
        records,
        segments,
        line_segments,
        relevant_segment_indexes=relevant_segment_indexes,
    )
    validate_task_completion_bindings(
        records,
        segments,
        line_segments,
        relevant_segment_indexes=relevant_segment_indexes,
        scope=scope,
    )
    unbound = [
        locator(row)
        for row in records
        if (
            (is_call(row) or is_output(row))
            and row["line"] not in line_segments
            and scope["start_line"] <= row["line"] <= scope["end_line"]
        )
    ]
    if unbound:
        raise ExportError(
            "call-output-binding-error",
            "A governed call or output is outside a physical turn segment.",
            reason="call-record-outside-turn-segment",
            record_locators=unbound,
        )
    for segment_index in sorted(relevant_segment_indexes):
        segment = segments[segment_index]
        segment_calls = [
            row for row in segment["rows"] if is_call(row)
        ]
        segment_outputs = [
            row for row in segment["rows"] if is_output(row)
        ]
        session_row = segment["bound_session_row"]
        if session_row is None:
            raise ExportError(
                "session-turn-binding-error",
                "A scope-intersecting physical turn has no governing session.",
                reason="scope-intersecting-turn-unbound",
                physical_segment_index=segment_index,
            )
        if outer_record_hash(session_row) not in selected_session_hashes:
            raise ExportError(
                "session-turn-binding-error",
                "A scope-intersecting physical turn is outside the selected governing session envelope.",
                reason="scope-intersecting-turn-outside-selected-session-envelope",
                physical_segment_index=segment_index,
                governing_session_source_line=session_row["line"],
                selected_session_source_lines=[
                    row["line"] for row in selected_session_rows
                ],
            )
        turn_id = payload(segment["rows"][0]).get("turn_id")
        for row in segment["rows"]:
            validate_turn_metadata(
                row,
                expected_turn_id=turn_id,
            )
        graph_identity = physical_turn_identity(segment_index, segment)
        try:
            for group in call_groups(segment_calls):
                ensure_call_group_consistent(group)
            validate_call_output_bindings(
                segment_calls,
                segment_outputs,
            )
            validate_turn_terminal_chronology(segment)
        except ExportError as error:
            raise ExportError(
                error.code,
                error.message,
                **graph_identity,
                **error.details,
            ) from error
    return {
        "scope_intersecting_turns_bound_to_selected_session": True,
        "scope_intersecting_turn_call_output_graphs_complete": True,
        "scope_intersecting_turn_singleton_terminals_complete": True,
        "scope_intersecting_turn_final_completion_texts_match": True,
        "scope_intersecting_turn_completion_terminal": True,
    }


def emitted_status_transitions(
    call_rows: list[dict],
    output_rows: list[dict] | None = None,
) -> list[dict]:
    transitions = [
        {
            "record_locator": locator(row),
            "status": payload(row).get("status"),
        }
        for row in call_rows
    ]
    transitions.extend(
        {
            "record_locator": locator(row),
            "status": "output-recorded",
        }
        for row in output_rows or []
    )
    return sorted(
        transitions,
        key=lambda transition: transition["record_locator"]["source_line"],
    )


def selected_output_group(
    outputs: list[dict],
    call_id: object,
    expected_kind: str,
) -> list[dict]:
    matches = [row for row in outputs if payload(row).get("call_id") == call_id]
    if not matches:
        raise ExportError(
            "selected-output-cardinality",
            "The selected call output was not found in the selected record scope.",
            call_id=call_id,
            count=0,
        )
    ensure_output_group_consistent(matches, call_id)
    first_kind = response_kind(matches[0])
    if first_kind != expected_kind:
        raise ExportError(
            "call-output-binding-error",
            "The selected call output kind does not match its call kind.",
            reason="cross-kind-call-output",
            call_id=call_id,
            output_payload_kind=first_kind,
            expected_output_payload_kinds=[expected_kind],
        )
    return matches


def worker_actuals(session: dict, turn: dict) -> dict:
    validate_field_contracts(
        session,
        {"agent_role": NONEMPTY_STRING_CONTRACT},
        label="session_meta",
    )
    validate_field_contracts(
        turn,
        {
            "approval_policy": NONEMPTY_STRING_CONTRACT,
            "cwd": NONEMPTY_STRING_CONTRACT,
            "effort": NONEMPTY_STRING_CONTRACT,
            "model": NONEMPTY_STRING_CONTRACT,
            "permission_profile": OBJECT_CONTRACT,
            "sandbox_policy": OBJECT_CONTRACT,
        },
        label="turn_context",
    )
    sandbox = turn.get("sandbox_policy")
    permission = turn.get("permission_profile")
    validate_policy_contract(
        sandbox,
        label="turn_context.sandbox_policy",
        allow_none=True,
        error_code="unprojectable-record",
    )
    validate_policy_contract(
        permission,
        label="turn_context.permission_profile",
        allow_none=True,
        error_code="unprojectable-record",
    )
    return {
        "model": turn.get("model"),
        "effort": turn.get("effort"),
        "role": session.get("agent_role"),
        "sandbox_policy": sandbox,
        "sandbox_type": sandbox.get("type") if isinstance(sandbox, dict) else None,
        "approval_policy": turn.get("approval_policy"),
        "permission_profile": permission,
        "permission_profile_type": permission.get("type") if isinstance(permission, dict) else None,
        "cwd": turn.get("cwd"),
    }


def evaluate_worker_expectations(actuals: dict, expectations: object) -> dict:
    if not isinstance(expectations, dict) or not expectations:
        raise ExportError("invalid-spec", "worker_expectations must be a non-empty object.")
    unknown = sorted(set(expectations).difference(WORKER_FIELDS))
    if unknown:
        raise ExportError("invalid-spec", "worker_expectations contains unsupported fields.", fields=unknown)
    validate_field_contracts(
        expectations,
        WORKER_FIELD_CONTRACTS,
        label="worker_expectations",
        required_fields=set(expectations),
        allow_none=True,
        error_code="invalid-spec",
    )
    for field in ("sandbox_policy", "permission_profile"):
        if field in expectations:
            validate_policy_contract(
                expectations[field],
                label=f"worker_expectations.{field}",
                allow_none=True,
                error_code="invalid-spec",
            )
    checks = {
        field: {
            "actual": actuals.get(field),
            "expected": expected,
            "matches": actuals.get(field) == expected,
        }
        for field, expected in sorted(expectations.items())
    }
    return {"all_match": all(check["matches"] for check in checks.values()), "checks": checks}


def completion_record(records: list[dict], selector: object) -> tuple[dict, list[dict]]:
    matches = select_rows(
        records,
        selector,
        label="record_selection.task_completion",
        predicate=lambda row: (
            row["record"].get("type") == "event_msg"
            and payload(row).get("type") == "task_complete"
        ),
    )
    task = payload(matches[0])
    missing = sorted(TASK_COMPLETION_FIELDS_V1.difference(task))
    unsupported = sorted(set(task).difference(TASK_COMPLETION_FIELDS_V1))
    if missing or unsupported:
        raise ExportError(
            "unprojectable-record",
            "The task completion does not match the supported source-field schema.",
            source_field_schema_version=TASK_COMPLETION_SOURCE_SCHEMA_VERSION,
            missing_fields=missing,
            unsupported_fields=unsupported,
        )
    validate_field_contracts(
        task,
        TASK_COMPLETION_FIELD_CONTRACTS,
        label="task_completion",
        required_fields=TASK_COMPLETION_FIELDS_V1,
    )
    completion = {
        "source_field_schema_version": TASK_COMPLETION_SOURCE_SCHEMA_VERSION,
        "record_locator": locator(matches[0]),
        "duplicate_record_locators": [locator(match) for match in matches[1:]],
        "payload_kind": task["type"],
        "turn_id": task.get("turn_id"),
        "last_agent_message": task.get("last_agent_message"),
        "started_at": task.get("started_at"),
        "completed_at": task.get("completed_at"),
        "duration_ms": task.get("duration_ms"),
        "time_to_first_token_ms": task.get("time_to_first_token_ms"),
    }
    return completion, matches


def classification_input(
    source: str,
    *,
    answer_text: str,
    completion: dict,
    selected_calls: dict[str, dict],
    selected_call_id: str | None,
) -> object:
    if source == "complete_final_answer":
        return answer_text
    if source == "complete_task_completion.last_agent_message":
        return completion.get("last_agent_message")
    if selected_call_id is None or selected_call_id not in selected_calls:
        raise ExportError(
            "invalid-spec",
            "The classification selected_call_id must belong to every run's selected_call_ids.",
            call_id=selected_call_id,
        )
    if source == "selected_task_calls.arguments":
        return selected_calls[selected_call_id]["arguments"]
    if source == "selected_task_calls.output":
        return selected_calls[selected_call_id]["exact_output"]
    raise ExportError("invalid-spec", "The classification source is unsupported.", field="study.classification.source")


def build_run(run_spec: dict, study_spec: dict) -> dict:
    required = {
        "condition",
        "expected_source_sha256",
        "record_selection",
        "run_id",
        "selected_call_ids",
        "source",
    }
    if not isinstance(run_spec, dict):
        raise ExportError("invalid-spec", "Every run specification must be an object.")
    missing = sorted(required.difference(run_spec))
    unknown = sorted(set(run_spec).difference(required))
    if missing or unknown:
        raise ExportError(
            "invalid-spec",
            "A run specification has missing or unsupported fields.",
            missing_fields=missing,
            unsupported_fields=unknown,
        )
    for field in ("condition", "expected_source_sha256", "run_id", "source"):
        if not isinstance(run_spec[field], str) or not run_spec[field]:
            raise ExportError("invalid-spec", "Required run identity fields must be non-empty strings.", field=field)
    selected_ids = run_spec["selected_call_ids"]
    if (
        not isinstance(selected_ids, list)
        or not selected_ids
        or not all(isinstance(call_id, str) and call_id for call_id in selected_ids)
        or len(set(selected_ids)) != len(selected_ids)
    ):
        raise ExportError(
            "invalid-spec",
            "selected_call_ids must be a non-empty array of unique non-empty strings.",
            field="selected_call_ids",
        )
    if re.fullmatch(r"[0-9a-fA-F]{64}", run_spec["expected_source_sha256"]) is None:
        raise ExportError("invalid-spec", "expected_source_sha256 must contain exactly 64 hexadecimal characters.")
    selection = run_spec["record_selection"]
    if not isinstance(selection, dict):
        raise ExportError("invalid-spec", "record_selection must be an object.")
    selection_fields = {"final_answer", "scope", "session_meta", "task_completion", "turn_context"}
    missing_selection = sorted(selection_fields.difference(selection))
    unknown_selection = sorted(set(selection).difference(selection_fields))
    if missing_selection or unknown_selection:
        raise ExportError(
            "invalid-spec",
            "record_selection must name the scope and every retained singleton record.",
            missing_fields=missing_selection,
            unsupported_fields=unknown_selection,
        )

    source = Path(run_spec["source"]).resolve(strict=True)
    data, records = parse_rollout(source)
    source_hash = sha256_bytes(data)
    if source_hash.casefold() != str(run_spec["expected_source_sha256"]).casefold():
        raise ExportError("source-hash-mismatch", "A source rollout does not match its declared identity.", path=source.as_posix())

    scoped_records, scope = selected_scope(records, selection)
    session_matches = select_rows(
        records,
        selection["session_meta"],
        label="record_selection.session_meta",
        predicate=lambda row: row["record"].get("type") == "session_meta",
        allow_nonidentical_matches=True,
    )
    scoped_turn_completeness = validate_governed_call_graph(
        records,
        scope=scope,
        selected_session_rows=session_matches,
    )
    turn_matches = select_rows(
        scoped_records,
        selection["turn_context"],
        label="record_selection.turn_context",
        predicate=lambda row: row["record"].get("type") == "turn_context",
    )
    turn_row = turn_matches[0]
    turn = payload(turn_row)
    validate_field_contracts(
        turn,
        TURN_IDENTITY_CONTRACTS,
        label="turn_context",
        required_fields={"turn_id"},
    )
    unsupported_call_kinds = sorted(
        {
            response_kind(row)
            for row in scoped_records
            if (is_call_like(row) and not is_call(row))
            or (is_output_like(row) and not is_output(row))
        }
    )
    if unsupported_call_kinds:
        raise ExportError(
            "unsupported-call-kind",
            "The selected scope contains an unsupported call-like record.",
            payload_kinds=unsupported_call_kinds,
        )
    calls = [row for row in scoped_records if is_call(row)]
    outputs = [row for row in scoped_records if is_output(row)]
    for index, row in enumerate(calls):
        validate_call_fields(payload(row), label=f"scoped_calls[{index}]")
    for index, row in enumerate(outputs):
        validate_output_fields(payload(row), label=f"scoped_outputs[{index}]")
    grouped_calls = call_groups(calls)
    consistent_call_groups = [
        ensure_call_group_consistent(group)
        for group in grouped_calls
    ]
    inventory = []
    selected_groups: dict[str, list[dict]] = {}
    for group, consistent_group in zip(grouped_calls, consistent_call_groups, strict=True):
        item, carrier, arguments = consistent_group
        entry = {
            "record_locator": locator(group[0]),
            "duplicate_record_locators": [locator(row) for row in group[1:]],
            "payload_kind": item.get("type"),
            "stable_id": item.get("id"),
            "call_id": item.get("call_id"),
            "name": item.get("name"),
            "namespace": item.get("namespace"),
            "arguments_field": carrier,
            "arguments_sha256": json_value_hash(arguments),
            "status_transitions": emitted_status_transitions(group),
        }
        inventory.append(entry)
        call_id = item.get("call_id")
        if call_id in selected_ids:
            selected_groups[call_id] = group
    missing_selected_ids = [
        call_id
        for call_id in selected_ids
        if call_id not in selected_groups
    ]
    if missing_selected_ids:
        raise ExportError(
            "selected-call-missing",
            "One or more selected call IDs were not found.",
            call_ids=missing_selected_ids,
        )

    selected_calls = []
    selected_calls_by_id: dict[str, dict] = {}
    selected_call_rows: list[dict] = []
    selected_output_rows: list[dict] = []
    for selected_id in selected_ids:
        selected_group = selected_groups[selected_id]
        selected_call_rows.extend(selected_group)
        selected_item, carrier, arguments = ensure_call_group_consistent(selected_group)
        selected_outputs = selected_output_group(
            outputs,
            selected_id,
            CALL_OUTPUT_KIND[selected_item["type"]],
        )
        selected_output_rows.extend(selected_outputs)
        selected_output_item = payload(selected_outputs[0])
        exact_output = exact_call_output(
            selected_output_item,
            label=f"selected_calls[{selected_id}].output",
        )
        selected_call = {
            "call_id": selected_id,
            "payload_kind": selected_item.get("type"),
            "stable_id": selected_item.get("id"),
            "name": selected_item.get("name"),
            "namespace": selected_item.get("namespace"),
            "arguments_field": carrier,
            "arguments": arguments,
            "arguments_sha256": json_value_hash(arguments),
            "exact_output": exact_output,
            "output_sha256": json_value_hash(exact_output),
            "output_payload_kind": selected_output_item.get("type"),
            "output_stable_id": selected_output_item.get("id"),
            "status_transitions": emitted_status_transitions(
                selected_group,
                selected_outputs,
            ),
            "duplicate_call_record_locators": [locator(row) for row in selected_group[1:]],
            "duplicate_output_record_locators": [locator(row) for row in selected_outputs[1:]],
        }
        selected_calls.append(selected_call)
        selected_calls_by_id[selected_id] = selected_call

    final, answer_text, final_matches = final_answer(scoped_records, selection["final_answer"])
    completion, task_matches = completion_record(scoped_records, selection["task_completion"])
    completion_message = completion.get("last_agent_message")
    if not isinstance(completion_message, str) or answer_text != completion_message:
        raise ExportError(
            "final-completion-mismatch",
            "The concatenated final answer does not exactly match task_completion.last_agent_message.",
            final_answer_text_sha256=sha256_bytes(answer_text.encode("utf-8")),
            task_completion_message_sha256=json_value_hash(completion_message),
        )
    turn_coherence, bound_session_rows, physical_turn_segments = validate_logical_turn_selection(
        records,
        session_matches=session_matches,
        turn_matches=turn_matches,
        selected_call_rows=selected_call_rows,
        selected_output_rows=selected_output_rows,
        final_matches=final_matches,
        task_matches=task_matches,
    )
    session_row = bound_session_rows[0]
    session = payload(session_row)
    validate_field_contracts(
        session,
        SESSION_IDENTITY_CONTRACTS,
        label="session_meta",
    )
    if not any(field in session for field in SESSION_IDENTITY_CONTRACTS):
        raise ExportError(
            "unprojectable-record",
            "Session metadata must contain at least one supported identity field.",
            field="session_meta",
            required_any=sorted(SESSION_IDENTITY_CONTRACTS),
        )

    included_lines = {
        *(row["line"] for row in session_matches),
        *(row["line"] for row in turn_matches),
        *(row["line"] for row in selected_output_rows),
        *(row["line"] for row in task_matches),
        *(row["line"] for row in final_matches),
        *(row["line"] for row in calls),
    }
    omitted = Counter(
        omission_category(row)
        for row in records
        if row["line"] not in included_lines
    )
    actuals = worker_actuals(session, turn)
    expectation_evaluation = evaluate_worker_expectations(
        actuals,
        study_spec["worker_expectations"],
    )

    classification_spec = study_spec["classification"]
    classification_source, classification_call_id = classification_target(classification_spec)
    if classification_call_id is not None and classification_call_id not in selected_calls_by_id:
        raise ExportError(
            "invalid-spec",
            "The classification selected_call_id must belong to every run's selected_call_ids.",
            run_id=run_spec["run_id"],
            call_id=classification_call_id,
        )
    classification = classify_value(
        classification_input(
            classification_source,
            answer_text=answer_text,
            completion=completion,
            selected_calls=selected_calls_by_id,
            selected_call_id=classification_call_id,
        ),
        classification_spec,
        study_spec["rubric"],
    )
    logical_session_identity = session.get("session_id") or session.get("id")
    logical_turn_identity = (
        completion.get("turn_id")
        or final["record_locator"].get("stable_id")
    )
    physical_selection_material = {
        "source_path": source.as_posix(),
        "turn_segments": physical_turn_segments,
    }
    logical_replay_material = {
        "session_identity": logical_session_identity,
        "turn_identity": logical_turn_identity,
    }
    result = {
        "run_id": run_spec["run_id"],
        "condition": run_spec["condition"],
        "source_identity": {
            "path": source.as_posix(),
            "filename": source.name,
            "sha256": source_hash,
            "session_id": session.get("session_id"),
            "record_id": session.get("id"),
            "agent_path": session.get("agent_path"),
        },
        "evidence_identity": {
            "physical_selection": {
                **physical_selection_material,
                "sha256": json_value_hash(physical_selection_material),
            },
            "logical_replay": {
                **logical_replay_material,
                "sha256": (
                    json_value_hash(logical_replay_material)
                    if logical_session_identity is not None and logical_turn_identity is not None
                    else None
                ),
            },
        },
        "runtime": {
            "cli_version": session.get("cli_version"),
            "model_provider": session.get("model_provider"),
            "multi_agent_version": session.get("multi_agent_version"),
            "context_window": session.get("context_window"),
            "source_schema": {
                "format": "one-json-object-per-line",
                "declared_version": GOVERNED_SOURCE_SCHEMA_VERSION,
                "declaration_authority": "exporter-governed-source-contract",
                "normalization_schema_version": SCHEMA_VERSION,
                "task_completion_payload_schema_version": TASK_COMPLETION_SOURCE_SCHEMA_VERSION,
            },
            "observed_outer_record_kinds": sorted(
                {str(row["record"].get("type")) for row in records}
            ),
            "observed_response_item_kinds": sorted(
                {kind for row in records if (kind := response_kind(row)) is not None}
            ),
        },
        "worker_condition": {
            **actuals,
            "record_locators": {
                "session_meta": {
                    "selected": locator(session_row),
                    "duplicates": [locator(row) for row in bound_session_rows[1:]],
                },
                "turn_context": {
                    "selected": locator(turn_row),
                    "duplicates": [locator(row) for row in turn_matches[1:]],
                },
            },
        },
        "worker_expectation_evaluation": expectation_evaluation,
        "record_selection": {
            "scope": scope,
            "session_meta": selection["session_meta"],
            "turn_context": selection["turn_context"],
            "final_answer": selection["final_answer"],
            "task_completion": selection["task_completion"],
        },
        "function_call_inventory": inventory,
        "call_coverage": {
            "source_call_record_count": len(calls),
            "unique_call_count": len(grouped_calls),
            "duplicate_call_record_count": len(calls) - len(grouped_calls),
            "inventory_count": len(inventory),
            "covered_call_record_count": sum(
                1 + len(entry["duplicate_record_locators"])
                for entry in inventory
            ),
            "covers_every_call_record": (
                len(calls)
                == sum(1 + len(entry["duplicate_record_locators"]) for entry in inventory)
            ),
        },
        "selected_task_calls": selected_calls,
        "complete_final_answer": final,
        "complete_task_completion": completion,
        "derived_assertions": {
            "worker_expectations_match": expectation_evaluation["all_match"],
            "final_answer_matches_task_completion": True,
            **scoped_turn_completeness,
            **turn_coherence,
        },
        "classification": classification,
        "omissions": {
            "record_counts": dict(sorted(omitted.items())),
            "field_policy": [
                "Retain the complete final answer and task completion, every call identity, and exact selected-call arguments/output.",
                "Omit unselected messages, world state, token/rate-limit metadata, and unrelated tool output.",
            ],
            "transformations": [
                "Parse every JSONL line as one object and locate retained values by source line and stable IDs.",
                "Apply the spec-declared inclusive source-line scope before record selection and call inventory.",
                "Bind selected session metadata to the governing physical turn segments before deriving session or worker fields.",
                "Deduplicate repeated call IDs while retaining every physical call locator and status transition.",
                "Keep exporter-derived physical selection identity separate from logical session-turn replay identity.",
                "Rename raw record type fields to record_kind or payload_kind in the normalized extract.",
                "Hash exact source and physical-record bytes; use canonical JSON hashes only for normalized value identities.",
            ],
        },
    }
    try:
        fresh_data = source.read_bytes()
    except OSError as error:
        raise ExportError(
            "source-drift",
            "A source rollout became unreadable before export completed.",
            path=source.as_posix(),
        ) from error
    if fresh_data != data:
        raise ExportError(
            "source-drift",
            "A source rollout changed before export completed.",
            path=source.as_posix(),
            expected_sha256=source_hash,
            actual_sha256=sha256_bytes(fresh_data),
        )
    return result


def validate_artifact_source_freshness(runs: list[dict]) -> None:
    identities_by_path: dict[Path, list[dict[str, str]]] = {}
    for run in runs:
        identity = run["source_identity"]
        source = Path(identity["path"])
        identities_by_path.setdefault(source, []).append(
            {
                "run_id": run["run_id"],
                "sha256": identity["sha256"].casefold(),
            }
        )

    for source, identities in sorted(
        identities_by_path.items(),
        key=lambda item: item[0].as_posix(),
    ):
        try:
            fresh_data = source.read_bytes()
        except OSError as error:
            raise ExportError(
                "source-drift",
                "A source rollout became unreadable before the artifact was finalized.",
                path=source.as_posix(),
            ) from error
        actual_sha256 = sha256_bytes(fresh_data)
        expected_sha256s = sorted({identity["sha256"] for identity in identities})
        if any(expected_sha256 != actual_sha256 for expected_sha256 in expected_sha256s):
            raise ExportError(
                "source-drift",
                "A source rollout changed before the artifact was finalized.",
                path=source.as_posix(),
                run_ids=sorted(identity["run_id"] for identity in identities),
                expected_sha256s=expected_sha256s,
                actual_sha256=actual_sha256,
            )


def build_extract(spec: dict) -> dict:
    required_top = {"runs", "schema_version", "study"}
    if not isinstance(spec, dict):
        raise ExportError("invalid-spec", "The specification must be an object.")
    missing_top = sorted(required_top.difference(spec))
    unknown_top = sorted(set(spec).difference(required_top))
    if missing_top or unknown_top:
        raise ExportError(
            "invalid-spec",
            "The specification has missing or unsupported fields.",
            missing_fields=missing_top,
            unsupported_fields=unknown_top,
        )
    if spec.get("schema_version") != SCHEMA_VERSION or not isinstance(spec.get("runs"), list):
        raise ExportError(
            "invalid-spec",
            f"The specification must use schema_version {SCHEMA_VERSION} and contain a runs array.",
        )
    if not spec["runs"]:
        raise ExportError("invalid-spec", "The runs array must not be empty.")
    study = spec.get("study")
    if not isinstance(study, dict):
        raise ExportError("invalid-spec", "The study field must be an object.")
    study_fields = {"claim", "classification", "reporting", "rubric", "worker_expectations"}
    missing_study = sorted(study_fields.difference(study))
    unknown_study = sorted(set(study).difference(study_fields))
    if missing_study or unknown_study:
        raise ExportError(
            "invalid-spec",
            "The study must declare claim, rubric, classification, worker expectations, and reporting.",
            missing_fields=missing_study,
            unsupported_fields=unknown_study,
        )
    if not isinstance(study["claim"], str) or not study["claim"]:
        raise ExportError("invalid-spec", "study.claim must be a non-empty string.")
    if not isinstance(study["rubric"], str) or not study["rubric"]:
        raise ExportError("invalid-spec", "study.rubric must be a non-empty string.")
    if not isinstance(study["classification"], dict):
        raise ExportError("invalid-spec", "study.classification must be an object.")
    if not isinstance(study["worker_expectations"], dict) or not study["worker_expectations"]:
        raise ExportError("invalid-spec", "study.worker_expectations must be a non-empty object.")
    reporting = study["reporting"]
    if (
        not isinstance(reporting, dict)
        or set(reporting) != {"evidence_grade", "known_limits", "promotion_candidate"}
        or not isinstance(reporting["promotion_candidate"], bool)
        or not isinstance(reporting["evidence_grade"], str)
        or not reporting["evidence_grade"]
        or not isinstance(reporting["known_limits"], list)
        or not all(isinstance(value, str) for value in reporting["known_limits"])
    ):
        raise ExportError(
            "invalid-spec",
            "study.reporting must declare promotion_candidate, evidence_grade, and a string-array known_limits.",
        )
    classification_target(study["classification"])
    runs = [build_run(run_spec, study) for run_spec in spec["runs"]]
    run_ids = [run["run_id"] for run in runs]
    if len(set(run_ids)) != len(run_ids):
        raise ExportError("duplicate-run-id", "Run IDs must be unique.")
    selected_physical_turns: dict[str, str] = {}
    selected_logical_turns: dict[tuple[object, object], str] = {}
    for run in runs:
        physical_identity = run["evidence_identity"]["physical_selection"]["sha256"]
        if physical_identity in selected_physical_turns:
            raise ExportError(
                "duplicate-physical-run-selection",
                "Two runs select the same physical source turn evidence.",
                first_run_id=selected_physical_turns[physical_identity],
                duplicate_run_id=run["run_id"],
                physical_selection_sha256=physical_identity,
            )
        selected_physical_turns[physical_identity] = run["run_id"]

        logical_identity = run["evidence_identity"]["logical_replay"]
        session_identity = logical_identity["session_identity"]
        turn_identity = logical_identity["turn_identity"]
        if session_identity is None or turn_identity is None:
            raise ExportError(
                "logical-run-identity-missing",
                "Selected session and turn records need stable identities to prevent resumed-history double-counting.",
            )
        identity = (session_identity, turn_identity)
        if identity in selected_logical_turns:
            raise ExportError(
                "duplicate-logical-run-selection",
                "Two runs select the same logical session turn; resumed history would be double-counted.",
                first_run_id=selected_logical_turns[identity],
                duplicate_run_id=run["run_id"],
                session_id=session_identity,
                turn_id=turn_identity,
            )
        selected_logical_turns[identity] = run["run_id"]

    conditions: dict[str, dict[str, int]] = {}
    for run in runs:
        condition = run["condition"]
        counts = conditions.setdefault(condition, {"passed": 0, "total": 0})
        counts["total"] += 1
        counts["passed"] += run["classification"]["result"] == "pass"
    actual_sandboxes = {
        run["worker_condition"]["sandbox_type"]
        for run in runs
    }
    worker_expectations_match_all_runs = all(
        run["worker_expectation_evaluation"]["all_match"]
        for run in runs
    )
    first_worker = runs[0]["worker_condition"]
    worker_conditions_invariant_all_runs = all(
        first_worker.get(field) is not None
        and all(
            run["worker_condition"].get(field) == first_worker.get(field)
            for run in runs[1:]
        )
        for field in PROMOTION_WORKER_INVARIANT_FIELDS
    )
    turn_coherence_verified_all_runs = all(
        all(run["derived_assertions"].get(assertion) is True for assertion in TURN_COHERENCE_ASSERTIONS)
        for run in runs
    )
    scoped_turn_semantic_completeness_verified_all_runs = all(
        all(
            run["derived_assertions"].get(assertion) is True
            for assertion in SCOPED_TURN_COMPLETENESS_ASSERTIONS
        )
        for run in runs
    )
    promotion_machine_checks = {
        "at_least_two_conditions": len(conditions) >= 2,
        "at_least_two_runs_per_condition": bool(conditions)
        and all(counts["total"] >= 2 for counts in conditions.values()),
        "scoped_turn_semantic_completeness_verified_all_runs": (
            scoped_turn_semantic_completeness_verified_all_runs
        ),
        "turn_coherence_verified_all_runs": turn_coherence_verified_all_runs,
        "worker_expectations_match_all_runs": worker_expectations_match_all_runs,
        "worker_conditions_invariant_all_runs": worker_conditions_invariant_all_runs,
    }
    failed_promotion_checks = [
        check for check, passed in promotion_machine_checks.items() if not passed
    ]
    if reporting["promotion_candidate"] and failed_promotion_checks:
        raise ExportError(
            "promotion-evidence-insufficient",
            "The declared promotion candidate fails machine-checkable study gates.",
            failed_checks=failed_promotion_checks,
        )
    extract = {
        "schema_version": SCHEMA_VERSION,
        "study": study,
        "runs": runs,
        "summary": {
            "conditions": conditions,
            "classification_source": study["classification"]["source"],
            "declared_promotion_candidate": reporting["promotion_candidate"],
            "verified_promotion_eligible": False,
            "promotion_gate": {
                "status": (
                    "unverified-non-machine-evidence"
                    if reporting["promotion_candidate"]
                    else "not-requested"
                ),
                "machine_checks": promotion_machine_checks,
                "worker_invariant_fields": list(PROMOTION_WORKER_INVARIANT_FIELDS),
                "unverified_requirements": list(PROMOTION_UNVERIFIED_REQUIREMENTS),
            },
            "evidence_grade": reporting["evidence_grade"],
            "observed_sandbox_types": sorted(str(value) for value in actual_sandboxes),
            "worker_expectations_match_all_runs": worker_expectations_match_all_runs,
            "worker_conditions_invariant_all_runs": worker_conditions_invariant_all_runs,
            "scoped_turn_semantic_completeness_verified_all_runs": (
                scoped_turn_semantic_completeness_verified_all_runs
            ),
            "turn_coherence_verified_all_runs": turn_coherence_verified_all_runs,
            "known_limits": reporting["known_limits"],
        },
        "export_policy": {
            "complete_rollouts_included": False,
            "spec_selected_record_scope": True,
            "source_hashes_required": True,
            "session_meta_bound_to_governing_turn_segments": True,
            "all_scoped_call_records_inventoried": True,
            "replayed_call_records_deduplicated_with_provenance": True,
            "duplicate_physical_run_selection_rejected": True,
            "duplicate_logical_run_selection_rejected": True,
            "physical_and_logical_run_identities_separate": True,
            "physical_replay_identity_uses_raw_record_bytes": True,
            "final_completion_text_equality_required": True,
            "selected_evidence_turn_coherence_required": True,
            "scope_intersecting_turn_semantic_completeness_required": True,
            "non_identical_turn_replays_rejected": True,
            "selected_task_calls_exact": True,
            "complete_final_answers": True,
            "complete_task_completions": True,
            "task_completion_source_schema_version": TASK_COMPLETION_SOURCE_SCHEMA_VERSION,
        },
    }
    validate_artifact_source_freshness(runs)
    return extract


def file_identity(stat_result: os.stat_result) -> tuple[int, int]:
    return stat_result.st_dev, stat_result.st_ino


def lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def is_reparse_endpoint(stat_result: os.stat_result) -> bool:
    attributes = getattr(stat_result, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(attributes & reparse_flag)


def lexical_endpoint_identity(path: Path) -> tuple[int, int, int, bool]:
    endpoint = path.lstat()
    return (
        endpoint.st_dev,
        endpoint.st_ino,
        stat.S_IFMT(endpoint.st_mode),
        is_reparse_endpoint(endpoint),
    )


def unlink_exact_endpoint(
    path: Path,
    identity: tuple[int, int, int, bool],
) -> bool:
    try:
        if lexical_endpoint_identity(path) != identity:
            return False
        path.unlink()
        return True
    except FileNotFoundError:
        return False


def read_regular_endpoint(
    path: Path,
    *,
    writable: bool = False,
) -> tuple[bytes, tuple[int, int]]:
    try:
        before = path.lstat()
    except OSError as error:
        raise ExportError(
            "artifact-write-integrity",
            "An artifact endpoint could not be inspected.",
            path=path.as_posix(),
        ) from error
    if not stat.S_ISREG(before.st_mode) or is_reparse_endpoint(before):
        raise ExportError(
            "artifact-write-integrity",
            "An artifact endpoint is not a regular file.",
            path=path.as_posix(),
            endpoint_mode=stat.S_IFMT(before.st_mode),
        )
    flags = os.O_RDWR if writable else os.O_RDONLY
    flags |= getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
        try:
            opened = os.fstat(descriptor)
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                data = stream.read()
            if writable:
                os.fsync(descriptor)
        finally:
            os.close(descriptor)
        after = path.lstat()
    except OSError as error:
        raise ExportError(
            "artifact-write-integrity",
            "A regular artifact endpoint could not be opened safely.",
            path=path.as_posix(),
        ) from error
    identity = file_identity(opened)
    if (
        not stat.S_ISREG(opened.st_mode)
        or not stat.S_ISREG(after.st_mode)
        or is_reparse_endpoint(opened)
        or is_reparse_endpoint(after)
        or identity != file_identity(before)
        or identity != file_identity(after)
    ):
        raise ExportError(
            "artifact-write-integrity",
            "An artifact endpoint changed identity while it was inspected.",
            path=path.as_posix(),
        )
    return data, identity


def capture_specification(
    path: Path,
) -> tuple[SpecificationSnapshot, dict]:
    try:
        data, endpoint_identity = read_regular_endpoint(path)
    except ExportError as error:
        raise ExportError(
            "invalid-spec-endpoint",
            "The specification endpoint must be an existing regular non-reparse file.",
            path=path.as_posix(),
        ) from error
    snapshot = SpecificationSnapshot(
        path=path,
        data=data,
        endpoint_identity=endpoint_identity,
        sha256=sha256_bytes(data),
    )
    return snapshot, parse_json_bytes(path, data)


def validate_specification_freshness(
    snapshot: SpecificationSnapshot,
) -> None:
    try:
        data, endpoint_identity = read_regular_endpoint(snapshot.path)
    except ExportError as error:
        raise ExportError(
            "specification-changed",
            "The specification endpoint became unavailable or unsafe after it was captured.",
            path=snapshot.path.as_posix(),
            expected_sha256=snapshot.sha256,
            expected_endpoint_identity=snapshot.endpoint_identity,
        ) from error
    if (
        endpoint_identity != snapshot.endpoint_identity
        or data != snapshot.data
    ):
        raise ExportError(
            "specification-changed",
            "The specification endpoint or exact bytes changed after it was captured.",
            path=snapshot.path.as_posix(),
            expected_sha256=snapshot.sha256,
            actual_sha256=sha256_bytes(data),
            expected_endpoint_identity=snapshot.endpoint_identity,
            actual_endpoint_identity=endpoint_identity,
        )


def owned_path_matches(
    path: Path,
    identity: tuple[int, int],
    expected: bytes | None = None,
) -> bool:
    try:
        data, current_identity = read_regular_endpoint(path)
        return current_identity == identity and (
            expected is None or data == expected
        )
    except ExportError:
        return False


def unlink_owned_path(
    path: Path,
    identity: tuple[int, int],
    expected: bytes | None = None,
) -> bool:
    if owned_path_matches(path, identity, expected):
        path.unlink()
        return True
    return False


def fsync_parent_directory(path: Path) -> None:
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(path.parent, flags)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as error:
        raise ExportError(
            "artifact-write-error",
            "The artifact directory entry could not be synchronized.",
            path=path.parent.as_posix(),
        ) from error


def write_durable_temporary(
    parent: Path,
    *,
    prefix: str,
    data: bytes,
) -> tuple[Path, tuple[int, int]]:
    temporary: Path | None = None
    identity: tuple[int, int] | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=parent,
            prefix=prefix,
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            identity = file_identity(os.fstat(stream.fileno()))
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if not owned_path_matches(temporary, identity, data):
            raise ExportError(
                "artifact-write-integrity",
                "A staged artifact does not contain the intended bytes.",
                path=temporary.as_posix(),
                expected_sha256=sha256_bytes(data),
            )
        return temporary, identity
    except Exception:
        if temporary is not None and identity is not None:
            unlink_owned_path(temporary, identity)
        raise


def validate_destination_absent(path: Path) -> None:
    try:
        path.lstat()
    except FileNotFoundError:
        return
    except OSError as error:
        raise ExportError(
            "artifact-write-error",
            "The output path could not be inspected before commit.",
            path=path.as_posix(),
        ) from error
    raise ExportError(
        "artifact-write-conflict",
        "The output artifact appeared before commit.",
        path=path.as_posix(),
    )


def verify_committed_artifact(
    path: Path,
    *,
    identity: tuple[int, int],
    intended_data: bytes,
) -> None:
    try:
        committed_data, committed_identity = read_regular_endpoint(
            path,
            writable=True,
        )
    except ExportError as error:
        raise ExportError(
            "artifact-write-integrity",
            "The committed artifact could not be verified.",
            path=path.as_posix(),
            expected_sha256=sha256_bytes(intended_data),
        ) from error
    if committed_identity != identity or committed_data != intended_data:
        raise ExportError(
            "artifact-write-integrity",
            "The committed artifact does not match the owned staged bytes.",
            path=path.as_posix(),
            expected_sha256=sha256_bytes(intended_data),
            actual_sha256=sha256_bytes(committed_data),
        )


def write_atomic(
    path: Path,
    data: bytes,
    *,
    before_publish: Callable[[], None] | None = None,
    after_publish: Callable[[], None] | None = None,
    before_success: Callable[[], None] | None = None,
) -> None:
    try:
        parent_endpoint = path.parent.lstat()
    except FileNotFoundError as error:
        raise ExportError(
            "output-parent-missing",
            "The output parent directory must already exist.",
            path=path.parent.as_posix(),
        ) from error
    except OSError as error:
        raise ExportError(
            "artifact-write-error",
            "The output parent directory could not be inspected.",
            path=path.parent.as_posix(),
        ) from error
    if (
        not stat.S_ISDIR(parent_endpoint.st_mode)
        or is_reparse_endpoint(parent_endpoint)
    ):
        raise ExportError(
            "output-parent-invalid",
            "The output parent endpoint must be a real directory.",
            path=path.parent.as_posix(),
            endpoint_mode=stat.S_IFMT(parent_endpoint.st_mode),
        )
    temporary: Path | None = None
    temporary_identity: tuple[int, int] | None = None
    created_destination_identity: tuple[int, int, int, bool] | None = None
    committed = False
    try:
        try:
            path.lstat()
        except FileNotFoundError:
            pass
        except OSError as error:
            raise ExportError(
                "artifact-write-error",
                "The output path could not be inspected.",
                path=path.as_posix(),
            ) from error
        else:
            raise ExportError(
                "output-exists",
                "The output path already exists; exports publish only to a new path.",
                path=path.as_posix(),
            )
        temporary, temporary_identity = write_durable_temporary(
            path.parent,
            prefix=f".{path.name}.staged-",
            data=data,
        )
        if before_publish is not None:
            before_publish()
        validate_destination_absent(path)
        if not owned_path_matches(temporary, temporary_identity, data):
            raise ExportError(
                "artifact-write-integrity",
                "The staged artifact changed before publication.",
                path=temporary.as_posix(),
                expected_sha256=sha256_bytes(data),
            )
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise ExportError(
                "artifact-write-conflict",
                "The output artifact was concurrently created at the commit boundary.",
                path=path.as_posix(),
            ) from error
        committed = True
        try:
            created_destination_identity = lexical_endpoint_identity(path)
        except OSError as error:
            raise ExportError(
                "artifact-write-integrity",
                "The newly linked destination endpoint could not be bound.",
                path=path.as_posix(),
            ) from error
        fsync_parent_directory(path)
        verify_committed_artifact(
            path,
            identity=temporary_identity,
            intended_data=data,
        )
        if after_publish is not None:
            after_publish()
        verify_committed_artifact(
            path,
            identity=temporary_identity,
            intended_data=data,
        )
        if not unlink_owned_path(temporary, temporary_identity, data):
            raise ExportError(
                "artifact-write-integrity",
                "The owned staging endpoint could not be removed exactly.",
                path=temporary.as_posix(),
            )
        fsync_parent_directory(path)
        verify_committed_artifact(
            path,
            identity=temporary_identity,
            intended_data=data,
        )
        if before_success is not None:
            before_success()
    except Exception as original_error:
        rollback_error: Exception | None = None
        try:
            if committed:
                if created_destination_identity is None:
                    try:
                        created_destination_identity = (
                            lexical_endpoint_identity(path)
                        )
                    except OSError:
                        created_destination_identity = None
                if (
                    created_destination_identity is not None
                    and unlink_exact_endpoint(
                        path,
                        created_destination_identity,
                    )
                ):
                    fsync_parent_directory(path)
            if temporary is not None and temporary_identity is not None:
                removed_staging_endpoint = unlink_owned_path(
                    temporary,
                    temporary_identity,
                )
                if removed_staging_endpoint:
                    fsync_parent_directory(path)
        except Exception as error:
            rollback_error = error
        if rollback_error is not None:
            if isinstance(rollback_error, ExportError):
                raise rollback_error from original_error
            raise ExportError(
                "artifact-rollback-failed",
                "A failed new publication could not be removed safely.",
                path=path.as_posix(),
            ) from rollback_error
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export or verify bounded structural rollout evidence.")
    parser.add_argument("--spec", required=True, type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--out", type=Path)
    group.add_argument("--verify", type=Path)
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        spec_path = lexical_absolute(args.spec)
        specification, spec = capture_specification(spec_path)
        extract = build_extract(spec)
        data = canonical_bytes(extract)
        if args.out is not None:
            output = lexical_absolute(args.out)
            protected_inputs = {
                spec_path,
                *(Path(run["source_identity"]["path"]) for run in extract["runs"]),
            }
            if output in protected_inputs:
                raise ExportError(
                    "output-input-conflict",
                    "The output path must not replace the specification or a source rollout.",
                    path=output.as_posix(),
                )

            def export_input_freshness() -> None:
                validate_artifact_source_freshness(extract["runs"])
                validate_specification_freshness(specification)

            write_atomic(
                output,
                data,
                before_publish=export_input_freshness,
                after_publish=export_input_freshness,
                before_success=export_input_freshness,
            )
            result = {
                "status": "exported",
                "extract": output.as_posix(),
                "extract_sha256": sha256_bytes(data),
                "run_count": len(extract["runs"]),
                "summary": extract["summary"],
            }
        else:
            candidate = lexical_absolute(args.verify)
            existing, candidate_identity = read_regular_endpoint(candidate)
            validate_artifact_json_bytes(candidate, existing)
            validate_specification_freshness(specification)
            if existing != data:
                raise ExportError(
                    "extract-mismatch",
                    "The extract does not match a fresh deterministic export from its declared sources.",
                    path=candidate.as_posix(),
                )
            validate_artifact_source_freshness(extract["runs"])
            confirmed, confirmed_identity = read_regular_endpoint(candidate)
            validate_artifact_json_bytes(candidate, confirmed)
            validate_specification_freshness(specification)
            if (
                confirmed_identity != candidate_identity
                or confirmed != existing
            ):
                raise ExportError(
                    "extract-mismatch",
                    "The extract changed while it was being verified.",
                    path=candidate.as_posix(),
                )
            validate_artifact_source_freshness(extract["runs"])
            final_candidate, final_candidate_identity = read_regular_endpoint(
                candidate
            )
            validate_artifact_json_bytes(candidate, final_candidate)
            validate_specification_freshness(specification)
            if (
                final_candidate_identity != candidate_identity
                or final_candidate != existing
            ):
                raise ExportError(
                    "extract-mismatch",
                    "The extract changed at the final verification boundary.",
                    path=candidate.as_posix(),
                )
            result = {
                "status": "verified",
                "extract": candidate.as_posix(),
                "extract_sha256": sha256_bytes(existing),
                "run_count": len(extract["runs"]),
                "summary": extract["summary"],
            }
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except ExportError as error:
        result = {"status": "error", "error": error.code, "message": error.message, **error.details}
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": "internal-error",
                    "message": type(error).__name__,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

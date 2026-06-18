import json
import os

import pandas as pd
import requests
from dotenv import load_dotenv


load_dotenv()


AIRTABLE_API_URL = "https://api.airtable.com/v0"
LITERACY_SESSION_FRONT_COLUMNS = [
    "Session Record",
    "Literacy Coach Name",
    "School",
    "Site Type",
    "Children in Session",
    "Session Date",
    "Created",
    "Blending Level",
    "Sounds Covered",
    "Sounds Covered (Clean)",
    "Sounds Covered 1",
    "Sounds Covered 1 (Clean)",
    "Sounds Covered 2",
    "Sounds Covered 2 (Clean)",
]
YOUTH_FRONT_COLUMNS = [
    "Employee ID",
    "Full Name",
    "First Names",
    "Last Name",
    "Job Title",
    "Employment Status",
    "Site Placement",
    "Mentor",
    "Basic Link",
    "Office Link",
    "Start Date",
    "End Date",
    "Gender",
    "Race",
    "Email",
    "Cell Phone Number",
    "City or Town",
]


def _get_airtable_token(airtable_token: str | None = None) -> str:
    token = airtable_token or os.getenv("AIRTABLE_API_KEY")
    if not token:
        raise ValueError("AIRTABLE_API_KEY is missing. Add it to your .env file.")
    return token


def _get_required_env_var(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} is missing. Add it to your .env file.")
    return value


def _first_value(value):
    if isinstance(value, list):
        if not value:
            return None
        return value[0]
    return value


def _join_list_values(value, separator: str = ", "):
    if isinstance(value, list):
        cleaned_values = [str(item) for item in value if item not in (None, "")]
        if not cleaned_values:
            return None
        return separator.join(cleaned_values)
    return value


def _jsonify_dict(value):
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=True)
    return value


def _ensure_columns(dataframe: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        if column not in dataframe.columns:
            dataframe[column] = None
    return dataframe


def _move_existing_columns_to_front(
    dataframe: pd.DataFrame,
    front_columns: list[str],
) -> pd.DataFrame:
    existing_front_columns = [
        column for column in front_columns if column in dataframe.columns
    ]
    remaining_columns = [
        column for column in dataframe.columns if column not in existing_front_columns
    ]
    return dataframe[existing_front_columns + remaining_columns]


def _normalize_airtable_dataframe(
    dataframe: pd.DataFrame,
    first_value_columns: list[str] | None = None,
    joined_list_columns: list[str] | None = None,
    datetime_columns: list[str] | None = None,
    numeric_columns: list[str] | None = None,
    json_columns: list[str] | None = None,
    selected_columns: list[str] | None = None,
) -> pd.DataFrame:
    cleaned_dataframe = dataframe.copy()

    for column in first_value_columns or []:
        if column in cleaned_dataframe.columns:
            cleaned_dataframe[column] = cleaned_dataframe[column].apply(_first_value)

    for column in joined_list_columns or []:
        if column in cleaned_dataframe.columns:
            cleaned_dataframe[column] = cleaned_dataframe[column].apply(_join_list_values)

    for column in json_columns or []:
        if column in cleaned_dataframe.columns:
            cleaned_dataframe[column] = cleaned_dataframe[column].apply(_jsonify_dict)

    for column in datetime_columns or []:
        if column in cleaned_dataframe.columns:
            cleaned_dataframe[column] = pd.to_datetime(
                cleaned_dataframe[column],
                errors="coerce",
            )

    for column in numeric_columns or []:
        if column in cleaned_dataframe.columns:
            cleaned_dataframe[column] = pd.to_numeric(
                cleaned_dataframe[column],
                errors="coerce",
            )

    if selected_columns:
        cleaned_dataframe = _ensure_columns(cleaned_dataframe, selected_columns)
        cleaned_dataframe = cleaned_dataframe[selected_columns]

    return cleaned_dataframe


def get_raw_airtable_records(
    base_id: str,
    table_name: str,
    airtable_token: str | None = None,
    view_name: str | None = None,
    filter_formula: str | None = None,
) -> list[dict]:
    """
    Fetch all records from one Airtable table and return the raw Airtable records.
    """
    token = _get_airtable_token(airtable_token)
    url = f"{AIRTABLE_API_URL}/{base_id}/{table_name}"
    headers = {"Authorization": f"Bearer {token}"}

    all_records = []
    offset = None

    while True:
        params = {}
        if offset:
            params["offset"] = offset
        if view_name:
            params["view"] = view_name
        if filter_formula:
            params["filterByFormula"] = filter_formula

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        payload = response.json()
        all_records.extend(payload.get("records", []))

        offset = payload.get("offset")
        if not offset:
            break

    return all_records


def import_airtable_table(
    base_id: str,
    table_name: str,
    airtable_token: str | None = None,
    view_name: str | None = None,
) -> pd.DataFrame:
    """
    Import one Airtable table into a pandas DataFrame with the raw Airtable field names.
    """
    records = get_raw_airtable_records(
        base_id=base_id,
        table_name=table_name,
        airtable_token=airtable_token,
        view_name=view_name,
    )

    return pd.DataFrame([record.get("fields", {}) for record in records])


def _as_airtable_record_id_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, float) and pd.isna(value):
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    if value == "":
        return []
    return [str(value)]


def _resolve_airtable_record_ids(value, display_map: dict[str, str]) -> list[str]:
    return [display_map.get(record_id, record_id) for record_id in _as_airtable_record_id_list(value)]


def _get_children_record_ids_from_session(row) -> list[str]:
    child_ids = _as_airtable_record_id_list(row.get("Children in Session"))
    if child_ids:
        return child_ids
    return (
        _as_airtable_record_id_list(row.get("Child 1"))
        + _as_airtable_record_id_list(row.get("Child 2"))
    )


def _collect_literacy_session_linked_record_ids(dataframe: pd.DataFrame) -> dict[str, set[str]]:
    linked_record_ids = {
        "youth": set(),
        "schools": set(),
        "children": set(),
    }

    for _, row in dataframe.iterrows():
        linked_record_ids["youth"].update(
            _as_airtable_record_id_list(row.get("Literacy Coach Name"))
        )
        linked_record_ids["schools"].update(_as_airtable_record_id_list(row.get("School")))
        linked_record_ids["children"].update(_get_children_record_ids_from_session(row))

    return linked_record_ids


def _build_record_id_filter_formula(record_ids: list[str]) -> str:
    record_id_checks = [f"RECORD_ID()='{record_id}'" for record_id in record_ids]
    if len(record_id_checks) == 1:
        return record_id_checks[0]
    return f"OR({','.join(record_id_checks)})"


def _chunks(values: list[str], size: int):
    for start in range(0, len(values), size):
        yield values[start : start + size]


def _get_airtable_record_display_map(
    base_id: str,
    table_name: str,
    display_field: str,
    airtable_token: str | None = None,
    record_ids: set[str] | None = None,
) -> dict[str, str]:
    if record_ids is not None and not record_ids:
        return {}

    if record_ids is None:
        records = get_raw_airtable_records(
            base_id=base_id,
            table_name=table_name,
            airtable_token=airtable_token,
        )
    else:
        records = []
        for record_id_chunk in _chunks(sorted(record_ids), 50):
            records.extend(
                get_raw_airtable_records(
                    base_id=base_id,
                    table_name=table_name,
                    airtable_token=airtable_token,
                    filter_formula=_build_record_id_filter_formula(record_id_chunk),
                )
            )

    display_map = {}
    for record in records:
        display_value = record.get("fields", {}).get(display_field)
        if isinstance(display_value, list):
            display_value = _join_list_values(display_value)
        if display_value not in (None, ""):
            display_map[record["id"]] = str(display_value)
    return display_map


def _resolve_literacy_session_linked_names(
    dataframe: pd.DataFrame,
    youth_display_map: dict[str, str],
    school_display_map: dict[str, str],
    child_display_map: dict[str, str],
) -> pd.DataFrame:
    resolved_dataframe = dataframe.copy()

    if "Literacy Coach Name" in resolved_dataframe.columns:
        resolved_dataframe["Literacy Coach Record IDs"] = resolved_dataframe[
            "Literacy Coach Name"
        ].apply(_as_airtable_record_id_list)
        resolved_dataframe["Literacy Coach Name"] = resolved_dataframe[
            "Literacy Coach Name"
        ].apply(lambda value: _resolve_airtable_record_ids(value, youth_display_map))

    if "School" in resolved_dataframe.columns:
        resolved_dataframe["School Record IDs"] = resolved_dataframe["School"].apply(
            _as_airtable_record_id_list
        )
        resolved_dataframe["School"] = resolved_dataframe["School"].apply(
            lambda value: _resolve_airtable_record_ids(value, school_display_map)
        )

    children_record_ids = [
        _get_children_record_ids_from_session(row) for _, row in resolved_dataframe.iterrows()
    ]

    resolved_dataframe["Children in Session Record IDs"] = children_record_ids
    resolved_dataframe["Children in Session"] = [
        [child_display_map.get(record_id, record_id) for record_id in record_ids]
        for record_ids in children_record_ids
    ]

    return resolved_dataframe


def _resolve_youth_linked_names(dataframe: pd.DataFrame) -> pd.DataFrame:
    resolved_dataframe = dataframe.copy()

    if "Basic Link" in resolved_dataframe.columns:
        resolved_dataframe["Basic Link Record IDs"] = resolved_dataframe[
            "Basic Link"
        ].apply(_as_airtable_record_id_list)
        if "Full Name" in resolved_dataframe.columns:
            resolved_dataframe["Basic Link"] = resolved_dataframe["Full Name"]

    if "Office Link" in resolved_dataframe.columns:
        resolved_dataframe["Office Link Record IDs"] = resolved_dataframe[
            "Office Link"
        ].apply(_as_airtable_record_id_list)
        if "Site Placement" in resolved_dataframe.columns:
            resolved_dataframe["Office Link"] = resolved_dataframe["Site Placement"]

    return resolved_dataframe


def import_airtable_schools(
    airtable_token: str | None = None,
) -> pd.DataFrame:
    dataframe = import_airtable_table(
        base_id=_get_required_env_var("AIRTABLE_SCHOOLS_BASE_ID"),
        table_name=_get_required_env_var("AIRTABLE_SCHOOLS_TABLE_ID"),
        airtable_token=airtable_token,
    )

    return _normalize_airtable_dataframe(
        dataframe=dataframe,
        joined_list_columns=["Type"],
        numeric_columns=["Coord East", "Coord South", "School Number"],
        json_columns=["Google Maps", "School Info"],
        selected_columns=[
            "School",
            "Type",
            "Suburb",
            "School Number",
            "Coord East",
            "Coord South",
            "Google Maps Link",
            "School UID",
            "Google Maps",
            "School Info",
        ],
    )


def import_airtable_literacy_sessions(
    airtable_token: str | None = None,
    include_all_columns: bool = False,
) -> pd.DataFrame:
    base_id = _get_required_env_var("AIRTABLE_MASI_WEEKLY_SESSIONS_BASE_ID")
    dataframe = import_airtable_table(
        base_id=base_id,
        table_name=_get_required_env_var("AIRTABLE_MASI_WEEKLY_SESSIONS_TABLE_NAME"),
        airtable_token=airtable_token,
    )

    linked_record_ids = _collect_literacy_session_linked_record_ids(dataframe)

    dataframe = _resolve_literacy_session_linked_names(
        dataframe=dataframe,
        youth_display_map=_get_airtable_record_display_map(
            base_id=base_id,
            table_name="Youth DB",
            display_field="Name & Surname",
            airtable_token=airtable_token,
            record_ids=linked_record_ids["youth"],
        ),
        school_display_map=_get_airtable_record_display_map(
            base_id=base_id,
            table_name="Schools DB",
            display_field="School",
            airtable_token=airtable_token,
            record_ids=linked_record_ids["schools"],
        ),
        child_display_map=_get_airtable_record_display_map(
            base_id=base_id,
            table_name="Child DB",
            display_field="Canonical Full Name",
            airtable_token=airtable_token,
            record_ids=linked_record_ids["children"],
        ),
    )

    selected_columns = None
    if not include_all_columns:
        selected_columns = [
            "Session Record",
            "Session UID",
            "Session Date",
            "Literacy Coach Name",
            "School",
            "Children in Session",
            "Child UID",
            "Children Count",
            "Blending Level",
            "Sounds Covered",
            "Sounds Covered (Clean)",
            "Site Type",
            "Overall Session Status",
            "Capture Delay",
            "Created",
        ]

    cleaned_dataframe = _normalize_airtable_dataframe(
        dataframe=dataframe,
        joined_list_columns=[
            "Literacy Coach Name",
            "School",
            "Children in Session",
            "Literacy Coach Record IDs",
            "School Record IDs",
            "Children in Session Record IDs",
            "Child UID",
            "Sounds Covered",
            "Sounds Covered (Clean)",
            "Site Type",
        ],
        datetime_columns=["Session Date", "Created"],
        numeric_columns=["Children Count", "Capture Delay", "Sounds Token Count"],
        selected_columns=selected_columns,
    )
    if include_all_columns:
        cleaned_dataframe = _move_existing_columns_to_front(
            cleaned_dataframe,
            LITERACY_SESSION_FRONT_COLUMNS,
        )
    return cleaned_dataframe


def import_airtable_2025_assessments(
    airtable_token: str | None = None,
) -> pd.DataFrame:
    dataframe = import_airtable_table(
        base_id=_get_required_env_var("AIRTABLE_2025_ASSESSMENTS_BASE_ID"),
        table_name=_get_required_env_var("AIRTABLE_2025_ASSESSMENTS_TABLE_ID"),
        airtable_token=airtable_token,
    )

    return _normalize_airtable_dataframe(
        dataframe=dataframe,
        joined_list_columns=[
            "School Name",
            "Support Needed",
            "Graduate",
            "Midline Graduates",
            "Endline Graduates",
            "Total Sessions - Tracker",
            "Endline Points Improvement",
            "Endline Overall Points Improvement",
            "Latest Reading Level",
            "Reading Band",
            "Assessment Grade",
        ],
        datetime_columns=["Created"],
        numeric_columns=[
            "Jan - Total",
            "June - Total",
            "Nov - Total",
            "Points Gained/Reduced",
            "Total Sessions - Tracker",
            "Endline Points Improvement",
            "Endline Overall Points Improvement",
        ],
        selected_columns=[
            "Mcode",
            "Full Name",
            "School",
            "School Name",
            "Grade",
            "Class",
            "Teacher",
            "Language",
            "Mentor",
            "Gender",
            "On the Programme",
            "Baseline Status",
            "Midline Status",
            "Endline Status",
            "Jan - Total",
            "June - Total",
            "Nov - Total",
            "Points Gained/Reduced",
            "Total Sessions - Tracker",
            "Latest Reading Level",
            "Reading Band",
            "LC Status",
            "Created",
        ],
    )


def import_airtable_children(
    airtable_token: str | None = None,
) -> pd.DataFrame:
    dataframe = import_airtable_table(
        base_id=_get_required_env_var("AIRTABLE_CHILDREN_2026_BASE_ID"),
        table_name=_get_required_env_var("AIRTABLE_CHILDREN_2026_TABLE_ID"),
        airtable_token=airtable_token,
    )

    return _normalize_airtable_dataframe(
        dataframe=dataframe,
        joined_list_columns=[
            "Years",
            "Programme Belonging",
            "Programme Link",
            "Mcode (from Seeded Link)",
            "2025 Language",
            "2026 Language",
            "2025 Baseline Totals",
            "2026 Baseline Totals",
        ],
        datetime_columns=["Created"],
        numeric_columns=["Child Number", "Unique First Names Count", "Unique Surnames Count"],
        json_columns=["Remove List Only"],
        selected_columns=[
            "Child Number",
            "Canonical Full Name",
            "Canonical First Name",
            "Canonical Surname",
            "Gender",
            "Years",
            "Mcode",
            "Mcode (from Seeded Link)",
            "Child UID",
            "Identity Confidence",
            "Seed Source",
            "Programme Belonging",
            "2025 School",
            "2025 Grade",
            "2025 Language",
            "2026 School",
            "2026 Grade",
            "2026 Language",
            "2025 Baseline Totals",
            "2026 Baseline Totals",
            "Created",
        ],
    )


def import_airtable_staff(
    airtable_token: str | None = None,
) -> pd.DataFrame:
    dataframe = import_airtable_table(
        base_id=_get_required_env_var("AIRTABLE_STAFF_2026_BASE_ID"),
        table_name=_get_required_env_var("AIRTABLE_STAFF_2026_TABLE_ID"),
        airtable_token=airtable_token,
    )

    return _normalize_airtable_dataframe(
        dataframe=dataframe,
        joined_list_columns=[
            "Combined Staff Data",
            "Staff Office Data",
            "Attachment: Drivers License",
            "Attachment: ID Document",
        ],
        datetime_columns=["Date of Birth"],
        selected_columns=[
            "Employee Number",
            "Full Name",
            "First Names",
            "Last Name",
            "Gender",
            "Race",
            "Email",
            "Cell Number",
            "Date of Birth",
            "City or town",
            "Suburb or district",
            "Street",
            "Street number",
            "Postal Code",
        ],
    )


def import_airtable_youth(
    airtable_token: str | None = None,
    include_all_columns: bool = False,
) -> pd.DataFrame:
    dataframe = import_airtable_table(
        base_id=_get_required_env_var("AIRTABLE_YOUTH_DB_BASE"),
        table_name=_get_required_env_var("AIRTABLE_COMBINED_YOUTH_DB_TABLE"),
        airtable_token=airtable_token,
    )

    dataframe = _resolve_youth_linked_names(dataframe)

    selected_columns = None
    if not include_all_columns:
        selected_columns = [
            "Employee ID",
            "Full Name",
            "First Names",
            "Last Name",
            "Job Title",
            "Employment Status",
            "Site Placement",
            "Mentor",
            "Start Date",
            "End Date",
            "Gender",
            "Race",
            "Email",
            "Cell Phone Number",
            "City or Town",
        ]

    cleaned_dataframe = _normalize_airtable_dataframe(
        dataframe=dataframe,
        joined_list_columns=[
            "Full Name",
            "First Names",
            "Last Name",
            "Site Placement",
            "Job Title",
            "Employment Status",
            "Mentor",
            "Basic Link",
            "Basic Link Record IDs",
            "Office Link",
            "Office Link Record IDs",
            "Email",
            "Cell Phone Number",
            "Gender",
            "Race",
            "Start Date",
            "End Date",
        ],
        datetime_columns=["DOB", "Start Date", "End Date"],
        selected_columns=selected_columns,
    )
    if include_all_columns:
        cleaned_dataframe = _move_existing_columns_to_front(
            cleaned_dataframe,
            YOUTH_FRONT_COLUMNS,
        )
    return cleaned_dataframe


def import_airtable_numeracy_2026_sessions(
    airtable_token: str | None = None,
) -> pd.DataFrame:
    """
    Import the configured numeracy 2026 Airtable table.

    Based on the current Airtable response shape, this table looks like a
    session-style dataset.
    """
    dataframe = import_airtable_table(
        base_id=_get_required_env_var("AIRTABLE_NUMERACY_2026_BASE_ID"),
        table_name=_get_required_env_var("AIRTABLE_NUMERACY_2026_TABLE_ID"),
        airtable_token=airtable_token,
    )

    return _normalize_airtable_dataframe(
        dataframe=dataframe,
        joined_list_columns=[
            "Numeracy Coach Name",
            "School",
            "Children in Session",
            "Child UID",
            "Mentor",
        ],
        datetime_columns=["Session Date", "Created"],
        numeric_columns=["Children Count", "Capture Delay"],
        selected_columns=[
            "Session Record",
            "Session UID",
            "Session Date",
            "Numeracy Coach Name",
            "School",
            "Children in Session",
            "Child UID",
            "Children Count",
            "Group Current Count Level",
            "Group Current Number Recognition",
            "Mentor",
            "Overall Session Status",
            "Capture Delay",
            "Created",
        ],
    )


def import_airtable_numeracy_2026_assessments(
    airtable_token: str | None = None,
) -> pd.DataFrame:
    """
    Backwards-compatible alias for the numeracy 2026 sessions import helper.
    """
    return import_airtable_numeracy_2026_sessions(airtable_token=airtable_token)


def import_masi_literacy_sessions_from_airtable(
    airtable_token: str | None = None,
) -> pd.DataFrame:
    """
    Backwards-compatible alias for the literacy sessions import helper.
    """
    return import_airtable_literacy_sessions(airtable_token=airtable_token)

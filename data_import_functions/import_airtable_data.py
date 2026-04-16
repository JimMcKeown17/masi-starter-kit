import json
import os

import pandas as pd
import requests
from dotenv import load_dotenv


load_dotenv()


AIRTABLE_API_URL = "https://api.airtable.com/v0"


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
) -> pd.DataFrame:
    dataframe = import_airtable_table(
        base_id=_get_required_env_var("AIRTABLE_MASI_WEEKLY_SESSIONS_BASE_ID"),
        table_name=_get_required_env_var("AIRTABLE_MASI_WEEKLY_SESSIONS_TABLE_NAME"),
        airtable_token=airtable_token,
    )

    return _normalize_airtable_dataframe(
        dataframe=dataframe,
        joined_list_columns=[
            "Literacy Coach Name",
            "School",
            "Children in Session",
            "Child UID",
            "Sounds Covered",
            "Sounds Covered (Clean)",
            "Site Type",
        ],
        datetime_columns=["Session Date", "Created"],
        numeric_columns=["Children Count", "Capture Delay", "Sounds Token Count"],
        selected_columns=[
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
        ],
    )


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
) -> pd.DataFrame:
    dataframe = import_airtable_table(
        base_id=_get_required_env_var("AIRTABLE_YOUTH_DB_BASE"),
        table_name=_get_required_env_var("AIRTABLE_COMBINED_YOUTH_DB_TABLE"),
        airtable_token=airtable_token,
    )

    return _normalize_airtable_dataframe(
        dataframe=dataframe,
        joined_list_columns=[
            "Site Placement",
            "Job Title",
            "Employment Status",
            "Mentor",
            "Email",
            "Cell Phone Number",
            "Gender",
            "Race",
            "Start Date",
            "End Date",
        ],
        datetime_columns=["DOB", "Start Date", "End Date"],
        selected_columns=[
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
        ],
    )


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

import json
import os
import time

import pandas as pd
import requests
from dotenv import load_dotenv


load_dotenv()


TEAMPACT_BASE_URL = os.getenv("TEAMPACT_BASE_URL", "https://teampact.co/api/analytics/v1")
TEAMPACT_SESSIONS_URL = os.getenv(
    "TEAMPACT_SESSIONS_URL",
    "https://teampact.co/api/analytics/v1/sessions/attendance",
)

AVAILABLE_TEAMPACT_ASSESSMENT_SURVEYS = {
    815: "Baseline Full Assessment - isiXhosa",
    816: "Baseline Full Assessment - Afrikaans",
    817: "Baseline Full Assessment - English",
    805: "ZZ ECD Baseline 2026",
}

SURVEY_LANGUAGE = {
    815: "isiXhosa",
    816: "Afrikaans",
    817: "English",
    805: "ECD",
}

ECD_QUESTION_IDS = {
    "grade": 28181,
    "first_name": 28183,
    "last_name": 28184,
    "gender": 28185,
}


def _get_api_token(api_token: str | None = None) -> str:
    token = api_token or os.getenv("TEAMPACT_API_TOKEN")
    if not token:
        raise ValueError("TEAMPACT_API_TOKEN is missing. Add it to your .env file.")
    return token


def _get_headers(api_token: str | None = None) -> dict:
    token = _get_api_token(api_token)
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _request_json(url: str, headers: dict, params: dict | None = None) -> dict:
    response = requests.get(url, headers=headers, params=params, timeout=30)

    if response.status_code == 429:
        time.sleep(5)
        response = requests.get(url, headers=headers, params=params, timeout=30)

    response.raise_for_status()
    return response.json()


def _parse_datetime(value):
    return pd.to_datetime(value, errors="coerce", utc=True)


def _clean_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _clean_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _split_name(full_name: str | None) -> tuple[str, str]:
    if not full_name:
        return "", ""
    parts = str(full_name).strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def _parse_group_ids(raw_group_id) -> list[int]:
    if raw_group_id in (None, ""):
        return []

    try:
        if isinstance(raw_group_id, list):
            return [int(group_id) for group_id in raw_group_id]
        if isinstance(raw_group_id, str):
            parsed = json.loads(raw_group_id)
            if isinstance(parsed, list):
                return [int(group_id) for group_id in parsed]
            return [int(parsed)]
        return [int(raw_group_id)]
    except (json.JSONDecodeError, TypeError, ValueError):
        return []


def _extract_grade_from_class_name(class_name: str | None) -> str:
    if not class_name:
        return ""

    class_name = str(class_name)
    if "Grade R" in class_name:
        return "Grade R"
    if "Grade 1" in class_name:
        return "Grade 1"
    if "Grade 2" in class_name:
        return "Grade 2"

    first_character = class_name.strip()[:1].upper()
    return {"R": "Grade R", "1": "Grade 1", "2": "Grade 2"}.get(first_character, "")


def _extract_ecd_learner_info(answers: list[dict]) -> dict:
    learner_info = {
        "first_name": "",
        "last_name": "",
        "grade": "",
        "gender": "",
    }

    for answer in answers:
        question_id = answer.get("question_id")
        value = answer.get("answer")
        if isinstance(value, dict):
            value = value.get("value", "")
        value = str(value or "").strip()

        if question_id == ECD_QUESTION_IDS["first_name"]:
            learner_info["first_name"] = value
        elif question_id == ECD_QUESTION_IDS["last_name"]:
            learner_info["last_name"] = value
        elif question_id == ECD_QUESTION_IDS["grade"]:
            learner_info["grade"] = value
        elif question_id == ECD_QUESTION_IDS["gender"]:
            learner_info["gender"] = value

    return learner_info


def _infer_subtest_name(question: dict, answer_value: dict, seen_subtests: set[str]) -> str:
    content = str(question.get("content") or "").lower()
    question_type = str(question.get("type") or "").lower()
    search_text = f"{content} {question_type}"

    if "nonword" in search_text or "nonsense" in search_text:
        return "nonwords"
    if "letter" in search_text:
        return "letters"
    if "word" in search_text:
        return "words"

    cell_count = len(answer_value.get("cells", []))
    if cell_count >= 50 and "letters" not in seen_subtests:
        return "letters"

    for subtest_name in ("letters", "nonwords", "words"):
        if subtest_name not in seen_subtests:
            return subtest_name

    question_id = question.get("question_id", "unknown")
    return f"question_{question_id}"


def _fetch_group_details(group_id: int, api_token: str | None = None) -> dict:
    url = f"{TEAMPACT_BASE_URL.rstrip('/')}/groups/{group_id}"
    payload = _request_json(url, headers=_get_headers(api_token))
    group_data = payload.get("data", {})
    program_data = group_data.get("program") or {}

    return {
        "class_id": group_data.get("id"),
        "class_name": group_data.get("name", ""),
        "program_id": group_data.get("program_id"),
        "program_name": program_data.get("name", ""),
    }


def _build_group_lookup(survey_responses: list[dict], api_token: str | None = None) -> dict[int, dict]:
    unique_group_ids = set()
    for response in survey_responses:
        unique_group_ids.update(_parse_group_ids(response.get("group_id")))

    group_lookup = {}
    for group_id in sorted(unique_group_ids):
        try:
            group_lookup[group_id] = _fetch_group_details(group_id, api_token=api_token)
            time.sleep(0.2)
        except requests.RequestException:
            group_lookup[group_id] = {
                "class_id": group_id,
                "class_name": "",
                "program_id": None,
                "program_name": "",
            }

    return group_lookup


def get_raw_teampact_assessment_data(
    survey_id: int,
    api_token: str | None = None,
    per_page: int = 100,
) -> dict:
    survey_name = AVAILABLE_TEAMPACT_ASSESSMENT_SURVEYS.get(survey_id, f"Survey {survey_id}")
    url = f"{TEAMPACT_BASE_URL.rstrip('/')}/surveys/{survey_id}/responses"
    headers = _get_headers(api_token)

    all_responses = []
    survey_questions = []
    page = 1
    last_page = 1

    while True:
        payload = _request_json(
            url,
            headers=headers,
            params={"page": page, "per_page": per_page},
        )

        data = payload.get("data", {})
        if page == 1:
            survey_questions = data.get("survey_questions", [])

        page_responses = data.get("survey_responses", [])
        if not page_responses:
            break

        all_responses.extend(page_responses)
        meta = payload.get("meta", {})
        last_page = meta.get("last_page", page)

        if page >= last_page:
            break

        page += 1
        time.sleep(0.2)

    return {
        "survey_id": survey_id,
        "survey_name": survey_name,
        "language": SURVEY_LANGUAGE.get(survey_id, ""),
        "survey_questions": survey_questions,
        "survey_responses": all_responses,
        "meta": {
            "pages_fetched": page,
            "last_page": last_page,
            "total_responses": len(all_responses),
        },
    }


def turn_teampact_assessment_data_into_dataframe(
    raw_data: dict,
    api_token: str | None = None,
) -> pd.DataFrame:
    survey_id = raw_data["survey_id"]
    survey_responses = raw_data.get("survey_responses", [])
    survey_questions = raw_data.get("survey_questions", [])

    question_lookup = {
        question.get("question_id"): question
        for question in survey_questions
    }
    group_lookup = _build_group_lookup(survey_responses, api_token=api_token)

    rows = []

    for response in survey_responses:
        answers = response.get("answers") or []
        learner_info = _extract_ecd_learner_info(answers)

        group_ids = _parse_group_ids(response.get("group_id"))
        group_info = group_lookup.get(group_ids[0], {}) if group_ids else {}

        first_name, last_name = _split_name(response.get("participant_name"))
        if learner_info["first_name"] or learner_info["last_name"]:
            first_name = learner_info["first_name"] or first_name
            last_name = learner_info["last_name"] or last_name

        class_name = response.get("class_name") or group_info.get("class_name", "")
        program_name = response.get("program_name") or group_info.get("program_name", "")

        row = {
            "response_id": response.get("response_id"),
            "response_uuid": response.get("response_uuid"),
            "survey_id": survey_id,
            "survey_name": raw_data.get("survey_name"),
            "language": raw_data.get("language"),
            "participant_id": response.get("participant_id"),
            "first_name": first_name,
            "last_name": last_name,
            "gender": learner_info["gender"],
            "grade": learner_info["grade"] or _extract_grade_from_class_name(class_name),
            "class_id": group_info.get("class_id") or (group_ids[0] if group_ids else None),
            "class_name": class_name,
            "program_id": group_info.get("program_id"),
            "program_name": program_name,
            "collected_by": response.get("user_name"),
            "user_id": response.get("user_id"),
            "response_date": _parse_datetime(response.get("response_start_at")),
            "response_end_at": _parse_datetime(response.get("response_end_at")),
            "duration_minutes": _clean_float(response.get("duration_minutes")),
            "is_completed": response.get("is_completed"),
        }

        seen_subtests = set()
        for answer in answers:
            answer_value = answer.get("answer") or {}
            if not isinstance(answer_value, dict) or "cells" not in answer_value:
                continue

            question = question_lookup.get(answer.get("question_id"), {})
            subtest_name = _infer_subtest_name(question, answer_value, seen_subtests)
            seen_subtests.add(subtest_name)

            row[f"{subtest_name}_total_correct"] = _clean_int(answer_value.get("total_correct"))
            row[f"{subtest_name}_total_incorrect"] = _clean_int(answer_value.get("total_incorrect"))
            row[f"{subtest_name}_total_attempted"] = _clean_int(answer_value.get("total_attempted"))
            row[f"{subtest_name}_total_not_attempted"] = _clean_int(answer_value.get("total_incomplete"))
            row[f"{subtest_name}_time_taken"] = _clean_float(answer_value.get("total_time_taken"))
            row[f"{subtest_name}_assessment_completed"] = answer_value.get("assessment_completed")
            row[f"{subtest_name}_stop_rule"] = answer_value.get("stop_rule")
            row[f"{subtest_name}_timer_elapsed"] = answer_value.get("timer_elapsed")

        rows.append(row)

    dataframe = pd.DataFrame(rows)
    if "response_date" in dataframe.columns:
        dataframe = dataframe.sort_values("response_date", ascending=False).reset_index(drop=True)

    return dataframe


def import_teampact_assessment_data(
    survey_id: int,
    api_token: str | None = None,
) -> pd.DataFrame:
    raw_data = get_raw_teampact_assessment_data(
        survey_id=survey_id,
        api_token=api_token,
    )
    return turn_teampact_assessment_data_into_dataframe(
        raw_data=raw_data,
        api_token=api_token,
    )


def get_raw_teampact_sessions_data(
    api_token: str | None = None,
    year: int = 2026,
    per_page: int = 100,
) -> dict:
    headers = _get_headers(api_token)
    all_records = []
    page = 1
    last_page = 1

    while True:
        payload = _request_json(
            TEAMPACT_SESSIONS_URL,
            headers=headers,
            params={"page": page, "per_page": per_page},
        )

        page_records = payload.get("data", [])
        if not page_records:
            break

        all_records.extend(page_records)
        meta = payload.get("meta", {})
        last_page = meta.get("last_page", page)

        if page >= last_page:
            break

        page += 1
        time.sleep(0.2)

    return {
        "attendance_records": all_records,
        "year": year,
        "meta": {
            "pages_fetched": page,
            "last_page": last_page,
            "total_records": len(all_records),
        },
    }


def turn_teampact_sessions_data_into_dataframe(raw_data: dict) -> pd.DataFrame:
    target_year = raw_data.get("year", 2026)
    rows = []

    for record in raw_data.get("attendance_records", []):
        session_data = record.get("session") or {}
        participant_data = record.get("participant") or {}
        user_data = record.get("user") or {}
        session_tags = session_data.get("session_tags") or []

        letters_taught = []
        session_tag_ids = []
        session_tag_group_ids = []

        for tag in session_tags:
            if tag.get("name"):
                letters_taught.append(tag.get("name"))
            if tag.get("id") is not None:
                session_tag_ids.append(str(tag["id"]))

            pivot = tag.get("pivot") or {}
            if pivot.get("group_id") is not None:
                session_tag_group_ids.append(str(pivot["group_id"]))

        session_started_at = _parse_datetime(record.get("session_started_at"))
        if pd.isna(session_started_at) or session_started_at.year != target_year:
            continue

        row = {
            "attendance_id": record.get("id"),
            "session_id": record.get("session_id"),
            "participant_id": record.get("participant_id"),
            "participant_name": record.get("participant_name"),
            "participant_firstname": participant_data.get("firstname"),
            "participant_lastname": participant_data.get("lastname"),
            "participant_gender": _clean_int(participant_data.get("gender")),
            "user_id": record.get("user_id"),
            "user_name": record.get("user_name"),
            "user_email": user_data.get("email"),
            "class_id": record.get("class_id"),
            "class_name": record.get("class_name"),
            "program_id": record.get("program_id"),
            "program_name": record.get("program_name"),
            "organisation_name": record.get("organisation_name"),
            "session_text": session_data.get("text"),
            "session_topic": session_data.get("topic"),
            "session_started_at": session_started_at,
            "session_ended_at": _parse_datetime(record.get("session_ended_at")),
            "session_duration": _clean_int(session_data.get("session_duration")),
            "attendance_status": record.get("attendance_status"),
            "check_in_time": _parse_datetime(record.get("check_in_time")),
            "participant_total": _clean_int(session_data.get("participant_total")),
            "attended_total": _clean_int(session_data.get("attended_total")),
            "attended_percentage": _clean_float(session_data.get("attended_percentage")),
            "attended_male_total": _clean_int(session_data.get("attended_male_total")),
            "attended_female_total": _clean_int(session_data.get("attended_female_total")),
            "letters_taught": ", ".join(letters_taught),
            "num_letters_taught": len(letters_taught),
            "session_tag_ids": ",".join(session_tag_ids),
            "session_tag_group_ids": ",".join(session_tag_group_ids),
            "is_flagged": record.get("is_flagged", False),
            "flag_reason": record.get("flag_reason"),
        }
        rows.append(row)

    dataframe = pd.DataFrame(rows)
    if "session_started_at" in dataframe.columns:
        dataframe = dataframe.sort_values("session_started_at", ascending=False).reset_index(drop=True)

    return dataframe


def import_teampact_sessions_data(
    year: int = 2026,
    api_token: str | None = None,
) -> pd.DataFrame:
    raw_data = get_raw_teampact_sessions_data(
        api_token=api_token,
        year=year,
    )
    return turn_teampact_sessions_data_into_dataframe(raw_data=raw_data)

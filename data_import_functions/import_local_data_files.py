from pathlib import Path

import pandas as pd


SAMPLE_DATA_FOLDER = Path(__file__).resolve().parent.parent / "sample_data"

AVAILABLE_LOCAL_DATA_FILES = {
    "children_2024_results": "2024_childrens_results.csv",
    "children_2025_results": "2025_childrens_results.csv",
}


def _get_sample_data_file_path(dataset_name: str) -> Path:
    if dataset_name not in AVAILABLE_LOCAL_DATA_FILES:
        allowed_values = ", ".join(sorted(AVAILABLE_LOCAL_DATA_FILES))
        raise ValueError(
            f"Unknown dataset_name '{dataset_name}'. Choose one of: {allowed_values}"
        )

    return SAMPLE_DATA_FOLDER / AVAILABLE_LOCAL_DATA_FILES[dataset_name]


def import_local_csv_data(dataset_name: str) -> pd.DataFrame:
    """
    Load one local CSV file from the sample_data folder into a DataFrame.
    """
    file_path = _get_sample_data_file_path(dataset_name)
    return pd.read_csv(file_path)


def import_2024_childrens_results() -> pd.DataFrame:
    """
    Load the 2024 children's results CSV file into a DataFrame.
    """
    dataframe = import_local_csv_data("children_2024_results")

    if "Language" in dataframe.columns:
        dataframe["Language"] = dataframe["Language"].astype(str).str.strip()

    return dataframe


def import_2025_childrens_results() -> pd.DataFrame:
    """
    Load the 2025 children's results CSV file into a DataFrame.
    """
    dataframe = import_local_csv_data("children_2025_results")

    if "Language" in dataframe.columns:
        dataframe["Language"] = dataframe["Language"].astype(str).str.strip()

    return dataframe

from datetime import datetime
from pathlib import Path

import pandas as pd


DEFAULT_SESSIONS_CACHE_DIR = Path("data/sessions")
CURRENT_SESSIONS_CACHE_FILENAME = "sessions-current.csv"


def get_current_sessions_cache_path(
    cache_dir: str | Path = DEFAULT_SESSIONS_CACHE_DIR,
) -> Path:
    return Path(cache_dir) / CURRENT_SESSIONS_CACHE_FILENAME


def get_sessions_cache_last_updated(
    cache_dir: str | Path = DEFAULT_SESSIONS_CACHE_DIR,
) -> datetime | None:
    current_path = get_current_sessions_cache_path(cache_dir)
    if not current_path.exists():
        return None
    return datetime.fromtimestamp(current_path.stat().st_mtime)


def load_current_sessions_cache(
    cache_dir: str | Path = DEFAULT_SESSIONS_CACHE_DIR,
) -> pd.DataFrame:
    current_path = get_current_sessions_cache_path(cache_dir)
    return pd.read_csv(current_path)


def save_sessions_cache(
    dataframe: pd.DataFrame,
    cache_dir: str | Path = DEFAULT_SESSIONS_CACHE_DIR,
    timestamp: datetime | None = None,
) -> tuple[Path, Path]:
    timestamp = timestamp or datetime.now()
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    archive_path = cache_path / f"{timestamp:%Y-%m-%d-%H%M%S}-sessions.csv"
    current_path = get_current_sessions_cache_path(cache_path)

    dataframe.to_csv(archive_path, index=False)
    dataframe.to_csv(current_path, index=False)

    return archive_path, current_path

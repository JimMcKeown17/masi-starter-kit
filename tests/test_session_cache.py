import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import pandas as pd

from data_import_functions.session_cache import get_current_sessions_cache_path
from data_import_functions.session_cache import load_current_sessions_cache
from data_import_functions.session_cache import save_sessions_cache


class SessionCacheTests(unittest.TestCase):
    def test_save_sessions_cache_writes_archive_and_current_csv(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            cache_dir = Path(temporary_directory)
            dataframe = pd.DataFrame(
                [
                    {
                        "Session Date": "2026-05-19",
                        "School": "Empumalanga",
                    }
                ]
            )

            archive_path, current_path = save_sessions_cache(
                dataframe=dataframe,
                cache_dir=cache_dir,
                timestamp=datetime(2026, 6, 18, 10, 30, 5),
            )

            self.assertEqual(archive_path, cache_dir / "2026-06-18-103005-sessions.csv")
            self.assertEqual(current_path, cache_dir / "sessions-current.csv")
            self.assertTrue(archive_path.exists())
            self.assertTrue(current_path.exists())

            archived_dataframe = pd.read_csv(archive_path)
            current_dataframe = pd.read_csv(current_path)
            pd.testing.assert_frame_equal(archived_dataframe, dataframe)
            pd.testing.assert_frame_equal(current_dataframe, dataframe)

    def test_save_sessions_cache_overwrites_current_without_overwriting_archive(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            cache_dir = Path(temporary_directory)
            first_dataframe = pd.DataFrame([{"School": "Empumalanga"}])
            second_dataframe = pd.DataFrame([{"School": "Seyisi"}])

            first_archive_path, current_path = save_sessions_cache(
                dataframe=first_dataframe,
                cache_dir=cache_dir,
                timestamp=datetime(2026, 6, 18, 10, 30, 5),
            )
            second_archive_path, _ = save_sessions_cache(
                dataframe=second_dataframe,
                cache_dir=cache_dir,
                timestamp=datetime(2026, 6, 18, 11, 45, 30),
            )

            self.assertTrue(first_archive_path.exists())
            self.assertTrue(second_archive_path.exists())
            pd.testing.assert_frame_equal(pd.read_csv(first_archive_path), first_dataframe)
            pd.testing.assert_frame_equal(pd.read_csv(current_path), second_dataframe)

    def test_load_current_sessions_cache_reads_current_csv(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            cache_dir = Path(temporary_directory)
            dataframe = pd.DataFrame([{"School": "Qaqawuli Godolozi"}])
            current_path = get_current_sessions_cache_path(cache_dir)
            current_path.parent.mkdir(parents=True, exist_ok=True)
            dataframe.to_csv(current_path, index=False)

            result = load_current_sessions_cache(cache_dir=cache_dir)

            pd.testing.assert_frame_equal(result, dataframe)


if __name__ == "__main__":
    unittest.main()

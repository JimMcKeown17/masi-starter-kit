import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import pandas as pd

from data_import_functions.youth_cache import get_current_youth_cache_path
from data_import_functions.youth_cache import load_current_youth_cache
from data_import_functions.youth_cache import save_youth_cache


class YouthCacheTests(unittest.TestCase):
    def test_save_youth_cache_writes_archive_and_current_csv(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            cache_dir = Path(temporary_directory)
            dataframe = pd.DataFrame(
                [
                    {
                        "Full Name": "Nadia Ruiters",
                        "Employment Status": "Active",
                    }
                ]
            )

            archive_path, current_path = save_youth_cache(
                dataframe=dataframe,
                cache_dir=cache_dir,
                timestamp=datetime(2026, 6, 18, 11, 5, 30),
            )

            self.assertEqual(archive_path, cache_dir / "2026-06-18-110530-youth.csv")
            self.assertEqual(current_path, cache_dir / "youth-current.csv")
            self.assertTrue(archive_path.exists())
            self.assertTrue(current_path.exists())

            pd.testing.assert_frame_equal(pd.read_csv(archive_path), dataframe)
            pd.testing.assert_frame_equal(pd.read_csv(current_path), dataframe)

    def test_save_youth_cache_overwrites_current_without_overwriting_archive(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            cache_dir = Path(temporary_directory)
            first_dataframe = pd.DataFrame([{"Full Name": "Nadia Ruiters"}])
            second_dataframe = pd.DataFrame([{"Full Name": "Sipho Yose"}])

            first_archive_path, current_path = save_youth_cache(
                dataframe=first_dataframe,
                cache_dir=cache_dir,
                timestamp=datetime(2026, 6, 18, 11, 5, 30),
            )
            second_archive_path, _ = save_youth_cache(
                dataframe=second_dataframe,
                cache_dir=cache_dir,
                timestamp=datetime(2026, 6, 18, 11, 10, 45),
            )

            self.assertTrue(first_archive_path.exists())
            self.assertTrue(second_archive_path.exists())
            pd.testing.assert_frame_equal(pd.read_csv(first_archive_path), first_dataframe)
            pd.testing.assert_frame_equal(pd.read_csv(current_path), second_dataframe)

    def test_load_current_youth_cache_reads_current_csv(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            cache_dir = Path(temporary_directory)
            dataframe = pd.DataFrame([{"Full Name": "Sibongile Joni"}])
            current_path = get_current_youth_cache_path(cache_dir)
            current_path.parent.mkdir(parents=True, exist_ok=True)
            dataframe.to_csv(current_path, index=False)

            result = load_current_youth_cache(cache_dir=cache_dir)

            pd.testing.assert_frame_equal(result, dataframe)


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

import pandas as pd

from data_import_functions.import_airtable_data import import_airtable_literacy_sessions
from data_import_functions.import_airtable_data import import_airtable_youth
from data_import_functions.import_airtable_data import _resolve_literacy_session_linked_names
from data_import_functions.import_airtable_data import _collect_literacy_session_linked_record_ids


class LiteracySessionLinkedNameTests(unittest.TestCase):
    def test_collects_only_linked_record_ids_used_by_sessions(self):
        dataframe = pd.DataFrame(
            [
                {
                    "Literacy Coach Name": ["recCoach1"],
                    "School": ["recSchool1"],
                    "Child 1": ["recChild1"],
                    "Child 2": ["recChild2"],
                    "Children in Session": None,
                },
                {
                    "Literacy Coach Name": ["recCoach2"],
                    "School": ["recSchool1"],
                    "Children in Session": ["recChild2", "recChild3"],
                },
            ]
        )

        result = _collect_literacy_session_linked_record_ids(dataframe)

        self.assertEqual(result["youth"], {"recCoach1", "recCoach2"})
        self.assertEqual(result["schools"], {"recSchool1"})
        self.assertEqual(result["children"], {"recChild1", "recChild2", "recChild3"})

    def test_resolves_linked_record_ids_to_display_names(self):
        dataframe = pd.DataFrame(
            [
                {
                    "Literacy Coach Name": ["recCoach1"],
                    "School": ["recSchool1"],
                    "Child 1": ["recChild1"],
                    "Child 2": ["recChild2"],
                    "Children in Session": None,
                }
            ]
        )

        result = _resolve_literacy_session_linked_names(
            dataframe=dataframe,
            youth_display_map={"recCoach1": "Babalwa Njajula"},
            school_display_map={"recSchool1": "Empumalanga"},
            child_display_map={
                "recChild1": "akahlulwa buncwele sompondo",
                "recChild2": "kungentando lupha",
            },
        )

        self.assertEqual(result.loc[0, "Literacy Coach Name"], ["Babalwa Njajula"])
        self.assertEqual(result.loc[0, "School"], ["Empumalanga"])
        self.assertEqual(
            result.loc[0, "Children in Session"],
            ["akahlulwa buncwele sompondo", "kungentando lupha"],
        )
        self.assertEqual(result.loc[0, "Literacy Coach Record IDs"], ["recCoach1"])
        self.assertEqual(result.loc[0, "School Record IDs"], ["recSchool1"])
        self.assertEqual(result.loc[0, "Children in Session Record IDs"], ["recChild1", "recChild2"])

    def test_keeps_unknown_linked_record_ids_visible(self):
        dataframe = pd.DataFrame(
            [
                {
                    "Literacy Coach Name": ["recMissing"],
                    "School": ["recSchool1"],
                    "Children in Session": ["recChild1", "recMissingChild"],
                }
            ]
        )

        result = _resolve_literacy_session_linked_names(
            dataframe=dataframe,
            youth_display_map={},
            school_display_map={"recSchool1": "Empumalanga"},
            child_display_map={"recChild1": "akahlulwa buncwele sompondo"},
        )

        self.assertEqual(result.loc[0, "Literacy Coach Name"], ["recMissing"])
        self.assertEqual(
            result.loc[0, "Children in Session"],
            ["akahlulwa buncwele sompondo", "recMissingChild"],
        )

    def test_literacy_sessions_can_return_all_airtable_columns_with_display_names(self):
        airtable_dataframe = pd.DataFrame(
            [
                {
                    "Extra Airtable Field": "kept",
                    "Sounds Covered 2": "h,n",
                    "Blending Level": "CV Blending",
                    "Created": "2026-06-18",
                    "Children in Session": ["recChild1"],
                    "Site Type": ["Primary"],
                    "School": ["recSchool1"],
                    "Literacy Coach Name": ["recCoach1"],
                    "Session Record": 18477,
                    "Session Date": "2026-05-19",
                }
            ]
        )

        def fake_display_map(
            base_id,
            table_name,
            display_field,
            airtable_token=None,
            record_ids=None,
        ):
            return {
                "Youth DB": {"recCoach1": "Babalwa Njajula"},
                "Schools DB": {"recSchool1": "Empumalanga"},
                "Child DB": {"recChild1": "akahlulwa buncwele sompondo"},
            }[table_name]

        with (
            patch(
                "data_import_functions.import_airtable_data._get_required_env_var",
                side_effect=lambda name: {
                    "AIRTABLE_MASI_WEEKLY_SESSIONS_BASE_ID": "base123",
                    "AIRTABLE_MASI_WEEKLY_SESSIONS_TABLE_NAME": "Sessions",
                }[name],
            ),
            patch(
                "data_import_functions.import_airtable_data.import_airtable_table",
                return_value=airtable_dataframe,
            ),
            patch(
                "data_import_functions.import_airtable_data._get_airtable_record_display_map",
                side_effect=fake_display_map,
            ),
        ):
            result = import_airtable_literacy_sessions(include_all_columns=True)

        self.assertIn("Extra Airtable Field", result.columns)
        self.assertEqual(
            list(result.columns[:9]),
            [
                "Session Record",
                "Literacy Coach Name",
                "School",
                "Site Type",
                "Children in Session",
                "Session Date",
                "Created",
                "Blending Level",
                "Sounds Covered 2",
            ],
        )
        self.assertEqual(result.loc[0, "Extra Airtable Field"], "kept")
        self.assertEqual(result.loc[0, "Literacy Coach Name"], "Babalwa Njajula")
        self.assertEqual(result.loc[0, "School"], "Empumalanga")
        self.assertEqual(result.loc[0, "Children in Session"], "akahlulwa buncwele sompondo")


class YouthLinkedNameTests(unittest.TestCase):
    def test_youth_all_columns_keep_readable_names_and_preserve_link_ids(self):
        airtable_dataframe = pd.DataFrame(
            [
                {
                    "Extra Youth Field": "kept",
                    "Office Link": ["recOffice1"],
                    "Basic Link": ["recBasic1"],
                    "Site Placement": ["Daniels"],
                    "Mentor": ["Sibongile Joni"],
                    "Employment Status": ["Active"],
                    "Job Title": ["Zazi Izandi Coach"],
                    "Employee ID": 123,
                    "Full Name": ["Nadia Ruiters"],
                }
            ]
        )

        with (
            patch(
                "data_import_functions.import_airtable_data._get_required_env_var",
                side_effect=lambda name: {
                    "AIRTABLE_YOUTH_DB_BASE": "base123",
                    "AIRTABLE_COMBINED_YOUTH_DB_TABLE": "Youth",
                }[name],
            ),
            patch(
                "data_import_functions.import_airtable_data.import_airtable_table",
                return_value=airtable_dataframe,
            ),
        ):
            result = import_airtable_youth(include_all_columns=True)

        self.assertEqual(
            list(result.columns[:8]),
            [
                "Employee ID",
                "Full Name",
                "Job Title",
                "Employment Status",
                "Site Placement",
                "Mentor",
                "Basic Link",
                "Office Link",
            ],
        )
        self.assertEqual(result.loc[0, "Extra Youth Field"], "kept")
        self.assertEqual(result.loc[0, "Full Name"], "Nadia Ruiters")
        self.assertEqual(result.loc[0, "Basic Link"], "Nadia Ruiters")
        self.assertEqual(result.loc[0, "Office Link"], "Daniels")
        self.assertEqual(result.loc[0, "Basic Link Record IDs"], "recBasic1")
        self.assertEqual(result.loc[0, "Office Link Record IDs"], "recOffice1")


if __name__ == "__main__":
    unittest.main()

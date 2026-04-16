# Masi Starter Repo

This repo is a very simple starting point for beginner staff learning:

- basic Python
- pandas
- Streamlit
- how to work with real Masi data

This starter repo uses:

- read-only APIs
- simple local CSV files

The teaching flow is:

1. Import one data function into `main.py`
2. Run the function
3. Store the result in a pandas dataframe
4. Explore that dataframe with pandas and Streamlit

## Folder Structure

- `main.py`
  The main Streamlit file. Keep this simple.
- `data_import_functions/import_teampact_data.py`
  Functions for loading TeamPact data into pandas dataframes.
- `data_import_functions/import_airtable_data.py`
  Functions for loading Airtable data into pandas dataframes.
- `data_import_functions/import_local_data_files.py`
  Functions for loading local sample CSV files into pandas dataframes.
- `sample_data/`
  Real Masi CSV files for beginner practice.
- `.env.example`
  Example environment variables.
- `requirements.txt`
  Required Python packages.

## Quick Start

1. Create a virtual environment.
2. Install the requirements.
3. Copy `.env.example` to `.env`
4. Add your real credentials to `.env`
5. Run:

```bash
streamlit run main.py
```

## Some Teampact Endpoints

https://teampact.co/api/analytics/v1/
[9:16 AM]https://teampact.co/api/analytics/v1/surveys/
[9:18 AM]https://teampact.co/api/analytics/v1/surveys/816
[9:19 AM]https://teampact.co/api/analytics/v1/surveys/816/responses

## Example: TeamPact Assessment Data

```python
from data_import_functions.import_teampact_data import import_teampact_assessment_data

dataframe = import_teampact_assessment_data(survey_id=817)
```

## Example: TeamPact Sessions Data

```python
from data_import_functions.import_teampact_data import import_teampact_sessions_data

dataframe = import_teampact_sessions_data(year=2026)
```

## Example: Airtable Data

```python
from data_import_functions.import_airtable_data import import_airtable_literacy_sessions

dataframe = import_airtable_literacy_sessions()
```

## Example: Local 2024 Results File

```python
from data_import_functions.import_local_data_files import import_2024_childrens_results

dataframe = import_2024_childrens_results()
```

## Example: Local 2025 Results File

```python
from data_import_functions.import_local_data_files import import_2025_childrens_results

dataframe = import_2025_childrens_results()
```

## Example: Basic pandas work

```python
st.write(dataframe.head())
st.write(dataframe.columns)

grade_counts = dataframe["Grade"].value_counts()
st.write(grade_counts)
```

## Airtable Import Helpers

These helpers fetch Airtable data, clean the common Airtable list formatting,
and return a pandas dataframe.

```python
from data_import_functions.import_airtable_data import import_airtable_2025_assessments
from data_import_functions.import_airtable_data import import_airtable_children
from data_import_functions.import_airtable_data import import_airtable_literacy_sessions
from data_import_functions.import_airtable_data import import_airtable_numeracy_2026_sessions
from data_import_functions.import_airtable_data import import_airtable_schools
from data_import_functions.import_airtable_data import import_airtable_staff
from data_import_functions.import_airtable_data import import_airtable_youth
```

Available helpers:

- `import_airtable_schools()`
- `import_airtable_literacy_sessions()`
- `import_airtable_2025_assessments()`
- `import_airtable_children()`
- `import_airtable_staff()`
- `import_airtable_youth()`
- `import_airtable_numeracy_2026_sessions()`

Notes:

- `import_airtable_numeracy_2026_assessments()` still exists as a backwards-compatible alias.
- `import_airtable_table()` is still available if you want the raw Airtable fields without cleaning.

## Why There Is No Database Connection

This starter repo does not connect directly to a Masi database.

That keeps the learning setup safer and simpler for beginners.

## Included Local Files

The starter repo now includes these real Masi CSV files:

- `sample_data/2024_childrens_results.csv`
- `sample_data/2025_childrens_results.csv`

These files are for internal learning use only.

## Ideas For First Lessons

- Load one TeamPact survey and inspect the columns
- Load one Airtable table and inspect the columns
- Load the 2024 children's results file and count learners by grade
- Load the 2025 children's results file and filter to one language
- Show the first 5 rows with `head()`
- Group data by school, class, or program
- Plot simple totals in Streamlit

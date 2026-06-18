import streamlit as st

# Let's import the literacy sessions.
from data_import_functions.import_airtable_data import import_airtable_literacy_sessions
from data_import_functions.session_cache import get_current_sessions_cache_path
from data_import_functions.session_cache import get_sessions_cache_last_updated
from data_import_functions.session_cache import load_current_sessions_cache
from data_import_functions.session_cache import save_sessions_cache

# This title shows at the top of the page.
st.title("Sessions")
st.write("This page shows literacy sessions captured in Airtable.")

current_sessions_path = get_current_sessions_cache_path()

if st.button("Refresh from Airtable"):
    with st.spinner("Fetching session data from Airtable..."):
        try:
            sessions_dataframe = import_airtable_literacy_sessions(include_all_columns=True)
            archive_path, current_path = save_sessions_cache(sessions_dataframe)
        except Exception as error:
            st.error(
                "Sorry, the session data could not be refreshed.\n\n"
                "Please check that your .env file has the correct Airtable settings."
            )
            # Show the technical details in case they are helpful.
            st.exception(error)
            # st.stop() tells Streamlit to stop running the rest of the page.
            st.stop()

    st.success(
        f"Session data refreshed. Saved {current_path} and archive {archive_path.name}."
    )

if not current_sessions_path.exists():
    st.info(
        "No saved sessions file yet. Click 'Refresh from Airtable' to create one."
    )
    st.stop()

with st.spinner("Loading saved session data..."):
    try:
        sessions_dataframe = load_current_sessions_cache()
    except Exception as error:
        st.error(
            "Sorry, the saved session data could not be loaded.\n\n"
            "Try refreshing from Airtable to rebuild the CSV file."
        )
        # Show the technical details in case they are helpful.
        st.exception(error)
        st.stop()

last_updated = get_sessions_cache_last_updated()
if last_updated:
    st.caption(
        f"Loaded from {current_sessions_path}."
        f" Last updated: {last_updated:%Y-%m-%d %H:%M:%S}."
    )


st.dataframe(sessions_dataframe)

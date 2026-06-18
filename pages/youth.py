import streamlit as st

# Let's import the youth.
from data_import_functions import import_airtable_youth
from data_import_functions.youth_cache import get_current_youth_cache_path
from data_import_functions.youth_cache import get_youth_cache_last_updated
from data_import_functions.youth_cache import load_current_youth_cache
from data_import_functions.youth_cache import save_youth_cache


# This title shows at the top of the page.
st.title("Youth")
st.write("This page shows how many youth are currently active.")

current_youth_path = get_current_youth_cache_path()

if st.button("Refresh from Airtable"):
    with st.spinner("Fetching youth data from Airtable..."):
        try:
            youth_dataframe = import_airtable_youth(include_all_columns=True)
            archive_path, current_path = save_youth_cache(youth_dataframe)
        except Exception as error:
            st.error(
                "Sorry, the youth data could not be refreshed.\n\n"
                "Please check that your .env file has the correct Airtable settings."
            )
            # Show the technical details in case they are helpful.
            st.exception(error)
            # st.stop() tells Streamlit to stop running the rest of the page.
            st.stop()

    st.success(
        f"Youth data refreshed. Saved {current_path} and archive {archive_path.name}."
    )

if not current_youth_path.exists():
    st.info("No saved youth file yet. Click 'Refresh from Airtable' to create one.")
    st.stop()

with st.spinner("Loading saved youth data..."):
    try:
        youth_dataframe = load_current_youth_cache()
    except Exception as error:
        st.error(
            "Sorry, the saved youth data could not be loaded.\n\n"
            "Try refreshing from Airtable to rebuild the CSV file."
        )
        # Show the technical details in case they are helpful.
        st.exception(error)
        st.stop()

last_updated = get_youth_cache_last_updated()
if last_updated:
    st.caption(
        f"Loaded from {current_youth_path}."
        f" Last updated: {last_updated:%Y-%m-%d %H:%M:%S}."
    )

status_counts = youth_dataframe["Employment Status"].value_counts()


active_youth_count = int(status_counts.get("Active", 0))


st.metric(label="Active youth", value=active_youth_count)



st.subheader("Youth by employment status")
st.bar_chart(status_counts)


with st.expander("See the raw youth data"):
    st.dataframe(youth_dataframe)

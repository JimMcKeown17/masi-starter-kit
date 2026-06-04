

import streamlit as st

# Let's import the youth.
from data_import_functions import import_airtable_youth



# This title shows at the top of the page.
st.title("Youth")
st.write("This page shows how many youth are currently active.")



# message instead of a scary error.
with st.spinner("Loading youth data..."):
    try:
        youth_dataframe = import_airtable_youth()
    except Exception as error:
        st.error(
            "Sorry, the youth data could not be loaded.\n\n"
            "Please check that your .env file has the correct Airtable settings."
        )
        # Show the technical details in case they are helpful.
        st.exception(error)
        # st.stop() tells Streamlit to stop running the rest of the page.
        st.stop()


status_counts = youth_dataframe["Employment Status"].value_counts()


active_youth_count = int(status_counts.get("Active", 0))


st.metric(label="Active youth", value=active_youth_count)



st.subheader("Youth by employment status")
st.bar_chart(status_counts)


with st.expander("See the raw youth data"):
    st.dataframe(youth_dataframe)

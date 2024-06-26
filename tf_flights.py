import streamlit as st
from streamlit_gsheets import GSheetsConnection
import requests
from bs4 import BeautifulSoup as bs
import datetime
import airportsdata
import time
import pandas as pd
import altair as alt

st.set_page_config(page_title="Tup's Flight Tracker", page_icon="✈️")


def ping_plane_info(tail_number: str) -> dict:
    """Ping the FAA registry for plane info
    TODO: Add airfleets.net
    """

    try:
        empty = ""
        plane_info = {
            "serial_number": "",
            "manufacturer": "",
            "model": "",
            "manufactured_year": "",
            "registered_owner": "",
            "engine_model": "",
            "aw_date": "",
            "engine_manufacturer": "",
            "aircraft_type": "",
        }

        return plane_info
    # Add the info to the sheet for each row
    except AttributeError:
        st.error("No plane info found for this tail number")
        pass

    return


# Read the data and clean it up
def get_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read()
    full_data = df[~df["tail_number"].isnull()]
    full_data["origin"] = full_data["origin"].str.upper()
    full_data["destination"] = full_data["destination"].str.upper()
    full_data["date"] = pd.to_datetime(full_data["date"]).dt.date

    return full_data, conn


full_data, conn = get_data()
st.cache_data.clear()
airports = airportsdata.load("IATA")  # key is the IATA location code
airport_codes = sorted(list(airports.keys()))

st.header("✈️ Tup's Flight Tracker 🌎")
st.write(
    """Enter new flights and visualize your data. Merry Christmas, Tup! Check on the data 
    [here](https://docs.google.com/spreadsheets/d/1r0CEyglssx3wOljj1R_2VQEc-NsbFtiOxS4ht1cmfCs/edit) 🎄
"""
)

# date
with st.expander("Flight Entry", expanded=True):
    with st.form("my_form"):
        st.subheader("Enter New Flight")
        col1, col2 = st.columns(2)
        dt = col1.date_input("Date of Flight", datetime.datetime.today())
        tn = col2.text_input("Tail Number", "960WN")
        origin = col1.selectbox("Origin", airport_codes, index=airport_codes.index("SJC"))
        destination = col2.selectbox("Destination", airport_codes, index=airport_codes.index("SEA"))

        submitted = st.form_submit_button("Submit")


if submitted:
    # Display the plane info
    plane_info = ping_plane_info(tn)

    # Filter the data for the tail number
    try:
        tail_data = full_data[full_data["tail_number"] == int(tn)]
    except ValueError:
        tail_data = full_data[full_data["tail_number"] == str(tn)]

    # if the tail number is in the data
    if tail_data.shape[0] > 0 and plane_info:
        st.info("You've flown this plane before! Adding flight entry...")
    elif tail_data.shape[0] > 0 and not plane_info:
        st.info("You've flown this plane before! Adding flight entry...")
    else:
        st.info("New plane! Adding flight entry...")

        # Add the info to full_data
    new_data = full_data.append(
        {
            "date": dt,
            "tail_number": tn,
            "origin": origin,
            "destination": destination,
            "registered_owner": plane_info["registered_owner"],
            "serial_number": plane_info["serial_number"],
            "manufacturer": plane_info["manufacturer"],
            "model": plane_info["model"],
            "aw_date": plane_info["aw_date"],
            "manufactured_year": plane_info["manufactured_year"],
            "engine_model": plane_info["engine_model"],
            "engine_manufacturer": plane_info["engine_manufacturer"],
            "aircraft_type": plane_info["aircraft_type"],
        },
        ignore_index=True,
    )
    full_data, conn = get_data()
    if new_data.shape[0] >= full_data.shape[0]:
        new_data = conn.update(data=new_data)
    else:
        st.error("Error adding flight data -- please contact Tyler to let him know!")
    st.cache_data.clear()
    full_data = new_data

    # Display the info
    if plane_info:
        with st.expander("Plane Info", expanded=True):
            col1, col2 = st.columns(2)
            # with col1:
            #     for val in plane_info.items():
            #         category = val[0].replace("_", " ").title()
            #         value = val[1]
            #         st.write(f"**{category}**: {value}")

            # Display the dates flown and the origin/destination
            with col1:
                st.write("**Flights on this plane**")
                for row in tail_data.iterrows():
                    st.write(
                        f"{row[1]['date'].strftime('%m/%d/%Y')}: {row[1]['origin']} to {row[1]['destination']}"
                    )


col1, col2, col3 = st.columns(3)

tail_number_counts = full_data["tail_number"].value_counts()
top_tail_number = tail_number_counts.index[0]
top_tail_number_count = tail_number_counts.values[0]

col1.metric("Total Flights", full_data.shape[0])
col2.metric("Number of Unique Destinations", full_data["destination"].nunique())

col3.metric("Top tailnumber", f"{top_tail_number} ({top_tail_number_count})")

st.subheader("Top Destinations")
dest_data = full_data.value_counts(["destination"]).reset_index()
dest_data.columns = ["destination", "count"]


chrt = (
    alt.Chart(dest_data.head(15))
    .mark_bar(color="#80221c", stroke="#ffffff", strokeWidth=1)
    .encode(
        x=alt.X("destination", sort="-y"),
        y="count",
        tooltip=["destination", "count"],
    )
    .interactive()
)
st.altair_chart(chrt, use_container_width=True)


st.subheader("Date Heatmap")
st.write("Which day of the year do you fly most often?")

# Prepare the data by extracting day and week
date_data = full_data.copy()
date_data["date"] = pd.to_datetime(date_data["date"])

# Display as Jan 1
date_data["display"] = date_data["date"].dt.strftime("%b %d")
date_data["day"] = date_data["date"].dt.day
date_data["month"] = date_data["date"].dt.month
date_data = date_data[["day", "month", "display"]].value_counts().reset_index()
date_data.columns = ["day", "month", "display", "value"]

# Create the heatmap
color = alt.Color("value:N", scale=alt.Scale(scheme="reds"))
filt_data = date_data[date_data["value"] > 0]
heatmap_1 = (
    alt.Chart(filt_data)
    .mark_bar(stroke="#ffffff", strokeWidth=0.6)
    .encode(
        x=alt.X("day:O", title="Day of the Month"),
        y=alt.Y("month:O", title="Month"),
        color=color,
        tooltip=["value", "display"],
    )
)

# Display the heatmap
col1, col2 = st.columns(2)
st.write("Yearly Heatmap")
st.altair_chart(heatmap_1, use_container_width=True)


# Explore top tail numbers
st.subheader("Top Tail Numbers")
tail_data = full_data["tail_number"].value_counts().reset_index()
tail_data.columns = ["tail_number", "count"]
selected_plane = st.selectbox("Select a plane", tail_data["tail_number"])
plane_data = full_data[full_data["tail_number"] == selected_plane]

plane_metadata = plane_data[
    [
        "registered_owner",
        "serial_number",
        "manufacturer",
        "model",
        "manufactured_year",
        "engine_model",
        "engine_manufacturer",
        "aircraft_type",
    ]
].head(1)


col1, col2 = st.columns(2)
with col1:
    st.write("**Plane Info**")
    for val in plane_metadata.to_dict().items():
        category = val[0].replace("_", " ").title()
        value = val[1].values()
        v2 = str(list(value)[0])
        if v2 != "nan":
            st.write(f"**{category}**: {list(value)[0]}")
with col2:
    # Print out the dates flown and the origin/destination
    st.write("**Flights on this plane**")
    for row in plane_data.iterrows():
        st.write(
            f"{row[1]['date'].strftime('%m/%d/%Y')}: {row[1]['origin']} to {row[1]['destination']}"
        )

with st.expander("Raw Data"):
    st.write(full_data)

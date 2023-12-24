import streamlit as st
from streamlit_gsheets import GSheetsConnection
import requests
from bs4 import BeautifulSoup as bs
import datetime
import airportsdata
import time
import pandas as pd
import altair as alt


def ping_plane_info(tail_number: str) -> dict:
    """Ping the FAA registry for plane info"""
    try:
        response = requests.get(
            "https://registry.faa.gov/AircraftInquiry/Search/NNumberResult?nNumberTxt="
            + str(tail_number),
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
            },
        )
        soup = bs(response.content, "html.parser")

        # Get plane info
        serial_number = soup.find("td", {"data-label": "Serial Number"}).text.strip()
        manufacturer = soup.find("td", {"data-label": "Manufacturer Name"}).text.strip()
        model = soup.find("td", {"data-label": "Model"}).text.strip()
        mfr_year = soup.find("td", {"data-label": "Mfr Year"}).text.strip()
        registered_owner = soup.find("td", {"data-label": "Name"}).text.strip()
        engine_model = soup.find("td", {"data-label": "Engine Model"}).text.strip()
        aw_date = soup.find("td", {"data-label": "A/W Date"}).text.strip()
        engine_manufacturer = soup.find("td", {"data-label": "Engine Manufacturer"}).text.strip()
        aircraft_type = soup.find("td", {"data-label": "Aircraft Type"}).text.strip()
        date_change_auth = soup.find("td", {"data-label": "Date Change Authorized"}).text.strip()

        plane_info = {
            "serial_number": serial_number,
            "manufacturer": manufacturer,
            "model": model,
            "manufactured_year": mfr_year,
            "registered_owner": registered_owner,
            "engine_model": engine_model,
            "aw_date": aw_date,
            "engine_manufacturer": engine_manufacturer,
            "aircraft_type": aircraft_type,
            "date_change_auth": date_change_auth,
        }
        st.info("Plane found! Adding flight entry")
    # Add the info to the sheet for each row
    except AttributeError:
        st.info("Plane not found, adding entry anyway")
        pass

    return plane_info


# Read the data and clean it up
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read()
full_data = df[~df["tail_number"].isnull()]
full_data["origin"] = full_data["origin"].str.upper()
full_data["destination"] = full_data["destination"].str.upper()
full_data["date"] = pd.to_datetime(full_data["date"]).dt.date

airports = airportsdata.load("IATA")  # key is the IATA location code
airport_codes = sorted(list(airports.keys()))

st.header("Tup's Flight Tracker")
st.write("Enter new flights and visualize your data. 🛫 Merry Christmas, Tup! 🎄")

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
    tail_data = full_data[full_data["tail_number"] == tn]

    # if the tail number is in the data
    if tail_data.shape[0] > 0:
        st.info("You've flown this plane before! Adding flight entry")

        # Display the info

    else:
        st.info("New plane! Adding flight entry")

        # Display the tail number info

    # TODO: add the new entry to the data


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

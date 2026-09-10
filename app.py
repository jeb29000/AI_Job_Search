import streamlit as st
import pandas as pd

from job_sources import search_jobs

from ollama_ai import (
    analyze_job_matches
)

from utils import convert_to_excel

# Configure the Streamlit page
st.set_page_config(
    page_title="AI Job Search Assistant",
    page_icon="💼",
    layout="wide"
)


# Application title
st.title("💼 AI Job Search Assistant")

st.write(
    "Search for recent job opportunities "
    "and download the results as an Excel file."
)


# Job title input
job_title = st.text_input(
    "Job Title",
    placeholder="Example: Python Developer"
)


# Location input
location = st.text_input(
    "Location",
    placeholder="Example: Berlin"
)

# ==========================================
# AI JOB MATCHING
# ==========================================

st.subheader(
    "🤖 AI Job Matching"
)


use_ai = st.checkbox(
    "Use local Ollama AI matching",
    value=False
)


candidate_profile = st.text_area(
    "Your skills and experience",
    placeholder=(
        "Example: Python, SQL, Tableau, "
        "Power BI, Excel, data analysis, "
        "machine learning..."
    ),
    disabled=not use_ai
)


if use_ai:

    st.caption(
        "AI matching runs locally through "
        "Ollama for the first 5 jobs. The current score is based "
        "mainly on job title and basic listing "
        "information because full job "
        "descriptions are not yet available."

    )


# Job sources filter

selected_sources = st.multiselect(
    "Select Job Sources",
    options=[
        "Arbeitnow",
        "Bundesagentur",
        "LinkedIn",
        "Indeed"
    ],
    default=[
        "Arbeitnow",
        "Bundesagentur"
    ]
)

# Number of days filter
# ==========================================
# DATE FILTER
# ==========================================

date_filter = st.selectbox(
    "Show jobs posted within:",
    options=[
        "All time",
        "Last 24 hours",
        "Last 3 days",
        "Last 7 days",
        "Last 30 days"
    ],
    index=0
)


if date_filter == "All time":

    days = "All time"

elif date_filter == "Last 24 hours":

    days = 1

elif date_filter == "Last 3 days":

    days = 3

elif date_filter == "Last 7 days":

    days = 7

else:
    days = 30

# ==========================================
# REMOTE JOB FILTER
# ==========================================

remote_filter = st.selectbox(
    "Work Arrangement",
    options=[
        "All jobs",
        "Remote only",
        "Non-remote only"
    ],
    index=0
)

# ==========================================
# SORTING OPTIONS
# ==========================================

sort_option = st.selectbox(
    "Sort Results By",
    options=[
        "Newest first",
        "Oldest first",
        "Company A-Z",
        "Job title A-Z"
    ],
    index=0
)

# Search button
search_button = st.button(
    "🔍 Search Jobs"
)


# Run the search when the button is clicked
if search_button:

    # ======================================
    # CHECK SOURCE SELECTION
    # ======================================

    if not selected_sources:

        st.warning(
            "Please select at least one job source."
        )


    # ======================================
    # CHECK SEARCH INPUT
    # ======================================

    elif not job_title and not location:

        st.warning(
            "Please enter a job title or location."
        )


    # ======================================
    # SEARCH JOBS
    # ======================================

    else:

        with st.spinner(
            "Searching for jobs..."
        ):

            jobs = search_jobs(
                job_title,
                location,
                days,
                selected_sources,
                remote_filter,
                sort_option
            )

        # ==================================
        # OLLAMA AI MATCHING
        # ==================================

        if (
            jobs
            and
            use_ai
        ):

            if not candidate_profile.strip():

                st.warning(
                    "AI matching is enabled, "
                    "but your skills and "
                    "experience are empty."
                )


            else:

                with st.spinner(
                    "Ollama is analyzing "
                    "the first 5 jobs..."
                ):

                    ai_result = (
                        analyze_job_matches(
                            candidate_profile,
                            jobs,
                            max_jobs=5
                        )
                    )


                if ai_result.get(
                    "success"
                ):

                    # Set defaults first.
                    for job in jobs:

                        job[
                            "AI Match"
                        ] = "Not analyzed"

                        job[
                            "AI Reason"
                        ] = ""


                    # Add Ollama results.
                    for match in ai_result.get(
                        "matches",
                        []
                    ):

                        index = match.get(
                            "index"
                        )


                        if (
                            isinstance(
                                index,
                                int
                            )
                            and
                            0 <= index < len(jobs)
                        ):

                            jobs[index][
                                "AI Match"
                            ] = (
                                f"{match.get('score', 0)}%"
                            )

                            jobs[index][
                                "AI Reason"
                            ] = (
                                match.get(
                                    "reason",
                                    ""
                                )
                            )


                else:

                    st.warning(
                        "Ollama AI matching "
                        "could not run: "
                        f"{ai_result.get('error', 'Unknown error')}"
                    )
        # ==================================
        # DISPLAY RESULTS
        # ==================================

        if jobs:

            df = pd.DataFrame(
                jobs
            )


            display_columns = [
                "Title",
                "Company",
                "Location",
                "Posted",
                "Remote",
                "Source"
            ]


            if (
                use_ai
                and
                "AI Match" in df.columns
            ):

                display_columns.extend(
                    [
                        "AI Match",
                        "AI Reason"
                    ]
                )


            display_columns.append(
                "Link"
            )


            excel_file = (
                convert_to_excel(
                    df
                )
            )


            st.success(
                f"Found {len(df)} jobs!"
            )


            st.metric(
                "Jobs Found",
                len(df)
            )


            st.dataframe(
                df[
                    display_columns
                ],
                use_container_width=True
            )


            st.download_button(
                label=(
                    "📥 Download Job Listings as Excel"
                ),
                data=excel_file,
                file_name=(
                    "job_listings.xlsx"
                ),
                mime=(
                    "application/"
                    "vnd.openxmlformats-"
                    "officedocument."
                    "spreadsheetml.sheet"
                )
            )


        else:

            st.info(
                "No jobs found."
            )

st.caption(
    "Note: The AI matching feature is "
    "currently in beta and may not "
    "always provide accurate results."
    "If you want to use AI matching for your job search, please use the 'AI Match APP' ."
)
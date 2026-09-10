import os
import requests
import streamlit as st

from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus
from dotenv import load_dotenv


# ==========================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================

load_dotenv()


#=================API SETUP=================



# ==========================================
# ARBEITNOW API
# ==========================================

API_URL = "https://www.arbeitnow.com/api/job-board-api"


# ==========================================
# BUNDESAGENTUR API
# ==========================================

BUNDESAGENTUR_API_URL = (
    "https://rest.arbeitsagentur.de/"
    "jobboerse/jobsuche-service/"
    "pc/v6/jobs"
)


BUNDESAGENTUR_HEADERS = {
    "X-API-Key": "jobboerse-jobsuche"
}


# ==========================================
# THEIRSTACK API
# ==========================================

THEIRSTACK_API_URL = (
    "https://api.theirstack.com/"
    "v1/jobs/search"
)

THEIRSTACK_LOCATION_API_URL = (
    "https://api.theirstack.com/"
    "v0/catalog/locations"
)

THEIRSTACK_API_KEY = os.getenv(
    "THEIRSTACK_API_KEY"
)


THEIRSTACK_HEADERS = {
    "Authorization": (
        f"Bearer {THEIRSTACK_API_KEY}"
    ),
    "Accept": "application/json",
    "Content-Type": "application/json"
}


#========================END OF API SETUP========================




#============================================================================
#========================= FUNCTIONS =========================
#============================================================================



#========================= ARBEITNOW FUNCTIONS =========================

def get_all_jobs():
    """Get all available jobs from the API."""

    try:

        response = requests.get(
            API_URL,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        jobs = data.get(
            "data",
            []
        )

        print(
            f"Total jobs received from API: {len(jobs)}"
        )

        return jobs

    except requests.RequestException as error:

        print(
            f"API Error: {error}"
        )

        return []


def format_job(job):
    """
    Convert raw Arbeitnow API data
    into our standard job format.
    """

    # --------------------------------------
    # FORMAT POSTED DATE
    # --------------------------------------

    created_at = job.get(
        "created_at",
        ""
    )

    posted_date = ""

    try:

        # Arbeitnow normally gives us
        # a Unix timestamp.
        if isinstance(
            created_at,
            (int, float)
        ):

            posted_date = (
                datetime.fromtimestamp(
                    created_at,
                    tz=timezone.utc
                )
                .strftime(
                    "%Y-%m-%d"
                )
            )

        else:

            # Also support an ISO date
            # in case the API changes later.
            job_date = (
                datetime.fromisoformat(
                    str(created_at).replace(
                        "Z",
                        "+00:00"
                    )
                )
            )

            posted_date = (
                job_date.strftime(
                    "%Y-%m-%d"
                )
            )

    except (
        ValueError,
        TypeError,
        OSError
    ):

        posted_date = str(
            created_at
        )


    # --------------------------------------
    # CREATE CLEAN JOB
    # --------------------------------------

    formatted_job = {

        "Title": job.get(
            "title",
            "Not available"
        ),

        "Company": job.get(
            "company_name",
            "Not available"
        ),

        "Location": job.get(
            "location",
            "Not available"
        ),

        "Posted": posted_date,

        "Remote": job.get(
            "remote",
            False
        ),

        "Source": "Arbeitnow",

        "Link": job.get(
            "url",
            ""
        )
    }


    return formatted_job


def get_clean_jobs():
    """Get jobs and format them."""

    raw_jobs = get_all_jobs()

    clean_jobs = []

    for job in raw_jobs:

        formatted_job = format_job(
            job
        )

        clean_jobs.append(
            formatted_job
        )

    return clean_jobs


#============================End of Arbeitnow Functions============================



# ==========================================
# BUNDESAGENTUR FUNCTIONS
# ==========================================


def get_bundesagentur_raw_jobs(
    job_title="",
    location="",
    days=3
):
    """Get raw jobs from the Bundesagentur API."""


    # --------------------------------------
    # SEARCH PARAMETERS
    # --------------------------------------

    params = {
        "was": job_title,
        "wo": location,
        "page": 1,
        "size": 50
    }


    if days != "All time":

        params[
            "veroeffentlichtseit"
        ] = days

    response = None


    try:

        response = requests.get(
            BUNDESAGENTUR_API_URL,
            headers=BUNDESAGENTUR_HEADERS,
            params=params,
            timeout=30
        )


        print(
            "Bundesagentur status:",
            response.status_code
        )


        response.raise_for_status()

        data = response.json()

        print(
            "Bundesagentur response type:",
            type(data)
        )

        if isinstance(
            data,
            dict
        ):

            print(
                "Bundesagentur response keys:",
                data.keys()
            )

            print(
                "Total results reported:",
                data.get(
                    "maxErgebnisse",
                    "Not found"
                )
            )

        print(
            "Bundesagentur response preview:",
            str(data)[:1000]
        )

        return data

    except requests.RequestException as error:

        print(
            "Bundesagentur API Error:",
            error
        )

        if response is not None:

            print(
                "Response:",
                response.text
            )

        return {}

def format_bundesagentur_job(job):
    """
    Convert a raw Bundesagentur job
    into our standard job format.
    """


    # --------------------------------------
    # GET LOCATION
    # --------------------------------------

    locations = job.get(
        "stellenlokationen",
        []
    )


    location = "Not available"


    # Check whether locations exist
    if locations:

        # Get the first location
        first_location = locations[0]


        # Get address information
        address = first_location.get(
            "adresse",
            {}
        )


        # Get city
        location = address.get(
            "ort",
            "Not available"
        )


    # --------------------------------------
    # CREATE JOB LINK
    # --------------------------------------

    external_url = (
        job.get(
            "externeUrl"
        )
        or
        job.get(
            "externalUrl"
        )
        or
        ""
    )


    reference_number = (
        job.get(
            "referenznummer"
        )
        or
        job.get(
            "refnr"
        )
        or
        job.get(
            "chiffrenummer"
        )
        or
        ""
    )


# Prefer the original employer/job URL
# when Bundesagentur provides one.
    if external_url:

        job_link = external_url


# Otherwise create a Bundesagentur
# Jobsuche link using the reference number.
    elif reference_number:

        encoded_reference = quote_plus(
            str(
                reference_number
            )
        )


        job_link = (
            "https://www.arbeitsagentur.de/"
            "jobsuche/suche?"
            "angebotsart=1&"
            "suchbereich=jobs&"
            f"was={encoded_reference}"
        )


    # Final fallback
    else:

        job_link = (
            "https://www.arbeitsagentur.de/"
            "jobsuche/"
        )


    # --------------------------------------
    # CREATE CLEAN JOB
    # --------------------------------------

    formatted_job = {

        "Title": job.get(
            "stellenangebotsTitel",
            "Not available"
        ),

        "Company": job.get(
            "firma",
            "Not available"
        ),

        "Location": location,

        "Posted": job.get(
            "datumErsteVeroeffentlichung",
            ""
        ),

        "Remote": job.get(
            "homeofficemoeglich",
            False
        ),

        "Source": "Bundesagentur",

        "Link": job_link
    }


    return formatted_job

def get_bundesagentur_jobs(
    job_title,
    location,
    days
):
    """
    Get Bundesagentur jobs
    and convert them into
    our standard format.
    """


    # Get raw API response
    data = get_bundesagentur_raw_jobs(
        job_title,
        location,
        days
    )


    # Extract job list
    raw_jobs = data.get(
        "ergebnisliste",
        []
    )


    # Create empty clean job list
    clean_jobs = []


    # Process every job
    for job in raw_jobs:

        formatted_job = (
            format_bundesagentur_job(
                job
            )
        )


        clean_jobs.append(
            formatted_job
        )


    print(
        "Bundesagentur jobs found:",
        len(clean_jobs)
    )


    return clean_jobs


#============================End of Bundesagentur Functions============================


# ==========================================
# THEIRSTACK FUNCTIONS
# ==========================================


def format_theirstack_job(
    job,
    source_name
):
    """
    Convert one TheirStack job
    into our standard application
    job format.
    """


    # ======================================
    # JOB TITLE
    # ======================================

    title = (
        job.get(
            "job_title"
        )
        or
        job.get(
            "title"
        )
        or
        "Not available"
    )


    # ======================================
    # COMPANY
    # ======================================

    company = (
        job.get(
            "company_name"
        )
    )


    if not company:

        company_data = job.get(
            "company"
        )


        if isinstance(
            company_data,
            dict
        ):

            company = (
                company_data.get(
                    "name"
                )
            )


        elif company_data:

            company = str(
                company_data
            )


    if not company:

        company = "Not available"


    # ======================================
    # LOCATION
    # ======================================

    location = job.get(
        "location"
    )


    # Current TheirStack responses normally
    # provide location as a string.
    if isinstance(
        location,
        str
    ):

        location = (
            location.strip()
            or
            "Not available"
        )


    # Keep support for dictionary-style
    # responses just in case.
    elif isinstance(
        location,
        dict
    ):

        location = (
            location.get(
                "name"
            )
            or
            location.get(
                "city"
            )
            or
            "Not available"
        )


    else:

        location = "Not available"


    # ======================================
    # POSTED DATE
    # ======================================

    posted_value = (
        job.get(
            "date_posted"
        )
        or
        job.get(
            "posted_at"
        )
        or
        job.get(
            "created_at"
        )
        or
        ""
    )


    posted_date = ""


    try:

        if isinstance(
            posted_value,
            (int, float)
        ):

            posted_date = (
                datetime.fromtimestamp(
                    posted_value,
                    tz=timezone.utc
                )
                .strftime(
                    "%Y-%m-%d"
                )
            )


        elif posted_value:

            posted_date = (
                datetime.fromisoformat(
                    str(
                        posted_value
                    ).replace(
                        "Z",
                        "+00:00"
                    )
                )
                .strftime(
                    "%Y-%m-%d"
                )
            )


    except (
        ValueError,
        TypeError,
        OSError
    ):

        posted_date = str(
            posted_value
        )[:10]


    # ======================================
    # REMOTE STATUS
    # ======================================

    remote = bool(
        job.get(
            "remote",
            False
        )
    )


    # Support older/different responses too.
    if job.get(
        "is_remote"
    ) is True:

        remote = True


    workplace_types = (
        job.get(
            "workplace_types",
            []
        )
        or
        []
    )


    workplace_types_clean = [
        str(
            workplace_type
        ).lower()
        for workplace_type
        in workplace_types
    ]


    if "remote" in workplace_types_clean:

        remote = True


    # ======================================
    # JOB LINK
    # ======================================

    job_link = (
        job.get(
            "url"
        )
        or
        job.get(
            "source_url"
        )
        or
        job.get(
            "canonical_url"
        )
        or
        ""
    )


    # ======================================
    # CREATE STANDARD JOB
    # ======================================

    formatted_job = {

        "Title": title,

        "Company": company,

        "Location": location,

        "Posted": posted_date,

        "Remote": remote,

        "Source": source_name,

        "Link": job_link
    }


    return formatted_job


@st.cache_data(
    ttl=86400,
    max_entries=100,
    show_spinner=False
)

def get_theirstack_location_id(location):
    """Return the TheirStack location ID for a location name."""

    # ======================================
    # EMPTY LOCATION
    # ======================================

    if not location.strip():

        return None


    # ======================================
    # SEARCH PARAMETERS
    # ======================================

    params = {
        "name": location.strip(),
        "country_code": "DE",
        "feature_code": "PPL",
        "limit": 5
    }


    response = None


    try:

        response = requests.get(
            THEIRSTACK_LOCATION_API_URL,
            headers=THEIRSTACK_HEADERS,
            params=params,
            timeout=30
        )


        print(
            "TheirStack location status:",
            response.status_code
        )


        response.raise_for_status()


        locations = response.json()


        # ==================================
        # CHECK RESPONSE
        # ==================================

        if not isinstance(
            locations,
            list
        ):

            print(
                "Unexpected location response."
            )

            return None


        if not locations:

            print(
                "No TheirStack location found for:",
                location
            )

            return None


        # ==================================
        # TRY EXACT MATCH FIRST
        # ==================================

        location_clean = (
            location
            .lower()
            .strip()
        )


        for item in locations:

            location_name = str(
                item.get(
                    "name",
                    ""
                )
            ).lower().strip()


            if (
                location_name
                ==
                location_clean
            ):

                location_id = (
                    item.get(
                        "id"
                    )
                )


                print(
                    "TheirStack location ID:",
                    location_id
                )


                return location_id


        # ==================================
        # OTHERWISE USE FIRST RESULT
        # ==================================

        location_id = (
            locations[0].get(
                "id"
            )
        )


        print(
            "TheirStack location ID:",
            location_id
        )


        return location_id


    except (
        requests.RequestException,
        ValueError
    ) as error:

        print(
            "TheirStack location error:",
            error
        )


        return None

@st.cache_data(
    ttl=3600,
    max_entries=100,
    show_spinner=False
)

def get_theirstack_raw_jobs(
    job_title="",
    location="",
    source_domain="",
    days=30,
    limit=5
):
    """
    Get raw job listings from
    the TheirStack API.
    """


    # ======================================
    # CHECK API KEY
    # ======================================

    if not THEIRSTACK_API_KEY:

        print(
            "TheirStack API key is missing."
        )

        return {}


    # ======================================
    # CREATE REQUEST BODY
    # ======================================

    payload = {

    "job_country_code_or": [
        "DE"
    ],

    "limit": limit,

    "page": 0,

    "include_total_results": True
    }


    # ======================================
    # DATE FILTER
    # ======================================

    if days == "All time":

        payload[
            "posted_at_gte"
        ] = "2021-01-01"

    else:

        payload[
            "posted_at_max_age_days"
        ] = int(days)


    # ======================================
    # JOB TITLE FILTER
    # ======================================

    if job_title.strip():

        payload[
            "job_title_or"
        ] = [
            job_title.strip()
        ]


    # ======================================
    # SOURCE FILTER
    # ======================================

    if source_domain.strip():

        payload[
            "url_domain_or"
        ] = [
            source_domain.strip()
        ]


    # ======================================
    # LOCATION FILTER
    # ======================================

    if location.strip():

        location_id = (
            get_theirstack_location_id(
                location
            )
        )


        if location_id is None:

            print(
                "TheirStack search stopped "
                "because location was not found."
            )

            return {
                "data": []
            }


        payload[
            "job_location_or"
        ] = [
            {
                "id": location_id
            }
        ]


    # ======================================
    # DEBUG INFORMATION
    # ======================================

    print(
        "TheirStack title:",
        job_title
    )


    print(
        "TheirStack location:",
        location
    )


    print(
        "TheirStack source:",
        source_domain
    )


    print(
        "TheirStack days:",
        days
    )


    response = None


    try:

        # ==================================
        # SEND REQUEST
        # ==================================

        response = requests.post(
            THEIRSTACK_API_URL,
            headers=THEIRSTACK_HEADERS,
            json=payload,
            timeout=30
        )


        print(
            "TheirStack status:",
            response.status_code
        )


        response.raise_for_status()


        # ==================================
        # CONVERT JSON
        # ==================================

        data = response.json()


        print(
            "TheirStack response type:",
            type(data)
        )


        if isinstance(
            data,
            dict
        ):

            print(
                "TheirStack response keys:",
                data.keys()
            )


            jobs = data.get(
                "data",
                []
            )


            print(
                "TheirStack jobs returned:",
                len(jobs)
            )



        metadata = data.get(
                "metadata",
    {}
            )


        print(
                "TheirStack total matches:",
                metadata.get(
                "total_results",
                "Not provided"
                )
            )    
        

        return data


    except (
        requests.RequestException,
        ValueError
    ) as error:

        print(
            "TheirStack API Error:",
            error
        )


        if response is not None:

            print(
                "TheirStack response:",
                response.text[:1000]
            )


        return {}



def get_theirstack_jobs(
    job_title,
    location,
    days,
    source_name,
    source_domain,
    limit=1
):
    """
    Get TheirStack jobs and convert
    them into our standard format.

    Only one API job-search request
    is made. No broader fallback
    request is performed.
    """


    # ======================================
    # SEARCH THEIRSTACK
    # ======================================

    print(
        f"Searching {source_name}..."
    )


    data = get_theirstack_raw_jobs(
        job_title=job_title,
        location=location,
        source_domain=source_domain,
        days=days,
        limit=limit
    )


    # ======================================
    # EXTRACT RAW JOBS
    # ======================================

    raw_jobs = data.get(
        "data",
        []
    )


    if not isinstance(
        raw_jobs,
        list
    ):

        raw_jobs = []


    print(
        f"{source_name} API jobs:",
        len(raw_jobs)
    )


    # ======================================
    # FORMAT RESULTS
    # ======================================

    clean_jobs = []


    for job in raw_jobs:

        formatted_job = (
            format_theirstack_job(
                job,
                source_name
            )
        )


        clean_jobs.append(
            formatted_job
        )


    print(
        f"{source_name} jobs found:",
        len(clean_jobs)
    )


    return clean_jobs

#============================End of TheirStack Functions============================



#------------------------------------------
# Python Functions (Filter and Search)
#------------------------------------------


def filter_recent_jobs(jobs, days=3):
    """Keep only jobs posted within the selected number of days."""

    recent_jobs = []

    # Calculate the earliest allowed posting time
    cutoff_date = (
        datetime.now(timezone.utc)
        - timedelta(days=days)
    )

    for job in jobs:

        created_at = job.get(
            "Posted",
            ""
        )

        try:

            # Arbeitnow currently returns created_at
            # as a Unix timestamp.
            if isinstance(
                created_at,
                (int, float)
            ):

                job_date = datetime.fromtimestamp(
                    created_at,
                    tz=timezone.utc
                )

            else:

                # Also support ISO date strings
                job_date = datetime.fromisoformat(
                    str(created_at).replace(
                        "Z",
                        "+00:00"
                    )
                )

                if job_date.tzinfo is None:

                    job_date = job_date.replace(
                        tzinfo=timezone.utc
                    )

            # Keep recent jobs
            if job_date >= cutoff_date:

                recent_jobs.append(
                    job
                )

        except (
            ValueError,
            AttributeError,
            TypeError,
            OSError
        ):

            # Ignore invalid dates
            continue

    print(
        f"Jobs after date filter: {len(recent_jobs)}"
    )

    return recent_jobs

#------------------------------------------
# Removing duplicates and searching jobs
#-----------------------------------------

def remove_duplicate_jobs(jobs):
    """
    Remove duplicate jobs based on
    title, company, and location.
    """

    unique_jobs = []

    seen_jobs = set()


    for job in jobs:

        if not isinstance(
            job,
            dict
        ):

            print(
                "Skipping invalid job:",
                job
            )

            continue


        title = str(
            job.get(
                "Title",
                ""
            )
        ).lower().strip()

        company = str(
            job.get(
                "Company",
                ""
            )
        ).lower().strip()


        location = str(
            job.get(
                "Location",
                ""
            )
        ).lower().strip()


        job_key = (
            title,
            company,
            location
        )


        if job_key not in seen_jobs:

            seen_jobs.add(
                job_key
            )

            unique_jobs.append(
                job
            )


    print(
        "Jobs after duplicate removal:",
        len(unique_jobs)
    )


    return unique_jobs

#------------------------------------------
# Sorting job results
#------------------------------------------

def sort_jobs(
    jobs,
    sort_option
):
    """
    Sort job results using the
    selected sorting option.
    """


    # =====================================
    # SORT BY POSTED DATE
    # =====================================

    if sort_option in [
        "Newest first",
        "Oldest first"
    ]:

        jobs_with_dates = []

        jobs_without_dates = []


        for job in jobs:

            posted = str(
                job.get(
                    "Posted",
                    ""
                )
            ).strip()


            try:

                datetime.strptime(
                    posted,
                    "%Y-%m-%d"
                )

                jobs_with_dates.append(
                    job
                )


            except (
                ValueError,
                TypeError
            ):

                jobs_without_dates.append(
                    job
                )


        # ---------------------------------
        # NEWEST FIRST
        # ---------------------------------

        if sort_option == "Newest first":

            jobs_with_dates.sort(
                key=lambda job: datetime.strptime(
                    str(
                        job.get(
                            "Posted",
                            ""
                        )
                    ).strip(),
                    "%Y-%m-%d"
                ),
                reverse=True
            )


        # ---------------------------------
        # OLDEST FIRST
        # ---------------------------------

        else:

            jobs_with_dates.sort(
                key=lambda job: datetime.strptime(
                    str(
                        job.get(
                            "Posted",
                            ""
                        )
                    ).strip(),
                    "%Y-%m-%d"
                )
            )


        sorted_jobs = (
            jobs_with_dates
            +
            jobs_without_dates
        )


    # =====================================
    # SORT BY COMPANY
    # =====================================

    elif sort_option == "Company A-Z":

        sorted_jobs = sorted(
            jobs,
            key=lambda job: str(
                job.get(
                    "Company",
                    ""
                )
            ).lower()
        )


    # =====================================
    # SORT BY JOB TITLE
    # =====================================

    elif sort_option == "Job title A-Z":

        sorted_jobs = sorted(
            jobs,
            key=lambda job: str(
                job.get(
                    "Title",
                    ""
                )
            ).lower()
        )


    # =====================================
    # FALLBACK
    # =====================================

    else:

        sorted_jobs = jobs


    return sorted_jobs

#------------------------------------------
# Searching jobs from both sources
#------------------------------------------


def search_jobs(
    job_title,
    location,
    days=3,
    selected_sources=None,
    remote_filter="All jobs",
    sort_option="Newest first"
):
    """
    Search selected job sources
    and return combined results.
    """


    # =====================================
    # DEFAULT SOURCES
    # =====================================

    if selected_sources is None:

        selected_sources = [
            "Arbeitnow",
            "Bundesagentur"
        ]


    # =====================================
    # CREATE EMPTY RESULT LISTS
    # =====================================

    filtered_arbeitnow_jobs = []

    bundesagentur_jobs = []

    linkedin_jobs = []

    indeed_jobs = []

    # =====================================
    # ARBEITNOW
    # =====================================

    if "Arbeitnow" in selected_sources:

        print(
            "Searching Arbeitnow..."
        )


        # ---------------------------------
        # GET ARBEITNOW JOBS
        # ---------------------------------

        arbeitnow_jobs = (
            get_clean_jobs()
        )


        print(
            "Arbeitnow jobs received:",
            len(arbeitnow_jobs)
        )


        # ---------------------------------
        # FILTER BY DATE
        # ---------------------------------

        if days == "All time":

            recent_arbeitnow_jobs = (
                arbeitnow_jobs
            )

        else:

            recent_arbeitnow_jobs = (
                filter_recent_jobs(
                    arbeitnow_jobs,
                    days
                )
            )


        print(
            "Recent Arbeitnow jobs:",
            len(recent_arbeitnow_jobs)
        )


        # ---------------------------------
        # CLEAN USER SEARCH
        # ---------------------------------

        job_title_clean = (
            job_title
            .lower()
            .strip()
        )


        location_clean = (
            location
            .lower()
            .strip()
        )


        # ---------------------------------
        # SEARCH ARBEITNOW RESULTS
        # ---------------------------------

        for job in recent_arbeitnow_jobs:

            title = str(
                job.get(
                    "Title",
                    ""
                )
            ).lower()


            job_location = str(
                job.get(
                    "Location",
                    ""
                )
            ).lower()


            title_match = (
                job_title_clean
                in
                title
            )


            location_match = (
                location_clean
                in
                job_location
            )


            if (
                title_match
                and
                location_match
            ):

                filtered_arbeitnow_jobs.append(
                    job
                )


        print(
            "Matching Arbeitnow jobs:",
            len(
                filtered_arbeitnow_jobs
            )
        )


    else:

        print(
            "Arbeitnow not selected."
        )


    # =====================================
    # BUNDESAGENTUR
    # =====================================

    if "Bundesagentur" in selected_sources:

        print(
            "Searching Bundesagentur..."
        )


        bundesagentur_jobs = (
            get_bundesagentur_jobs(
                job_title,
                location,
                days
            )
        )


        print(
            "Bundesagentur jobs received:",
            len(
                bundesagentur_jobs
            )
        )


    else:

        print(
            "Bundesagentur not selected."
        )


    # =====================================
    # LINKEDIN
    # =====================================

    if "LinkedIn" in selected_sources:

        print(
            "Searching LinkedIn..."
        )


        linkedin_jobs = (
            get_theirstack_jobs(
                job_title=job_title,
                location=location,
                days=days,
                source_name="LinkedIn",
                source_domain="linkedin.com",
                limit=1
            )
        )


        print(
            "LinkedIn jobs received:",
            len(linkedin_jobs)
        )


    else:

        print(
            "LinkedIn not selected."
        )


    # =====================================
    # INDEED
    # =====================================

    if "Indeed" in selected_sources:

        print(
            "Searching Indeed..."
        )


        indeed_jobs = (
            get_theirstack_jobs(
                job_title=job_title,
                location=location,
                days=days,
                source_name="Indeed",
                source_domain="indeed.com",
                limit=1
            )
        )


        print(
            "Indeed jobs received:",
            len(indeed_jobs)
        )


    else:

        print(
            "Indeed not selected."
        )


    # =====================================
    # COMBINE SELECTED SOURCES
    # =====================================

    all_jobs = (
        filtered_arbeitnow_jobs
        + bundesagentur_jobs
        + linkedin_jobs
        + indeed_jobs
    )

    print(
        "Total combined jobs:",
        len(all_jobs)
    )


    # =====================================
    # REMOVE DUPLICATES
    # =====================================

    unique_jobs = remove_duplicate_jobs(all_jobs)


    # =====================================
    # FILTER BY REMOTE STATUS
    # =====================================

    final_jobs = unique_jobs

    if remote_filter == "Remote only":

        final_jobs = [
            job
            for job in unique_jobs
            if job.get(
                "Remote",
                False
            ) is True
        ]


    elif remote_filter == "Non-remote only":

        final_jobs = [
            job
            for job in unique_jobs
            if job.get(
                "Remote",
                False
            ) is False
        ]


    print(
        "Jobs after remote filter:",
        len(final_jobs)
    )


    # =====================================
    # SORT FINAL RESULTS
    # =====================================

    sorted_jobs = sort_jobs(
        final_jobs,
        sort_option
    )


    print(
        "Jobs after sorting:",
        len(sorted_jobs)
    )


    print(
        "Sorting method:",
        sort_option
    )


    # =====================================
    # RETURN FINAL RESULTS
    # =====================================

    return sorted_jobs
import os
import json
import requests

from dotenv import load_dotenv


# ==========================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================

load_dotenv()


# ==========================================
# OLLAMA CONFIGURATION
# ==========================================

OLLAMA_API_URL = (
    "http://localhost:11434/"
    "api/chat"
)


OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    ""
)


# ==========================================
# TEST OLLAMA CONNECTION
# ==========================================

def test_ollama_connection():
    """
    Test whether the local Ollama API
    and selected model are working.
    """

    if not OLLAMA_MODEL:

        return {
            "success": False,
            "message": (
                "OLLAMA_MODEL is missing "
                "from the .env file."
            )
        }


    payload = {

        "model": OLLAMA_MODEL,

        "messages": [
            {
                "role": "user",
                "content": (
                    "Return JSON only. "
                    '{"status":"connected"}'
                )
            }
        ],

        "format": "json",

        "stream": False
    }


    try:

        response = requests.post(
            OLLAMA_API_URL,
            json=payload,
            timeout=120
        )


        response.raise_for_status()


        data = response.json()


        content = (
            data
            .get(
                "message",
                {}
            )
            .get(
                "content",
                ""
            )
        )


        return {
            "success": True,
            "message": content
        }


    except requests.RequestException as error:

        return {
            "success": False,
            "message": str(error)
        }


# ==========================================
# ANALYZE JOB MATCHES
# ==========================================

def analyze_job_matches(
    candidate_profile,
    jobs,
    max_jobs=5
):
    """
    Ask local Ollama to estimate how
    relevant returned jobs are to the
    candidate profile.

    Because the current APIs do not
    provide full job descriptions in
    our standard job format, this is a
    basic role-fit estimate.
    """


    if not OLLAMA_MODEL:

        return {
            "success": False,
            "error": (
                "OLLAMA_MODEL is missing "
                "from the .env file."
            ),
            "matches": []
        }


    if not candidate_profile.strip():

        return {
            "success": False,
            "error": (
                "Candidate profile is empty."
            ),
            "matches": []
        }


    jobs_for_ai = []


    for index, job in enumerate(
        jobs[:max_jobs]
    ):

        jobs_for_ai.append(
            {
                "index": index,

                "title": job.get(
                    "Title",
                    ""
                ),

                "company": job.get(
                    "Company",
                    ""
                ),

                "location": job.get(
                    "Location",
                    ""
                ),

                "remote": job.get(
                    "Remote",
                    False
                ),

                "source": job.get(
                    "Source",
                    ""
                )
            }
        )


    prompt = f"""
You are helping rank job-search results.

Candidate profile:
{candidate_profile}

Jobs:
{json.dumps(
    jobs_for_ai,
    ensure_ascii=False,
    indent=2
)}

Important:
The job data does NOT contain complete job
descriptions or qualification requirements.

Estimate role relevance using only:
- candidate profile
- job title
- company
- location
- remote status
- source

Do not invent specific requirements.

For each job return:
- index
- score from 0 to 100
- one short reason

The score is only a basic role-fit estimate,
not proof that the candidate qualifies.

Return valid JSON only in this exact shape:

{{
  "matches": [
    {{
      "index": 0,
      "score": 80,
      "reason": "Short explanation"
    }}
  ]
}}
"""


    payload = {

        "model": OLLAMA_MODEL,

        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a careful job "
                    "matching assistant. "
                    "Return valid JSON only."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        "format": "json",

        "stream": False
    }


    try:

        response = requests.post(
            OLLAMA_API_URL,
            json=payload,
            timeout=180
        )


        response.raise_for_status()


        response_data = (
            response.json()
        )


        content = (
            response_data
            .get(
                "message",
                {}
            )
            .get(
                "content",
                "{}"
            )
        )


        result = json.loads(
            content
        )


        matches = result.get(
            "matches",
            []
        )


        clean_matches = []


        for match in matches:

            try:

                index = int(
                    match.get(
                        "index"
                    )
                )


                score = int(
                    match.get(
                        "score",
                        0
                    )
                )


                # Keep score between
                # 0 and 100.
                score = max(
                    0,
                    min(
                        100,
                        score
                    )
                )


                reason = str(
                    match.get(
                        "reason",
                        ""
                    )
                ).strip()


                clean_matches.append(
                    {
                        "index": index,
                        "score": score,
                        "reason": reason
                    }
                )


            except (
                TypeError,
                ValueError
            ):

                continue


        return {
            "success": True,
            "matches": clean_matches
        }


    except requests.RequestException as error:

        return {
            "success": False,
            "error": str(error),
            "matches": []
        }


    except json.JSONDecodeError:

        return {
            "success": False,
            "error": (
                "Ollama returned invalid JSON."
            ),
            "matches": []
        }
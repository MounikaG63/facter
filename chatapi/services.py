# import requests

# SAFE_API_URL = "https://dev.fact-ops.in/fact-ops/safe/get_director_details"

# def fetch_director_documents(
#     org_id: str,
#     dir_id: str,
#     user_id: str,
#     access_token: str
# ) -> dict:

#     headers = {
#         "Authorization": f"Bearer {access_token}",
#         "Content-Type": "application/json"
#     }

#     payload = {
#         "org_id": org_id,
#         "dir_id": dir_id,
#         "user_id": user_id
#     }

#     try:
#         response = requests.post(
#             SAFE_API_URL,
#             headers=headers,
#             json=payload,
#             timeout=10
#         )
#         response.raise_for_status()
#         data = response.json()
#     except requests.RequestException as e:
#         raise Exception(f"SAFE API request failed: {str(e)}")

#     try:
#         return data["data"][0]["documents"]
#     except (KeyError, IndexError, TypeError):
#         raise Exception("Invalid SAFE API response structure")
import requests
from django.conf import settings

SAFE_API_URL = f"{settings.BASE_URL}/fact-ops/safe/get_director_details"

def fetch_director_documents(request, org_id: str, dir_id: str) -> dict:
    """
    Internal API call.
    Auth is forwarded; identity is resolved by middleware.
    """

    headers = {
        "Content-Type": "application/json",
    }

    # Forward Authorization header (mobile)
    auth_header = request.headers.get("Authorization")
    if auth_header:
        headers["Authorization"] = auth_header

    payload = {
        "org_id": org_id,
        "dir_id": dir_id,
    }

    try:
        response = requests.post(
            SAFE_API_URL,
            headers=headers,
            cookies=request.COOKIES,   # forward JWT cookies (web)
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        # Parse error response for user-friendly messages
        error_text = getattr(e.response, 'text', None)
        if error_text:
            try:
                error_data = json.loads(error_text)
                error_msg = error_data.get("message", "")
                if "not in org" in error_msg.lower():
                    raise Exception("NOT_IN_ORG")
            except json.JSONDecodeError:
                pass
        raise Exception(
            f"SAFE API request failed: {e}, "
            f"response={error_text}"
        )

    # Check if user doesn't have access
    if data.get("message") == "OTP required":
        raise Exception("NO_ACCESS")

    try:
        return data["data"][0]["documents"]
    except (KeyError, IndexError, TypeError):
        raise Exception("Invalid SAFE API response structure")
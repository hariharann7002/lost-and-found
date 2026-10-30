import json

from auth import (
    login,
    create_user
)

from objects import (
    create_object,
    get_object,
    list_objects
)

from claims import (
    create_claim,
    get_object_claims,
    select_successful_claim,
    get_my_claims
)

from admin import (
    get_dashboard,
    get_all_objects_for_admin
)

from s3_utils import generate_upload_url, generate_download_url
from response import response


def lambda_handler(event, context):

    try:

        # API Gateway sends body as JSON string
        body = event.get("body")

        if isinstance(body, str):

            body = json.loads(body)

        elif body is None:

            body = {}

        # Put body fields directly into event
        event.update(body)

        action = event.get("action")

        # -------------------------
        # AUTH
        # -------------------------

        if action == "LOGIN":

            return login(event)

        elif action == "CREATE_USER":

            return create_user(event)

        # -------------------------
        # S3
        # -------------------------

        elif action == "GET_UPLOAD_URL":

            return generate_upload_url(event)

        # -------------------------
        # OBJECTS
        # -------------------------

        elif action == "CREATE_OBJECT":

            return create_object(event)

        elif action == "GET_OBJECT":

            return get_object(event)

        elif action == "LIST_OBJECTS":

            return list_objects(event)

        # -------------------------
        # CLAIMS
        # -------------------------

        elif action == "CLAIM_OBJECT":

            return create_claim(event)

        elif action == "GET_CLAIMS":

            return get_object_claims(event)

        elif action == "SELECT_SUCCESSFUL_CLAIM":

            return select_successful_claim(event)
        
        elif action == "GET_MY_CLAIMS":
            return get_my_claims(event)

        # -------------------------
        # ADMIN
        # -------------------------

        elif action == "GET_DASHBOARD":

            return get_dashboard(event)

        elif action == "GET_ALL_OBJECTS":

            return get_all_objects_for_admin(event)

        # -------------------------
        # UNKNOWN
        # -------------------------

        else:

            return response(
                400,
                {
                    "message":
                        f"Unknown action: {action}"
                }
            )

    except Exception as e:

        print(
            f"Lambda error: {str(e)}"
        )

        return response(
            500,
            {
                "message":
                    "Internal server error"
            }
        )
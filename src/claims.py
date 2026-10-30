from datetime import datetime, timezone

from db import lost_found_table,users_table
from response import response
from s3_utils import generate_download_url


def create_claim(event):
    object_id = event["object_id"]
    user_id = event["user_id"]

    # Check that the object exists
    object_result = lost_found_table.get_item(
        Key={
            "PK": f"OBJECT#{object_id}",
            "SK": "OBJECT"
        }
    )

    object_item = object_result.get("Item")

    if object_item is None:
        return response(
            404,
            {
                "message": "Object not found"
            }
        )

    # Check object status
    if object_item.get("status") != "OPEN":
        return response(
            400,
            {
                "message": "This object is no longer available for claims"
            }
        )

    # Check whether this user has already claimed the object
    existing_claim = lost_found_table.get_item(
        Key={
            "PK": f"OBJECT#{object_id}",
            "SK": f"CLAIM#{user_id}"
        }
    )

    if existing_claim.get("Item"):
        return response(
            400,
            {
                "message": "You have already claimed this object"
            }
        )

    now = datetime.now(timezone.utc).isoformat()

    claim_item = {
        "PK": f"OBJECT#{object_id}",
        "SK": f"CLAIM#{user_id}",
        "entity_type": "CLAIM",
        "object_id": object_id,
        "user_id": user_id,
        "status": "PENDING",
        "created_at": now
    }

    lost_found_table.put_item(
        Item=claim_item
    )

    return response(
        201,
        {
            "message": "Claim submitted successfully",
            "object_id": object_id,
            "status": "PENDING"
        }
    )


def get_object_claims(event):
    object_id = event["object_id"]

    # Get all items belonging to this object
    result = lost_found_table.query(
        KeyConditionExpression="PK = :pk",
        ExpressionAttributeValues={
            ":pk": f"OBJECT#{object_id}"
        }
    )

    items = result.get("Items", [])

    claims = [
        item
        for item in items
        if item.get("entity_type") == "CLAIM"
    ]

    # Get users and create user_id -> user_name mapping
    users_result = users_table.scan()
    users = users_result.get("Items", [])

    user_names = {
        user.get("user_id"): user.get("user_name")
        for user in users
    }

    readable_claims = []

    for claim in claims:
        user_id = claim.get("user_id")

        readable_claims.append({
            "user_id": user_id,
            "user_name": user_names.get(
                user_id,
                "Unknown User"
            ),
            "status": claim.get("status"),
            "created_at": claim.get("created_at")
        })

    # Newest claims first
    readable_claims.sort(
        key=lambda x: x.get("created_at", ""),
        reverse=True
    )

    return response(
        200,
        {
            "object_id": object_id,
            "claims": readable_claims
        }
    )


def select_successful_claim(event):
    object_id = event["object_id"]
    selected_user_id = event["selected_user_id"]

    # Get all claims for this object
    result = lost_found_table.query(
        KeyConditionExpression="PK = :pk",
        ExpressionAttributeValues={
            ":pk": f"OBJECT#{object_id}"
        }
    )

    items = result.get("Items", [])

    claims = [
        item
        for item in items
        if item.get("entity_type") == "CLAIM"
    ]

    if not claims:
        return response(
            404,
            {
                "message": "No claims found for this object"
            }
        )

    # Check that selected user actually claimed the object
    selected_claim = next(
        (
            claim
            for claim in claims
            if claim.get("user_id") == selected_user_id
        ),
        None
    )

    if selected_claim is None:
        return response(
            404,
            {
                "message": "Selected user has not claimed this object"
            }
        )

    # Approve selected claim and reject all others
    for claim in claims:

        claim_user_id = claim.get("user_id")

        new_status = (
            "APPROVED"
            if claim_user_id == selected_user_id
            else "REJECTED"
        )

        lost_found_table.update_item(
            Key={
                "PK": f"OBJECT#{object_id}",
                "SK": f"CLAIM#{claim_user_id}"
            },
            UpdateExpression="SET #status = :status",
            ExpressionAttributeNames={
                "#status": "status"
            },
            ExpressionAttributeValues={
                ":status": new_status
            }
        )

    # Mark object as returned and store successful claimant
    lost_found_table.update_item(
        Key={
            "PK": f"OBJECT#{object_id}",
            "SK": "OBJECT"
        },
        UpdateExpression="SET #status = :status, successful_claim = :user_id",
        ExpressionAttributeNames={
            "#status": "status"
        },
        ExpressionAttributeValues={
            ":status": "RETURNED",
            ":user_id": selected_user_id
        }
    )

    return response(
        200,
        {
            "message": "Successful claim selected",
            "object_id": object_id,
            "successful_claim": selected_user_id
        }
    )


def get_my_claims(event):
    user_id = event["user_id"]

    # Find all claims made by this user
    result = lost_found_table.scan()
    items = result.get("Items", [])

    my_claims = [
        item
        for item in items
        if item.get("entity_type") == "CLAIM"
        and item.get("user_id") == user_id
    ]

    claims = []

    for claim in my_claims:
        object_id = claim.get("object_id")

        # Get the corresponding object
        object_result = lost_found_table.get_item(
            Key={
                "PK": f"OBJECT#{object_id}",
                "SK": "OBJECT"
            }
        )

        object_item = object_result.get("Item")

        if object_item is None:
            continue

        claim_data = {
            "object_id": object_id,
            "object_name": object_item.get("object_name"),
            "object_description": object_item.get("object_description"),
            "claim_status": claim.get("status"),
            "created_at": claim.get("created_at")
        }

        # Generate temporary presigned GET URL
        s3_key = object_item.get("s3_uri")

        if s3_key:
            claim_data["image_url"] = generate_download_url(s3_key)

        claims.append(claim_data)

    # Newest claims first
    claims.sort(
        key=lambda x: x.get("created_at", ""),
        reverse=True
    )

    return response(
        200,
        {
            "claims": claims
        }
    )
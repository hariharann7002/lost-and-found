from collections import defaultdict

from db import lost_found_table, users_table
from response import response


def get_dashboard(event):
    result = lost_found_table.scan()
    items = result.get("Items", [])

    objects = [
        item
        for item in items
        if item.get("entity_type") == "OBJECT"
    ]

    claims = [
        item
        for item in items
        if item.get("entity_type") == "CLAIM"
    ]

    # -------------------------
    # Basic counts
    # -------------------------

    total_objects = len(objects)
    total_claims = len(claims)

    successfully_returned = len([
        obj
        for obj in objects
        if obj.get("status") == "RETURNED"
    ])

    # -------------------------
    # Claim status
    # -------------------------

    pending_claims = len([
        claim
        for claim in claims
        if claim.get("status") == "PENDING"
    ])

    approved_claims = len([
        claim
        for claim in claims
        if claim.get("status") == "APPROVED"
    ])

    rejected_claims = len([
        claim
        for claim in claims
        if claim.get("status") == "REJECTED"
    ])

    # -------------------------
    # Object status
    # -------------------------

    open_objects = len([
        obj
        for obj in objects
        if obj.get("status") == "OPEN"
    ])

    returned_objects = len([
        obj
        for obj in objects
        if obj.get("status") == "RETURNED"
    ])

    # -------------------------
    # Activity over time
    # -------------------------

    activity = defaultdict(
        lambda: {
            "objects": 0,
            "claims": 0
        }
    )

    for obj in objects:
        created_at = obj.get("created_at")

        if created_at:
            date = created_at[:10]
            activity[date]["objects"] += 1

    for claim in claims:
        created_at = claim.get("created_at")

        if created_at:
            date = created_at[:10]
            activity[date]["claims"] += 1

    activity_data = [
        {
            "date": date,
            "objects": values["objects"],
            "claims": values["claims"]
        }
        for date, values in sorted(activity.items())
    ]

    # -------------------------
    # Response
    # -------------------------

    return response(
        200,
        {
            "total_objects": total_objects,
            "total_claims": total_claims,
            "successfully_returned": successfully_returned,

            "claim_status": {
                "pending": pending_claims,
                "approved": approved_claims,
                "rejected": rejected_claims
            },

            "object_status": {
                "open": open_objects,
                "returned": returned_objects
            },

            "activity": activity_data
        }
    )


def get_all_objects_for_admin(event):
    result = lost_found_table.scan()
    items = result.get("Items", [])

    objects = [
        item
        for item in items
        if item.get("entity_type") == "OBJECT"
    ]

    # Get all users and create a user_id -> user_name mapping
    users_result = users_table.scan()
    users = users_result.get("Items", [])

    user_names = {
        user.get("user_id"): user.get("user_name")
        for user in users
    }

    # Convert internal user IDs to readable usernames
    for obj in objects:

        found_by_id = obj.get("found_by")

        if found_by_id:
            obj["found_by"] = user_names.get(
                found_by_id,
                found_by_id
            )

        successful_claim_id = obj.get("successful_claim")

        if successful_claim_id:
            obj["successful_claim"] = user_names.get(
                successful_claim_id,
                successful_claim_id
            )

        # Remove internal DynamoDB/S3 fields from API response
        obj.pop("PK", None)
        obj.pop("SK", None)
        obj.pop("s3_uri", None)

    objects.sort(
        key=lambda x: x.get("created_at", ""),
        reverse=True
    )

    return response(
        200,
        {
            "objects": objects
        }
    )
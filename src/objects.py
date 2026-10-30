from datetime import datetime, timezone

from db import lost_found_table,users_table
from response import response
from s3_utils import generate_download_url


def create_object(event):
    object_id = event["object_id"]
    now = datetime.now(timezone.utc).isoformat()

    item = {
        "PK": f"OBJECT#{object_id}",
        "SK": "OBJECT",
        "entity_type": "OBJECT",
        "object_id": object_id,
        "object_name": event["object_name"],
        "object_description": event["object_description"],
        "s3_uri": event["s3_uri"],
        "found_by": event["user_id"],
        "successful_claim": None,
        "status": "OPEN",
        "created_at": now
    }

    lost_found_table.put_item(Item=item)

    return response(
        201,
        {
            "message": "Object created successfully",
            "object_id": object_id
        }
    )


def get_object(event):
    object_id = event["object_id"]
    user_id = event.get("user_id")

    result = lost_found_table.get_item(
        Key={
            "PK": f"OBJECT#{object_id}",
            "SK": "OBJECT"
        }
    )

    item = result.get("Item")

    if item is None:
        return response(
            404,
            {
                "message": "Object not found"
            }
        )

    # Convert found_by user ID to username
    found_by_id = item.get("found_by")

    if found_by_id:
        user_result = users_table.get_item(
            Key={
                "user_id": found_by_id
            }
        )

        user = user_result.get("Item")

        if user:
            item["found_by"] = user.get("user_name")

    # Generate temporary presigned GET URL
    s3_key = item.get("s3_uri")

    if s3_key:
        item["image_url"] = generate_download_url(s3_key)

    # Do not expose internal S3 key
    item.pop("s3_uri", None)

    # Get this user's claim status for this object
    item["claim_status"] = None

    if user_id:
        claim_result = lost_found_table.get_item(
            Key={
                "PK": f"OBJECT#{object_id}",
                "SK": f"CLAIM#{user_id}"
            }
        )

        claim = claim_result.get("Item")

        if claim:
            item["claim_status"] = claim.get("status")

    return response(
        200,
        item
    )

def list_objects(event):
    result = lost_found_table.scan()

    items = result.get("Items", [])

    objects = [
        item
        for item in items
        if item.get("entity_type") == "OBJECT"
    ]

    objects.sort(
        key=lambda x: x.get("created_at", ""),
        reverse=True
    )

    page = int(event.get("page", 1))
    page_size = int(event.get("page_size", 10))

    start = (page - 1) * page_size
    end = start + page_size

    paginated_objects = objects[start:end]

    for item in paginated_objects:
        s3_key = item.get("s3_uri")

        if s3_key:
            item["image_url"] = generate_download_url(s3_key)

        item.pop("s3_uri", None)

    total = len(objects)
    total_pages = (total + page_size - 1) // page_size

    return response(
        200,
        {
            "objects": paginated_objects,
            "page": page,
            "page_size": page_size,
            "total_objects": total,
            "total_pages": total_pages
        }
    )
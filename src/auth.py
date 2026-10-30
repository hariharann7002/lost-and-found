import hashlib
import hmac
import os
import uuid
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key

from db import users_table
from response import response


ITERATIONS = 310000


def hash_password(password):

    salt = os.urandom(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        ITERATIONS
    )

    return (
        f"{ITERATIONS}$"
        f"{salt.hex()}$"
        f"{password_hash.hex()}"
    )


def verify_password(password, stored_hash):

    try:

        iterations, salt_hex, hash_hex = stored_hash.split("$")

        salt = bytes.fromhex(salt_hex)

        expected_hash = bytes.fromhex(hash_hex)

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations)
        )

        return hmac.compare_digest(
            actual_hash,
            expected_hash
        )

    except Exception:

        return False


def get_user(user_id):

    result = users_table.get_item(
        Key={
            "user_id": user_id
        }
    )

    return result.get("Item")


def create_user(event):

    username = event["user_name"]
    password = event["password"]
    role = event.get("role", "USER")

    # For your demo, prevent duplicate usernames
    scan_result = users_table.scan(
        ProjectionExpression="user_id, user_name"
    )

    for user in scan_result.get("Items", []):

        if user.get("user_name") == username:

            return response(
                409,
                {
                    "message": "Username already exists"
                }
            )

    user_id = str(uuid.uuid4())

    now = datetime.now(
        timezone.utc
    ).isoformat()

    item = {
        "user_id": user_id,
        "user_name": username,
        "password_hash": hash_password(password),
        "role": role,
        "created_at": now
    }

    users_table.put_item(
        Item=item
    )

    return response(
        201,
        {
            "user_id": user_id,
            "user_name": username,
            "role": role
        }
    )


def login(event):

    username = event["user_name"]
    password = event["password"]

    # Only 3-4 users, so scanning is fine for your demo
    result = users_table.scan()

    users = result.get("Items", [])

    user = None

    for candidate in users:

        if candidate.get("user_name") == username:

            user = candidate
            break

    if user is None:

        return response(
            401,
            {
                "message": "Invalid username or password"
            }
        )

    if not verify_password(
        password,
        user["password_hash"]
    ):

        return response(
            401,
            {
                "message": "Invalid username or password"
            }
        )

    return response(
        200,
        {
            "user_id": user["user_id"],
            "user_name": user["user_name"],
            "role": user["role"]
        }
    )


def require_admin(user_id):

    user = get_user(user_id)

    if user is None:

        return False

    return user.get("role") == "ADMIN"
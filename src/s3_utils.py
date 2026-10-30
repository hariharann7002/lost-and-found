import os
import uuid
import boto3

from response import response

s3 = boto3.client("s3")
BUCKET = os.environ["S3_BUCKET"]


def generate_upload_url(event):
    object_id = str(uuid.uuid4())

    extension = event.get("extension", "jpg")
    key = f"objects/{object_id}.{extension}"

    upload_url = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": BUCKET,
            "Key": key,
            "ContentType": event.get("content_type", "image/jpeg")
        },
        ExpiresIn=300
    )

    return response(
        200,
        {
            "object_id": object_id,
            "s3_key": key,
            "upload_url": upload_url
        }
    )


def generate_download_url(s3_key):
    return s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": BUCKET,
            "Key": s3_key
        },
        ExpiresIn=300
    )
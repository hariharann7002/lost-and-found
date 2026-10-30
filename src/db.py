import boto3
import os


dynamodb = boto3.resource("dynamodb")

USERS_TABLE_NAME = os.environ["USERS_TABLE"]
LOST_FOUND_TABLE_NAME = os.environ["LOST_FOUND_TABLE"]

users_table = dynamodb.Table(USERS_TABLE_NAME)
lost_found_table = dynamodb.Table(LOST_FOUND_TABLE_NAME)
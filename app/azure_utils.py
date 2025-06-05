import os
from azure.storage.blob import BlobServiceClient, ContainerClient, BlobClient, generate_blob_sas, BlobSasPermissions
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

load_dotenv()
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_STORAGE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")

blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)

def get_or_create_container(user_id: str):
    container_name = f"user-{user_id.lower()}"
    container_client = blob_service_client.get_container_client(container_name)
    try:
        container_client.get_container_properties()
    except Exception:
        container_client = blob_service_client.create_container(container_name)
    return container_client

def upload_image(user_id: str, filename: str, content: bytes):
    container_client = get_or_create_container(user_id)
    blob_path = f"images/{filename}"  # Save under images/ folder
    blob_client = container_client.get_blob_client(blob_path)
    blob_client.upload_blob(content, overwrite=True)


def delete_image(user_id: str, filename: str):
    container_client = get_or_create_container(user_id)
    blob_path = f"images/{filename}"
    blob_client = container_client.get_blob_client(blob_path)
    blob_client.delete_blob()


def list_images(user_id: str):
    container_client = get_or_create_container(user_id)
    prefix = "images/"
    return [
        blob.name[len(prefix):] for blob in container_client.list_blobs(name_starts_with=prefix)
    ]

def get_image_sas_url(user_id: str, filename: str, expiry_minutes: int = 30) -> str:
    container_name = f"user-{user_id.lower()}"
    blob_path = f"images/{filename}"
    sas_token = generate_blob_sas(
        account_name=AZURE_STORAGE_ACCOUNT_NAME,
        container_name=container_name,
        blob_name=blob_path,
        account_key=AZURE_STORAGE_ACCOUNT_KEY,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
    )
    return f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{container_name}/{blob_path}?{sas_token}"
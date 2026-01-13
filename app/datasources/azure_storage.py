from azure.identity import ClientSecretCredential
from azure.storage.blob import BlobServiceClient

from app.core.config import settings

credential = ClientSecretCredential(
    tenant_id=settings.AZURE_TENANT_ID,
    client_id=settings.AZURE_CLIENT_ID,
    client_secret=settings.AZURE_CLIENT_SECRET,
)


# Construct the blob service client
blob_service_client = BlobServiceClient(
    f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
    credential=credential,
)

container_client = blob_service_client.get_container_client(settings.AZURE_CONTAINER_NAME)

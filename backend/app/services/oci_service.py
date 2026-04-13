
import os
import uuid
from datetime import datetime, timezone, timedelta

import oci


OCI_REGION = os.getenv("OCI_REGION", "us-sanjose-1")
OCI_BUCKET_NAME = os.getenv("OCI_BUCKET_NAME")
OCI_NAMESPACE = os.getenv("OCI_NAMESPACE")  # optional; auto-fetched if empty
OCI_OBJECT_PREFIX = os.getenv("OCI_OBJECT_PREFIX", "scans")

OCI_USE_INSTANCE_PRINCIPAL = os.getenv("OCI_USE_INSTANCE_PRINCIPAL", "false").lower() == "true"

OCI_CONFIG_FILE = os.getenv("OCI_CONFIG_FILE", os.path.expanduser("~/.oci/config"))
OCI_CONFIG_PROFILE = os.getenv("OCI_CONFIG_PROFILE", "DEFAULT")

def build_read_url(object_name: str, ttl_minutes: int = 15) -> str:
    if not OCI_BUCKET_NAME:
        raise RuntimeError("Missing OCI_BUCKET_NAME env var")
    if not object_name:
        raise ValueError("object_name is required")

    client = _get_object_storage_client()
    namespace = _get_namespace(client)

    details = oci.object_storage.models.CreatePreauthenticatedRequestDetails(
        name=f"scan-read-{uuid.uuid4().hex[:8]}",
        access_type="ObjectRead",
        object_name=object_name,
        time_expires=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
    )

    par = client.create_preauthenticated_request(
        namespace_name=namespace,
        bucket_name=OCI_BUCKET_NAME,
        create_preauthenticated_request_details=details,
    )

    return f"https://objectstorage.{OCI_REGION}.oraclecloud.com{par.data.access_uri}"

def _build_object_name(filename: str) -> str:
    safe_name = os.path.basename(filename or "upload.jpg")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    uid = uuid.uuid4().hex[:12]
    return f"{OCI_OBJECT_PREFIX}/{ts}-{uid}-{safe_name}"


def _get_object_storage_client():
    if OCI_USE_INSTANCE_PRINCIPAL:
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        return oci.object_storage.ObjectStorageClient(
            config={"region": OCI_REGION},
            signer=signer,
        )

    config = oci.config.from_file(OCI_CONFIG_FILE, OCI_CONFIG_PROFILE)
    return oci.object_storage.ObjectStorageClient(config)


def _get_namespace(client) -> str:
    if OCI_NAMESPACE:
        return OCI_NAMESPACE
    return client.get_namespace().data


def upload_to_oci(image_bytes: bytes, filename: str) -> tuple[str, str]:
    if not OCI_BUCKET_NAME:
        raise RuntimeError("Missing OCI_BUCKET_NAME env var")

    client = _get_object_storage_client()
    namespace = _get_namespace(client)
    object_name = _build_object_name(filename)

    client.put_object(
        namespace_name=namespace,
        bucket_name=OCI_BUCKET_NAME,
        object_name=object_name,
        put_object_body=image_bytes,
        content_type="image/jpeg",
    )

    image_url = build_read_url(object_name, ttl_minutes=60)
    return image_url, object_name      


def delete_from_oci(object_name: str) -> None:
    if not OCI_BUCKET_NAME:
        raise RuntimeError("Missing OCI_BUCKET_NAME env var")
    if not object_name:
        raise ValueError("object_name is required")

    client = _get_object_storage_client()
    namespace = _get_namespace(client)

    client.delete_object(
        namespace_name=namespace,
        bucket_name=OCI_BUCKET_NAME,
        object_name=object_name,
    )

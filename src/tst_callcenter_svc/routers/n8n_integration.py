"""
Module: n8n_integration

This module implements the n8n workflow orchestration endpoint which triggers a secure file upload workflow.
The endpoint validates and transforms incoming file upload request payloads, enforces TLS v1.2+, adds HIPAA compliant security headers,
and implements retry logic with exponential backoff for secure outbound HTTPS calls to the n8n webhook.
"""

import os
import uuid
import time
import logging
import ssl

import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime


router = APIRouter()


class N8nTriggerRequest(BaseModel):
    """Pydantic model for validating incoming n8n trigger payloads."""
    file_name: str
    file_size: int
    upload_timestamp: datetime
    metadata: dict = Field(default_factory=dict)


class TLSAdapter(HTTPAdapter):
    """A HTTPAdapter that enforces TLS v1.2 or higher for HTTPS connections."""
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        ctx = ssl.create_default_context()
        # Enforce TLS v1.2 or above
        if hasattr(ssl, "TLSVersion"):
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        else:
            ctx.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx)


@router.post("/trigger")

def trigger_n8n_workflow(payload: N8nTriggerRequest):
    """
    Trigger the n8n workflow upon file upload.

    Transforms the incoming file upload payload by generating a unique file_id and combining file details into the metadata.
    Sends a secure HTTPS POST request to the n8n webhook URL (from N8N_WEBHOOK_URL environment variable) with enforced TLS v1.2+,
    HIPAA compliant security headers, and retry logic with exponential backoff (1s, 2s, 4s) for up to 3 attempts.

    Returns:
        A JSON response with 'success' flag and 'message'.

    Raises:
        HTTPException with status_code 500 if configuration is missing or after retry failures.
    """
    try:
        webhook_url = os.getenv("N8N_WEBHOOK_URL")
        if not webhook_url:
            msg = "N8N_WEBHOOK_URL not set in environment"
            logging.error(msg)
            raise HTTPException(status_code=500, detail="Webhook URL not configured")

        # Construct payload with file_id, upload_timestamp, and file metadata merged into the metadata field
        request_payload = {
            "file_id": str(uuid.uuid4()),
            "upload_timestamp": payload.upload_timestamp.isoformat(),
            "metadata": {"file_name": payload.file_name, "file_size": payload.file_size, **payload.metadata}
        }

        # HIPAA compliant security headers
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'none'"
        }

        session = requests.Session()
        session.mount("https://", TLSAdapter())

        delay = 1
        # Attempt up to 3 times with exponential backoff
        for attempt in range(3):
            try:
                response = session.post(webhook_url, json=request_payload, headers=headers, timeout=5, verify=True)
                if response.status_code == 200:
                    return {"success": True, "message": "Workflow triggered successfully"}
                else:
                    logging.error(f"Attempt {attempt + 1}: Received status code {response.status_code}")
            except Exception as e:
                logging.error(e, exc_info=True)
            if attempt < 2:
                time.sleep(delay)
                delay *= 2

        # If all attempts fail, raise exception
        raise HTTPException(status_code=500, detail="Failed to trigger n8n workflow after retries")
    except Exception as e:
        logging.error(e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

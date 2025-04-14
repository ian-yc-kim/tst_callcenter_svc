import os
import uuid
import time
import logging
import ssl

import requests
from urllib3.poolmanager import PoolManager

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime


router = APIRouter()


class GoogleSupplementaryRequest(BaseModel):
    """Pydantic model to validate incoming Google supplementary processing requests."""
    task_id: str
    additional_data: dict = Field(default_factory=dict)
    timestamp: datetime


class TLSAdapter(requests.adapters.HTTPAdapter):
    """A HTTPAdapter that enforces TLS v1.2 or higher for HTTPS connections."""
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        try:
            ctx = ssl.create_default_context()
            if hasattr(ssl, "TLSVersion"):
                ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            else:
                ctx.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
            self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx)
        except Exception as e:
            logging.error(e, exc_info=True)
            raise


@router.post("/trigger")

def trigger_google_processing(payload: GoogleSupplementaryRequest):
    """
    Endpoint to trigger Google supplementary processing via secure HTTPS call with retry logic.

    Steps:
    1. Retrieve GOOGLE_API_URL from environment and validate its security.
    2. Construct the request payload with a unique request ID, formatted timestamp, and merged additional data.
    3. Set HIPAA-compliant security headers.
    4. Use a requests.Session with TLSAdapter mounted for HTTPS.
    5. Implement exponential backoff retry: 3 attempts with delays 1, 2, and 4 seconds.

    Returns:
        JSON response with success flag if the call returns HTTP 200.

    Raises:
        HTTPException 500 if configuration is missing or all retries fail.
    """
    try:
        google_api_url = os.getenv("GOOGLE_API_URL")
        if not google_api_url or not google_api_url.startswith("https://"):
            msg = "Invalid or insecure GOOGLE_API_URL configuration"
            logging.error(msg)
            raise HTTPException(status_code=500, detail="Google API URL not configured securely")

        # Construct payload with unique request_id and formatted timestamp
        request_payload = {
            "request_id": str(uuid.uuid4()),
            "timestamp": payload.timestamp.isoformat()
        }
        # Merge additional_data into payload
        request_payload.update(payload.additional_data)

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
        for attempt in range(3):
            try:
                response = session.post(google_api_url, json=request_payload, headers=headers, timeout=5, verify=True)
                if response.status_code == 200:
                    return {"success": True, "message": "Google processing triggered successfully"}
                else:
                    logging.error(f"Attempt {attempt + 1}: Received status code {response.status_code}")
            except Exception as e:
                logging.error(e, exc_info=True)
            if attempt < 2:
                time.sleep(delay)
                delay *= 2

        raise HTTPException(status_code=500, detail="Failed to trigger Google processing after retries")
    except Exception as e:
        logging.error(e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

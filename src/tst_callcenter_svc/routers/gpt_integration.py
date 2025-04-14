import os
import time
import logging
import ssl
import requests

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime


router = APIRouter()


class GPTAnalyzeRequest(BaseModel):
    """Pydantic model for validating incoming GPT analysis requests."""
    conversation_id: str
    preprocessed_audio_data: str
    timestamp: datetime


class TLSAdapter(requests.adapters.HTTPAdapter):
    """A HTTPAdapter that enforces TLS v1.2 or higher for HTTPS connections."""
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        ctx = ssl.create_default_context()
        # Enforce TLS v1.2 or above
        if hasattr(ssl, "TLSVersion"):
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        else:
            ctx.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        self.poolmanager = requests.packages.urllib3.poolmanager.PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx, **pool_kwargs
        )


@router.post("/analyze")

def analyze_conversation(request: GPTAnalyzeRequest):
    """
    Endpoint to analyze conversation using GPT API integration.

    This endpoint receives preprocessed audio data and conversation details,
    securely retrieves GPT API credentials, and sends an HTTPS POST request to the GPT API
    with enforced TLS v1.2+, custom headers, and retry logic with exponential backoff.

    Returns:
        JSON response with success flag and analysis result if successful,
        otherwise raises HTTP 500 error after retries.
    """
    try:
        gpt_api_url = os.getenv("GPT_API_URL")
        gpt_api_key = os.getenv("GPT_API_KEY")
        if not gpt_api_url or not gpt_api_url.startswith("https://"):
            msg = "GPT_API_URL not set or insecure. Must use https://"
            logging.error(msg)
            raise HTTPException(status_code=500, detail=msg)
        if not gpt_api_key:
            msg = "GPT_API_KEY not set in environment"
            logging.error(msg)
            raise HTTPException(status_code=500, detail=msg)

        # Setup headers with authorization and HIPAA compliant headers
        headers = {
            "Authorization": f"Bearer {gpt_api_key}",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'none'"
        }

        payload = {
            "conversation_id": request.conversation_id,
            "preprocessed_audio_data": request.preprocessed_audio_data,
            "timestamp": request.timestamp.isoformat()
        }

        session = requests.Session()
        session.mount("https://", TLSAdapter())

        delay = 1
        for attempt in range(3):
            try:
                response = session.post(gpt_api_url, json=payload, headers=headers, timeout=10, verify=True)
                if response.status_code == 200:
                    data = response.json()
                    analysis = data.get('analysis')
                    return {"success": True, "analysis": analysis}
                else:
                    logging.error(f"Attempt {attempt+1}: Received status code {response.status_code} from GPT API")
            except Exception as e:
                logging.error(e, exc_info=True)
            if attempt < 2:
                time.sleep(delay)
                delay *= 2

        raise HTTPException(status_code=500, detail="Failed to analyze conversation after retries")
    except Exception as e:
        logging.error(e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

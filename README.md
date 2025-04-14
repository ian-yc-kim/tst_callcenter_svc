# tst_callcenter_svc

## Updated Documentation for n8n Workflow Integration

### Overview
This section documents the n8n workflow orchestration integration for processing call center recordings. The integration leverages n8n to securely trigger file ingestion workflows, ensuring HIPAA compliance and secure processing of call recordings.

### Purpose
- **Workflow Orchestration:** Leverages n8n to trigger and manage secure file uploads and processing workflows.
- **Security:** Integration enforces TLS v1.2+ for secure HTTPS connections, implements HIPAA-compliant security headers, and follows retry logic with exponential backoff to ensure reliability.

### Environment Variables
- **N8N_WEBHOOK_URL:** The URL for triggering the n8n webhook. This must be set in the environment where the call center service is deployed. Example:
  ```bash
  export N8N_WEBHOOK_URL='https://your-n8n-instance.com/webhook'
  ```

### HTTPS/TLS Configuration
- **TLS Version Requirements:** Only TLS v1.2 or higher is allowed. The integration uses a custom HTTP adapter that sets the minimum TLS version to v1.2 or above (or disables TLS v1.0 and v1.1 when necessary).
- **Certificate Validation:** All HTTPS calls validate certificates to prevent man-in-the-middle attacks. Ensure that your certificates are valid and recognized by your system.
- **Security Headers:** The API call includes the following HIPAA-compliant security headers:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
  - `Content-Security-Policy: default-src 'none'`

### API Endpoint Details
- **Endpoint:** `/api/n8n/trigger`
- **Method:** POST
- **Request Payload:**
  ```json
  {
      "file_name": "recording.wav",
      "file_size": 102400,
      "upload_timestamp": "2023-10-10T10:00:00Z",
      "metadata": {"callerId": "12345"}
  }
  ```
- **Response Format:** On success, returns a JSON object with `"success": true` and a descriptive `"message"`.
- **Error Handling & Retry Logic:**
  - Implements retry logic with exponential backoff (1s, 2s, 4s) for up to 3 attempts in case of connection failures or non-200 responses.
  - If all attempts fail, the endpoint responds with status code 500 and an error message.

### Example Request and Response

- **Example Request:**
  ```json
  {
      "file_name": "recording.wav",
      "file_size": 204800,
      "upload_timestamp": "2023-10-10T10:00:00Z",
      "metadata": {"caller": "+1234567890"}
  }
  ```

- **Example Response (Success):**
  ```json
  {
      "success": true,
      "message": "Workflow triggered successfully"
  }
  ```

### Testing and Verification
- Ensure that the `N8N_WEBHOOK_URL` is correctly set in your deployment environment or during testing.
- Verify the API endpoint behavior by simulating both successful and retry scenarios as outlined in the unit tests (`tests/test_n8n_integration.py`).
- Review and update test cases if necessary to align with any changes in the API payload or logic.

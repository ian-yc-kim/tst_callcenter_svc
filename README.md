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
- **TLS Version Requirements:** Only TLS v1.2 or higher is allowed. The integration uses a custom HTTP adapter that sets the minimum TLS version to v1.2 or above (or disables TLS v1.0 and TLS v1.1 when necessary).
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

### Recorded Conversation Upload and Analysis Feature

#### Overview
This section details the `/api/upload` endpoint which is designed for the secure ingestion and preprocessing of recorded call center conversations. It accepts audio files, ensures rigorous validation, processes audio (e.g., noise reduction), and integrates with the n8n workflow system for subsequent processing.

#### Endpoint Details
- **Endpoint:** `/api/upload`
- **Method:** POST
- **Purpose:** To handle file uploads for recorded conversations. The endpoint validates that the uploaded file is a `.wav` file with an accepted MIME type (`audio/wav` or `audio/x-wav`) and that its size does not exceed 100MB.

#### Request Validation
- **File Extension:** Must be `.wav`.
- **MIME Type:** Must be either `audio/wav` or `audio/x-wav`.
- **File Size:** Must not exceed **100MB**; otherwise, a 400 error is returned.

#### Audio Preprocessing
Upon successful validation, the endpoint performs simulated audio preprocessing which includes noise reduction processes and format validation/conversion. This simulation is meant to mimic production-level audio processing and preps the file for analysis.

#### Error Handling
The endpoint responds with specific error messages for various failure scenarios:
- **Validation Errors:**
  - Invalid file extension: "Invalid file extension. Only .wav files are allowed." 
  - Invalid MIME type: Provides a message indicating the allowed MIME types.
  - File size exceeded: "File size exceeds the maximum limit of 100MB."
- **Integration Failures:**
  - In cases where the n8n workflow trigger fails after 3 retry attempts (with exponential backoff delays of 1s, 2s, and 4s), a 500 error is returned with details of the integration failure.

#### Integration with n8n Workflow
After processing, the endpoint assembles a payload and triggers the n8n workflow to handle further processing. The payload includes:
- `file_name`
- `file_size`
- `upload_timestamp`
- `metadata` (includes processing status and any additional data)

**Security & Compliance:**
- The request to the n8n webhook is made via HTTPS with enforced TLS v1.2+.
- HIPAA-compliant security headers are attached to ensure secure data transmission.

**Retry Mechanism:**
- On failure of the webhook call, the system retries the integration up to 3 times with exponential delays (1s, 2s, 4s).

#### Usage Example

**Request Example:**
Using `multipart/form-data`, send a POST request to `/api/upload` with the following key:

- `file`: The `.wav` file to be uploaded.

**Success Response Example:**
```json
{
    "success": true,
    "message": "Workflow triggered successfully"
}
```

**Error Response Examples:**
- For an invalid file extension:
```json
{
    "detail": "Invalid file extension. Only .wav files are allowed"
}
```
- For file size exceeding limit:
```json
{
    "detail": "File size exceeds the maximum limit of 100MB"
}
```

#### Troubleshooting and Recommendations
- Verify that the uploaded file is in `.wav` format and the MIME type is correctly set.
- Ensure that the file size is within the accepted limit.
- Check that the `N8N_WEBHOOK_URL` environment variable is correctly configured.
- Review the error messages for guidance on validation failures or integration issues.
- Ensure that HTTPS is properly configured with TLS v1.2+ and that all HIPAA-compliant security headers are included.

#### Performance & Compliance
- **Processing Time:** The endpoint is optimized to process uploads within 5 minutes.
- **HIPAA Compliance:** All transmissions adhere to HIPAA guidelines with enforced security protocols and proper error handling.

---

### Testing and Verification
- Verify that the `/api/upload` endpoint works as expected both in normal and edge case scenarios.
- Use the provided unit tests (located in `tests/test_upload.py`) to simulate file uploads and validate the endpoint behavior.
- Review and update test cases if necessary to ensure consistency with the endpoint's documented behavior.

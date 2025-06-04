# S3 Multipart Upload Documentation

This document provides an overview of the multipart upload functionality implemented in the Knowlio system. Multipart upload is essential for efficiently uploading large files to S3, providing benefits like:

- Improved throughput by uploading parts in parallel
- Quick recovery from network issues (only failed parts need to be retransmitted)
- Ability to pause and resume uploads
- Better handling of network timeouts with large files

## API Overview

The following API endpoints have been implemented for S3 uploads:

### Regular Upload

- `POST /uploads/url`: Generate a presigned URL for direct file upload
- `GET /uploads/download/{key}`: Generate a presigned URL for file download

### Multipart Upload

- `POST /uploads/multipart/init`: Initiate a multipart upload process
- `POST /uploads/multipart/part-url`: Generate a presigned URL for uploading a specific part
- `POST /uploads/multipart/complete`: Complete a multipart upload after all parts have been uploaded
- `DELETE /uploads/multipart/abort`: Abort a multipart upload and remove any uploaded parts
- `GET /uploads/multipart/parts`: List all parts that have been uploaded

## Client Implementation Workflow

The typical client workflow for multipart upload is:

1. **Initiate the multipart upload**
   - Call `POST /uploads/multipart/init` with file key and content type
   - Receive an `upload_id` which is required for all subsequent operations

2. **Split the file into chunks**
   - Typically 5MB chunks are recommended for best performance

3. **Upload each chunk**
   - For each part, call `POST /uploads/multipart/part-url` to get a presigned URL
   - Upload the chunk using a direct PUT request to the URL
   - Save the `ETag` value returned in the response headers

4. **Complete the upload**
   - After all parts are uploaded, call `POST /uploads/multipart/complete` with the list of parts and ETags
   - The S3 service will then assemble the parts into a single object

## Example Implementation

### Lambda Invocation Payloads

1. **Initiate a multipart upload:**

```json
{
  "processor_name": "s3_upload",
  "action": "initiate_multipart_upload",
  "payload": {
    "key": "large-files/myfile.zip",
    "content_type": "application/zip"
  }
}
```

2. **Generate a presigned URL for a part:**

```json
{
  "processor_name": "s3_upload",
  "action": "generate_presigned_part_upload_url",
  "payload": {
    "key": "large-files/myfile.zip",
    "upload_id": "abc123uploadid",
    "part_number": 1
  }
}
```

3. **Complete the multipart upload:**

```json
{
  "processor_name": "s3_upload",
  "action": "complete_multipart_upload",
  "payload": {
    "key": "large-files/myfile.zip",
    "upload_id": "abc123uploadid",
    "parts": [
      {"PartNumber": 1, "ETag": "\"etag1\""},
      {"PartNumber": 2, "ETag": "\"etag2\""},
      {"PartNumber": 3, "ETag": "\"etag3\""}
    ]
  }
}
```

### Browser Implementation Example

```javascript
// Step 1: Initiate upload
const initResponse = await fetch('/api/uploads/multipart/init', {
  method: 'POST',
  body: JSON.stringify({ key: 'myfiles/largefile.zip', content_type: 'application/zip' })
});
const { upload_id, key } = await initResponse.json();

// Step 2: Split file into chunks
const chunkSize = 5 * 1024 * 1024; // 5MB chunks
const file = document.getElementById('fileInput').files[0];
const chunks = Math.ceil(file.size / chunkSize);
const parts = [];

// Step 3: Upload each chunk
for (let partNumber = 1; partNumber <= chunks; partNumber++) {
  // Get part upload URL
  const urlResponse = await fetch('/api/uploads/multipart/part-url', {
    method: 'POST',
    body: JSON.stringify({ key, upload_id, part_number: partNumber })
  });
  const { url } = await urlResponse.json();
  
  // Upload the chunk
  const start = (partNumber - 1) * chunkSize;
  const end = Math.min(file.size, partNumber * chunkSize);
  const chunk = file.slice(start, end);
  
  const uploadResponse = await fetch(url, {
    method: 'PUT',
    body: chunk
  });
  
  // Save the ETag
  const etag = uploadResponse.headers.get('ETag');
  parts.push({ PartNumber: partNumber, ETag: etag });
}

// Step 4: Complete the upload
await fetch('/api/uploads/multipart/complete', {
  method: 'POST',
  body: JSON.stringify({ key, upload_id, parts })
});
```

## Best Practices

1. **Chunk Size**: Use 5MB-100MB chunks depending on file size and network reliability
   - For web browsers, 5-10MB is typically best
   - For server-side applications, 25-50MB can be more efficient

2. **Error Handling**: Implement proper retry logic for individual parts
   - Only retry failed parts, not the entire file
   - Implement exponential backoff for retries

3. **Cleanup**: Always abort incomplete uploads if the process fails
   - This prevents storage charges for incomplete uploads

4. **Performance**: Upload parts in parallel to maximize throughput
   - For browser implementations, limit concurrency to 3-6 parallel uploads
   - For server implementations, higher concurrency can be used based on resources

5. **Tracking**: Store the `upload_id` securely if supporting long-term pause/resume
   - This allows users to resume uploads even after browser refresh or application restart

## Monitoring and Troubleshooting

- Use `list_parts` API to check which parts have been successfully uploaded
- Check CloudWatch logs for any errors in the Lambda functions
- Implement client-side progress tracking to show upload status to users

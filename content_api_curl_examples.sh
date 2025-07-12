#!/bin/bash

# Content API CURL Examples
# These examples assume the API is running on localhost:3000
# Replace with your actual API Gateway URL and add proper authentication headers

API_URL="https://your-api-gateway-url.amazonaws.com/prod"
AUTH_TOKEN="your-auth-token-here"

echo "=== Content API CURL Examples ==="

# 1. Upload Book Content Metadata - ISBN Only (Recommended)
echo "1. Upload Book Content Metadata - ISBN Only (Recommended):"
curl -X POST "${API_URL}/content/metadata/upload" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -d '{
    "type": "BOOK",
    "isbn": "978-0-132350-88-4"
  }'

echo -e "\n\n"

# 1b. Upload Book Content Metadata - Full Details (Alternative)
echo "1b. Upload Book Content Metadata - Full Details (Alternative):"
curl -X POST "${API_URL}/content/metadata/upload" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -d '{
    "type": "BOOK",
    "title": "The Art of Software Engineering",
    "authors": ["John Doe", "Jane Smith"],
    "year": "2024",
    "isbn": "978-1234567890",
    "keywords": ["software", "engineering", "best practices"],
    "rag_status": "ENABLED",
    "training_status": "DISABLED",
    "licensing_status": "ENABLED"
  }'

echo -e "\n\n"

# 2. Upload Audio Content Metadata
echo "2. Upload Audio Content Metadata:"
curl -X POST "${API_URL}/content/metadata/upload" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -d '{
    "type": "AUDIO",
    "title": "Introduction to Machine Learning",
    "duration": 3600,
    "format": "mp3",
    "rag_status": "ENABLED",
    "training_status": "ENABLED",
    "licensing_status": "DISABLED"
  }'

echo -e "\n\n"

# 3. Get Content Details
echo "3. Get Content Details:"
curl -X POST "${API_URL}/content/get/550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -d '{
    "content_id": "550e8400-e29b-41d4-a716-446655440000"
  }'

echo -e "\n\n"

# 4. Update Content Metadata
echo "4. Update Content Metadata:"
curl -X PUT "${API_URL}/content/update/550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -d '{
    "content_id": "550e8400-e29b-41d4-a716-446655440000",
    "updates": {
      "title": "The Art of Software Engineering - 2nd Edition",
      "year": "2025",
      "keywords": ["software", "engineering", "best practices", "agile"],
      "metadata": {
        "edition": "2nd",
        "language": "English"
      }
    }
  }'

echo -e "\n\n"

# 5. Update Single Content Attribute
echo "5. Update Single Content Attribute:"
curl -X PATCH "${API_URL}/content/attribute/550e8400-e29b-41d4-a716-446655440000/rag_status" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -d '{
    "content_id": "550e8400-e29b-41d4-a716-446655440000",
    "attribute": "rag_status",
    "value": "DISABLED"
  }'

echo -e "\n\n"

# 6. Upload Content Blob
echo "6. Upload Content Blob:"
curl -X POST "${API_URL}/content/blob/upload" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -d '{
    "content_id": "550e8400-e29b-41d4-a716-446655440000",
    "s3_uri": "s3://knowlio-content-bucket/books/550e8400-e29b-41d4-a716-446655440000/content.pdf"
  }'

echo -e "\n\n"

# 7. Search Content - By Type
echo "7. Search Content - By Type:"
curl -X POST "${API_URL}/content/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -d '{
    "type": "BOOK",
    "limit": 10
  }'

echo -e "\n\n"

# 8. Search Content - By Publisher
echo "8. Search Content - By Publisher:"
curl -X POST "${API_URL}/content/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -d '{
    "publisher": "Tech Publications Inc.",
    "limit": 20
  }'

echo -e "\n\n"

# 9. Search Content - By Multiple Criteria
echo "9. Search Content - By Multiple Criteria:"
curl -X POST "${API_URL}/content/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -d '{
    "type": "BOOK",
    "year": "2024",
    "rag_status": "ENABLED",
    "limit": 15
  }'

echo -e "\n\n"

# 10. Search Content - With Pagination
echo "10. Search Content - With Pagination:"
curl -X POST "${API_URL}/content/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -d '{
    "type": "AUDIO",
    "limit": 5,
    "pagination_token": "eyJjb250ZW50X2lkIjogIjEyMzQ1In0="
  }'

echo -e "\n\n"

# 11. Search Content - By Keywords
echo "11. Search Content - By Keywords:"
curl -X POST "${API_URL}/content/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -d '{
    "keywords": ["machine learning", "AI"],
    "limit": 10
  }'

echo -e "\n\n"

# 12. Search Content - By Status
echo "12. Search Content - By Status:"
curl -X POST "${API_URL}/content/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -d '{
    "status": "ACTIVE",
    "training_status": "ENABLED",
    "limit": 25
  }'

echo -e "\n\n"

# 13. Archive Content
echo "13. Archive Content:"
curl -X POST "${API_URL}/content/archive/550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -d '{
    "content_id": "550e8400-e29b-41d4-a716-446655440000"
  }'

echo -e "\n\n"

# 14. Search Content - Legacy Format with Attributes
echo "14. Search Content - Legacy Format with Attributes:"
curl -X POST "${API_URL}/content/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -d '{
    "attributes": {
      "type": "BOOK",
      "authors": ["John Doe"]
    },
    "limit": 10
  }'

echo -e "\n\n"

echo "=== End of Content API Examples ==="

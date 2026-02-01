#!/bin/bash
# Test script for vision-translate endpoint

echo "=== Testing Vision Translate Endpoint ==="
echo

# Test 1: Valid request
echo "1. Testing valid translation request:"
curl -X POST "http://localhost:8000/api/vision-translate/ba0e7b2f-9692-45fb-8259-33ff53181ca1/page1_img1.png" \
  -H "Content-Type: application/json" \
  -d '{"target_language": "russian"}' \
  | jq '.'
echo

# Test 2: Invalid language
echo "2. Testing invalid language:"
curl -X POST "http://localhost:8000/api/vision-translate/ba0e7b2f-9692-45fb-8259-33ff53181ca1/page1_img1.png" \
  -H "Content-Type: application/json" \
  -d '{"target_language": "spanish"}' \
  | jq '.'
echo

# Test 3: Nonexistent job
echo "3. Testing nonexistent job:"
curl -X POST "http://localhost:8000/api/vision-translate/nonexistent-job/test.png" \
  -H "Content-Type: application/json" \
  -d '{"target_language": "russian"}' \
  | jq '.'
echo

# Test 4: English translation
echo "4. Testing English translation:"
curl -X POST "http://localhost:8000/api/vision-translate/ba0e7b2f-9692-45fb-8259-33ff53181ca1/page1_img1.png" \
  -H "Content-Type: application/json" \
  -d '{"target_language": "english"}' \
  | jq '.'
echo

echo "=== All tests completed ==="
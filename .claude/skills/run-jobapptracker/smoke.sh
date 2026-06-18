#!/bin/bash
# JobApplicationTracker smoke test — verify all critical endpoints respond
# Run this after starting both backend (uvicorn :8000) and frontend (npm :5173)

set -e

echo "🧪 JobApplicationTracker Smoke Test"
echo "===================================="
echo ""

# Color codes
OK="\033[0;32m✓\033[0m"
ERR="\033[0;31m✗\033[0m"

failed=0

# Test backend health
echo -n "Health check (localhost:8000/health)... "
if response=$(curl -s http://localhost:8000/health); then
  if echo "$response" | jq -e '.status == "ok"' > /dev/null 2>&1; then
    echo "$OK"
  else
    echo "$ERR (bad response: $response)"
    ((failed++))
  fi
else
  echo "$ERR (no connection)"
  ((failed++))
fi

# Test profile endpoint
echo -n "Profile endpoint (/api/profile)... "
if response=$(curl -s http://localhost:8000/api/profile); then
  if echo "$response" | jq -e '.full_name' > /dev/null 2>&1; then
    profile_name=$(echo "$response" | jq -r '.full_name')
    echo "$OK ($profile_name)"
  else
    echo "$ERR (no full_name field)"
    ((failed++))
  fi
else
  echo "$ERR (connection failed)"
  ((failed++))
fi

# Test applications list
echo -n "Applications list (/api/applications)... "
if response=$(curl -s http://localhost:8000/api/applications); then
  if echo "$response" | jq -e 'type == "array"' > /dev/null 2>&1; then
    count=$(echo "$response" | jq 'length')
    echo "$OK ($count applications)"
  else
    echo "$ERR (not an array)"
    ((failed++))
  fi
else
  echo "$ERR (connection failed)"
  ((failed++))
fi

# Test Swagger docs
echo -n "Swagger API docs (/openapi.json)... "
if response=$(curl -s http://localhost:8000/openapi.json); then
  if echo "$response" | jq -e '.paths | length > 0' > /dev/null 2>&1; then
    path_count=$(echo "$response" | jq '.paths | length')
    echo "$OK ($path_count endpoints)"
  else
    echo "$ERR (no paths)"
    ((failed++))
  fi
else
  echo "$ERR (connection failed)"
  ((failed++))
fi

# Test frontend
echo -n "Frontend (localhost:5173)... "
if status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173); then
  if [ "$status" = "200" ]; then
    echo "$OK"
  else
    echo "$ERR (HTTP $status)"
    ((failed++))
  fi
else
  echo "$ERR (no connection)"
  ((failed++))
fi

echo ""
if [ $failed -eq 0 ]; then
  echo "✓ All endpoints OK — system ready for testing"
  exit 0
else
  echo "✗ $failed check(s) failed — see errors above"
  exit 1
fi

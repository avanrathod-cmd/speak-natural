#!/bin/bash
# API Endpoint Calls Reference
# =============================================================================
# Edit this file with your frequently-used endpoint calls
# Copy and paste commands directly into terminal, or run: source API_CALLS_REFERENCE.sh
#
# SETUP: Set your Supabase token before calling any endpoint:
#   export TOKEN="<paste token from browser console>"
#
# Get token from browser DevTools console:
#   Object.entries(localStorage).find(([k]) => k.includes('supabase'))?.[1]
#   then copy the access_token value from the JSON.
# =============================================================================

BASE_URL="http://localhost:8000"

_auth_header() {
  if [ -z "$TOKEN" ]; then
    echo "Error: TOKEN is not set. Run: export TOKEN=\"<your_token>\"" >&2
    return 1
  fi
  echo "Authorization: Bearer $TOKEN"
}

# ============= PRODUCT ENDPOINTS =============

# CREATE PRODUCT (auto-generates sales script)
# POST /sales/products
create_product() {
  curl -X POST "$BASE_URL/sales/products" \
    -H "accept: application/json" \
    -H "Content-Type: application/json" \
    -H "$(_auth_header)" \
    -d '{
      "name": "Your Product Name",
      "description": "Product description here",
      "customer_profile": "Target customer profile",
      "talking_points": "Key talking points"
    }'
}

# LIST PRODUCTS
# GET /sales/products
list_products() {
  curl -X GET "$BASE_URL/sales/products" \
    -H "accept: application/json" \
    -H "$(_auth_header)"
}

# LIST PRODUCTS WITH SEARCH
# GET /sales/products?search=query
search_products() {
  curl -X GET "$BASE_URL/sales/products?search=$1" \
    -H "accept: application/json" \
    -H "$(_auth_header)"
}

# ============= SCRIPT ENDPOINTS =============

# GET SCRIPT BY ID
# GET /sales/scripts/{script_id}
get_script() {
  curl -X GET "$BASE_URL/sales/scripts/$1" \
    -H "accept: application/json" \
    -H "$(_auth_header)"
}

# REGENERATE SCRIPT FOR PRODUCT
# POST /sales/scripts/regenerate
regenerate_script() {
  curl -X POST "$BASE_URL/sales/scripts/regenerate" \
    -H "accept: application/json" \
    -H "Content-Type: application/json" \
    -H "$(_auth_header)" \
    -d "{\"product_id\": \"$1\"}"
}

# ============= CALL UPLOAD & ANALYSIS =============

# UPLOAD SALES CALL (audio file)
# POST /sales/calls/upload
# Usage: upload_call /path/to/audio.wav [rep_hint]
upload_call() {
  local audio_file=$1
  local rep_hint=${2:-}

  if [ -z "$audio_file" ]; then
    echo "Usage: upload_call <audio_file_path> [rep_hint]"
    return 1
  fi

  local url="$BASE_URL/sales/calls/upload"
  [ -n "$rep_hint" ] && url="$url?rep_hint=$rep_hint"

  curl -X POST "$url" \
    -H "accept: application/json" \
    -H "$(_auth_header)" \
    -F "audio_file=@$audio_file"
}

# CHECK CALL PROCESSING STATUS
# GET /sales/calls/{call_id}/status
check_call_status() {
  curl -X GET "$BASE_URL/sales/calls/$1/status" \
    -H "accept: application/json" \
    -H "$(_auth_header)"
}

# GET CALL ANALYSIS (once processing is complete)
# GET /sales/calls/{call_id}/analysis
get_call_analysis() {
  curl -X GET "$BASE_URL/sales/calls/$1/analysis" \
    -H "accept: application/json" \
    -H "$(_auth_header)"
}

# LIST ALL CALLS FOR CURRENT USER
# GET /sales/calls
list_calls() {
  curl -X GET "$BASE_URL/sales/calls?limit=50&offset=0" \
    -H "accept: application/json" \
    -H "$(_auth_header)"
}

# REANALYZE AN EXISTING CALL
# POST /sales/calls/{call_id}/reanalyze
reanalyze_call() {
  if [ -z "$1" ]; then
    echo "Usage: reanalyze_call <call_id>"
    return 1
  fi
  curl -X POST "$BASE_URL/sales/calls/$1/reanalyze" \
    -H "accept: application/json" \
    -H "$(_auth_header)"
}

# ============= QUICK EXAMPLES =============

# Setup:
#   source API_CALLS_REFERENCE.sh
#   export TOKEN="eyJ..."

# Example: Upload audio and capture call_id
#   upload_call ./recording.wav spk_0

# Example: Check status
#   check_call_status "call_abc123def456"

# Example: Get analysis after status shows "completed"
#   get_call_analysis "call_abc123def456"

# Example: Reanalyze a call
#   reanalyze_call "call_abc123def456"

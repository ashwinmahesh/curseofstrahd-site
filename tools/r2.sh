#!/bin/zsh -i
# rclone for the downloads bucket (Cloudflare R2), with credentials from the environment only:
#   tools/r2.sh lsf r2:curseofstrahd-downloads
#   tools/r2.sh copyto <file> r2:curseofstrahd-downloads/<key>
# Reads COS_CLOUDFLARE_R2_API_TOKEN and COS_CLOUDFLARE_ACCOUNT_ID (Ashwin's zshrc, hence the interactive shell). An R2
# token's S3 credentials are its id (from Cloudflare's verify call) and the SHA-256 of its value. Nothing is printed or
# written to disk; rclone gets them as RCLONE_CONFIG_R2_* variables for this one run.
set -euo pipefail
: "${COS_CLOUDFLARE_R2_API_TOKEN:?missing COS_CLOUDFLARE_R2_API_TOKEN}"
: "${COS_CLOUDFLARE_ACCOUNT_ID:?missing COS_CLOUDFLARE_ACCOUNT_ID}"
token_id="$(curl -s -H "Authorization: Bearer $COS_CLOUDFLARE_R2_API_TOKEN" \
  https://api.cloudflare.com/client/v4/user/tokens/verify | /usr/bin/python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["id"])')"
export RCLONE_CONFIG_R2_TYPE=s3
export RCLONE_CONFIG_R2_PROVIDER=Cloudflare
export RCLONE_CONFIG_R2_ACCESS_KEY_ID="$token_id"
export RCLONE_CONFIG_R2_SECRET_ACCESS_KEY="$(printf '%s' "$COS_CLOUDFLARE_R2_API_TOKEN" | shasum -a 256 | cut -d' ' -f1)"
export RCLONE_CONFIG_R2_ENDPOINT="https://${COS_CLOUDFLARE_ACCOUNT_ID}.r2.cloudflarestorage.com"
export RCLONE_CONFIG_R2_NO_CHECK_BUCKET=true
exec rclone "$@"

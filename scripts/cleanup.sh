#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT_DIR"

printf "Cleaning caches and generated artifacts...\n"

# Python caches
find . -type d -name "__pycache__" -prune -exec rm -rf {} + || true
find . -type f -name "*.pyc" -delete || true
find . -type f -name "*.pyo" -delete || true

# Data artifacts (keep vectorstore optionally)
if [[ "${1:-}" == "deep" ]]; then
  printf "Deep clean: removing vectorstore index and processed data...\n"
  rm -f data/vectorstore/index.faiss data/vectorstore/index.pkl || true
  rm -f data/processed/processed_chunks_*.json || true
else
  printf "Shallow clean: keeping vectorstore index. Use 'cleanup.sh deep' to remove.\n"
fi

# Optionally archive transcripts
if [[ "${2:-}" == "archive-transcripts" && -d data/raw/transcripts ]]; then
  ts=$(date +%Y%m%d_%H%M%S)
  tar -czf "transcripts_archive_${ts}.tar.gz" -C data/raw transcripts && rm -f data/raw/transcripts/*.txt || true
  printf "Transcripts archived to transcripts_archive_${ts}.tar.gz\n"
fi

printf "Done.\n"

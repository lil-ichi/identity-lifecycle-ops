#!/usr/bin/env bash
echo "Starting IdentityLifecycle Ops on http://localhost:8080..."
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

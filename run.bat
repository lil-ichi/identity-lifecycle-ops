@echo off
echo ========================================================
echo  Starting IdentityLifecycle Ops (SecOps & IAM Console)
echo ========================================================

python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

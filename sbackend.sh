#!/bin/bash

echo "Starting backend server..."
cd /data/taosha/taosha_analyse_platform
source .venv/bin/activate
cd /data/taosha/taosha_analyse_platform/backend
rm -rf .worker_registry/
nohup uvicorn main:app --workers=4 --port 50011 --host 0.0.0.0 &
tail -200f nohup.out
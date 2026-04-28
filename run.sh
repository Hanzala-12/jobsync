#!/bin/bash
# Run the JobSync API server
uvicorn backend.main:app --reload

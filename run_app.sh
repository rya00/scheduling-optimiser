#!/bin/bash

# Staff Scheduling Optimization Dashboard Launcher
# =================================================

echo "Starting Staff Scheduling Optimization Dashboard..."
echo ""
echo "The app will open in your default browser at http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd "$(dirname "$0")"
streamlit run streamlit_app.py

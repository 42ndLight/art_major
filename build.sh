#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Building project..."

# Install dependencies if needed (Vercel usually handles this via requirements.txt, but good to ensure)
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run database migrations against Neon
python manage.py migrate --no-input

echo "Build complete!"
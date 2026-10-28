#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Building project..."

# Collect static files
python manage.py collectstatic --no-input

# Run database migrations against Neon
python manage.py migrate --no-input

echo "Build complete!"
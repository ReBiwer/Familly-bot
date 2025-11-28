#!/bin/bash
set -e

alembic upgrade head

echo "Starting application..."

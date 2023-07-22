#!/bin/bash

set -e

# Generate Prisma client
python -m prisma generate

# Start the main Python script
python main.py

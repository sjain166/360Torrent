#!/bin/bash

# Step 1: Create virtual environment
python -m venv myenv

# Step 2: Activate the virtual environment
source myenv/bin/activate

# Step 3: Install dependencies
pip install -r requirements.txt

# Step 4: Create tests directory
mkdir -p tests/data

#!/usr/bin/env python3
"""
Simple wrapper to call the main encode_faces.py script
"""
import os
import sys

# Get the directory of this script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Path to the main encode_faces.py script
main_script = os.path.join(current_dir, 'encode_faces.py')

# Execute the main script
os.system(f'python "{main_script}"')
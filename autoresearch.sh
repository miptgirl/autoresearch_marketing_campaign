#!/bin/bash
set -euo pipefail

python3 -m py_compile optimise.py
python3 optimise.py

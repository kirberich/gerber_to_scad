#!/bin/bash

set -euo pipefail

poetry run mypy \
    src 

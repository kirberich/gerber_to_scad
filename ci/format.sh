#!/bin/bash
set -euo pipefail

ruff_fix=("--fix")
if [[ ${1-} == "--check" ]]; then
    ruff_fix=("--diff")
    ruff_format=("--check" "--diff")
    shift
fi

files=("$@")

if [[ $# == 0 ]]; then
    files=(".")
fi

EXIT_CODE=0

poetry run ruff check --select I001,I002 "${ruff_fix[@]}" "${files[@]}" || EXIT_CODE=1
poetry run ruff format "${ruff_format[@]}" "${files[@]}" || EXIT_CODE=1

exit "${EXIT_CODE}"

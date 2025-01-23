#!/bin/bash
set -euo pipefail

args=(".")
found_files_in_args=0

for file in "$@"; do
    if [[ -f ${file} ]]; then
        args=("$@")
        found_files_in_args=1
        break
    fi
done

if [[ ${found_files_in_args} == 0 ]] && [[ $# -gt 0 ]]; then
    args=("." "$@")
fi

poetry run ruff check "${args[@]}"

#!/usr/bin/env bash
#
# Stamp a version into the workspace, ready to build.
#
# The repo carries a bare major.minor everywhere (version = "0.2", "database_wrapper == 0.2")
# so a local editable install of all six packages resolves against itself. The published
# patch number is derived from the commit count, so it exists only at build time - this
# script writes it in. CI runs it right before `python -m build`; the rewrite is
# workspace-only and is never committed.
#
# Usage: scripts/set_version.bash [VERSION]
#
#   VERSION   Defaults to scripts/version.bash output, e.g. 0.2.145.
#
# Rewrites, across all six packages:
#   src/*/pyproject.toml  - the project version and every database_wrapper* == pin
#   config.py             - app_version
#
# The cross-package pins are exact on purpose: an adapter subclasses core internals, so a
# mismatched pair is not a combination that was ever tested. A pin left unstamped would
# publish 0.2.145 packages requiring "database_wrapper == 0.2", which resolves to nothing
# on PyPI - so this verifies its own work and fails loudly rather than shipping that.

set -Eeuo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_PATH="$(cd "${THIS_DIR}/.." && pwd)"

CONFIG_FILE="${BASE_PATH}/src/database_wrapper/database_wrapper/config.py"

VERSION="${1:-$("${THIS_DIR}/version.bash")}"

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+(\.[0-9]+)?(\.dev[0-9]+)?$ ]]; then
    echo "error: \"${VERSION}\" is not a version this project publishes (0.2, 0.2.145, 0.2.145.dev0)" >&2
    exit 1
fi

shopt -s nullglob
PYPROJECTS=("${BASE_PATH}"/src/*/pyproject.toml)
shopt -u nullglob

if [ "${#PYPROJECTS[@]}" -eq 0 ]; then
    echo "error: no packages found under ${BASE_PATH}/src" >&2
    exit 1
fi

for pyproject in "${PYPROJECTS[@]}"; do
    sed -i -E \
        -e "s/^version = \".*\"$/version = \"${VERSION}\"/" \
        -e "s/(database_wrapper(_[a-z]+)? == )[0-9][0-9a-zA-Z.]*/\1${VERSION}/g" \
        "$pyproject"
done

sed -i -E "s/(\"app_version\": \")[^\"]*(\")/\1${VERSION}\2/" "$CONFIG_FILE"

# Assert the rewrite landed rather than trusting that every pattern matched. A sed that
# quietly matches nothing is the failure mode worth catching, and it is only visible here.
FAILED=false

for pyproject in "${PYPROJECTS[@]}"; do
    if ! grep -q "^version = \"${VERSION}\"$" "$pyproject"; then
        echo "error: ${pyproject#"${BASE_PATH}/"} has no version line reading ${VERSION}" >&2
        FAILED=true
    fi
    while IFS= read -r pin; do
        if [[ "$pin" != *"== ${VERSION}"* ]]; then
            echo "error: ${pyproject#"${BASE_PATH}/"} left a pin unstamped: ${pin}" >&2
            FAILED=true
        fi
    done < <(grep -oE "database_wrapper(_[a-z]+)? == [^\"]*" "$pyproject")
done

if ! grep -q "\"app_version\": \"${VERSION}\"" "$CONFIG_FILE"; then
    echo "error: ${CONFIG_FILE#"${BASE_PATH}/"} has no app_version reading ${VERSION}" >&2
    FAILED=true
fi

if [ "$FAILED" = true ]; then
    exit 1
fi

echo "Stamped ${VERSION} into ${#PYPROJECTS[@]} packages"

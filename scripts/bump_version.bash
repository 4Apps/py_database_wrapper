#!/usr/bin/env bash
#
# Bump the manual part of the version, the only part a human decides.
#
# Usage: scripts/bump_version.bash [major|minor]
#
# Reads and rewrites .version (format: X.Y), then restamps the six pyproject.toml files
# and config.py to the new bare major.minor so a local editable install still resolves
# against itself. Both are staged.
#
# There is no "patch" here on purpose: the patch is read off the release tags, so the new
# minor's first release is .0 and nothing has to be stored for it.

set -Eeuo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_PATH="$(cd "${THIS_DIR}/.." && pwd)"

VERSION_FILE="${BASE_PATH}/.version"
BUMP_TYPE="${1:-minor}"

if [ ! -f "$VERSION_FILE" ]; then
    echo "error: ${VERSION_FILE} not found" >&2
    exit 1
fi

CURRENT_VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"

if [[ ! "$CURRENT_VERSION" =~ ^[0-9]+\.[0-9]+$ ]]; then
    echo "error: ${VERSION_FILE} must be major.minor - found \"${CURRENT_VERSION}\"" >&2
    exit 1
fi

MAJOR="${CURRENT_VERSION%%.*}"
MINOR="${CURRENT_VERSION##*.}"

case "$BUMP_TYPE" in
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        ;;
    minor)
        MINOR=$((MINOR + 1))
        ;;
    patch)
        echo "error: the patch comes from the release tags - run scripts/release_tag.bash instead" >&2
        exit 1
        ;;
    *)
        echo "error: unknown bump type \"${BUMP_TYPE}\". Use: major, minor" >&2
        exit 1
        ;;
esac

NEW_VERSION="${MAJOR}.${MINOR}"

echo "$NEW_VERSION" > "$VERSION_FILE"
"${THIS_DIR}/set_version.bash" "$NEW_VERSION"

git -C "$BASE_PATH" add "$VERSION_FILE" "${BASE_PATH}"/src/*/pyproject.toml \
    "${BASE_PATH}/src/database_wrapper/database_wrapper/config.py"

echo "  Version bumped: ${CURRENT_VERSION} -> ${NEW_VERSION}"
echo "  Next release would be $("${THIS_DIR}/version.bash")"

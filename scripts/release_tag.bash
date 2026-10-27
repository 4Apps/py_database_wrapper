#!/usr/bin/env bash
#
# Create the release tag for the current commit: v<.version>.<next patch of that minor>.
#
# Nothing is published by this script, and nothing is published by pushing the tag either.
# The tag only marks the commit; publishing happens when a GitHub *release* is created from
# it, which is the deliberate act - a version on PyPI can never be replaced or reused, and
# a release here mints six of them at once.
#
# Usage: scripts/release_tag.bash [--yes]
#
#   --yes   Skip the confirmation prompt. For a release job that has already decided.

set -Eeuo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_PATH="$(cd "${THIS_DIR}/.." && pwd)"

ASSUME_YES=false
for argument in "$@"; do
    case "$argument" in
        --yes)
            ASSUME_YES=true
            ;;
        *)
            echo "error: unknown option ${argument}" >&2
            exit 2
            ;;
    esac
done

VERSION="$("${THIS_DIR}/version.bash")"
TAG="v${VERSION}"
BRANCH="$(git -C "$BASE_PATH" rev-parse --abbrev-ref HEAD)"

# A tag names a commit, so the tree it describes has to be the tree that was committed
if [ -n "$(git -C "$BASE_PATH" status --porcelain)" ]; then
    echo "error: working tree is not clean; commit or stash before tagging" >&2
    exit 1
fi

# Any release tag counts, not only this minor's: after a minor bump version.bash no longer
# sees the old tag, and would happily mint the same tree again under a new number
RELEASED_AS="$(git -C "$BASE_PATH" tag --points-at HEAD | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -1 || true)"
if [ -n "$RELEASED_AS" ]; then
    echo "error: this commit is already released as ${RELEASED_AS}. Commit first." >&2
    exit 1
fi

# The release body is the changelog section, so a tag without one would publish blank notes
if ! "${THIS_DIR}/changelog.bash" notes "$TAG" >/dev/null; then
    echo "       Run scripts/changelog.bash prepare, commit CHANGELOG.md, then tag." >&2
    exit 1
fi

# .version set below a minor that was already released would publish a version PyPI keeps
# ranking under the older, higher one - and it can never be withdrawn and re-uploaded.
LATEST_TAG="$(git -C "$BASE_PATH" tag -l 'v*' | sort -V | tail -1)"
if [ -n "$LATEST_TAG" ]; then
    HIGHEST="$(printf '%s\n%s\n' "$LATEST_TAG" "$TAG" | sort -V | tail -1)"
    if [ "$HIGHEST" != "$TAG" ]; then
        echo "error: ${TAG} sorts below the existing ${LATEST_TAG}." >&2
        echo "       .version is behind a released minor; bump it rather than publishing" >&2
        echo "       a version that pip will never resolve as the newest." >&2
        exit 1
    fi
fi

# Releases are cut from master
if [ "$BRANCH" != "master" ]; then
    echo "warning: on \"${BRANCH}\", not master. Releases are normally tagged on master."
fi

echo
echo "  tag:     ${TAG}"
echo "  branch:  ${BRANCH}"
echo "  commit:  $(git -C "$BASE_PATH" log -1 --format='%h %s')"
echo "  publishes: database_wrapper{,_pgsql,_mysql,_mssql,_sqlite,_redis} ${VERSION}"
echo

if [ "$ASSUME_YES" = false ]; then
    read -r -p "Create this tag? [y/N] " answer
    if [ "$answer" != "y" ] && [ "$answer" != "Y" ]; then
        echo "Nothing was tagged."
        exit 1
    fi
fi

git -C "$BASE_PATH" tag -a "$TAG" -m "Release ${TAG}"

echo
echo "Created ${TAG}. It is local until you push it:"
echo
echo "    git push origin ${TAG}"
echo
echo "Pushing publishes nothing. Then create the GitHub release from the tag, which is"
echo "what uploads all six ${VERSION} packages to PyPI:"
echo
echo "    scripts/changelog.bash notes ${TAG} | gh release create ${TAG} --title ${TAG} --notes-file -"
echo

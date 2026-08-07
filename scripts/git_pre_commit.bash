#!/bin/bash

# To enable this hook:
#  cd .git/hooks/ && ln -s ../../scripts/git_pre_commit.bash ./pre-commit

# set -e
PLATFORM=`uname`

# Find base path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
BASE_PATH="$(cd "$SCRIPT_DIR/../../" && pwd)"

# Git stuff
COMMIT="HEAD"

# Test non-ascii filenames
echo
echo "*Testing non-ascii filenames.. "
if [ $(git diff --cached --name-only --diff-filter=A -z $COMMIT | LC_ALL=C tr -d '[ -~]\0' | wc -c) -gt 0 ]; then
    echo "Error: Attempt to add a non-ascii file name."
    echo
    echo "This can cause problems if you want to work"
    echo "with people on other platforms."
    echo
    echo "To be portable it is advisable to rename the file ..."
    echo
    exit 1
fi
echo " Done"
echo

# Trying to compile all changed python files
if [ $(git diff-index --cached --name-only --diff-filter=ACMR $COMMIT | grep \\.py | grep -v node_modules | wc -l) -gt 0 ]; then
    echo
    echo "*Python file(-s) changed, running lint.."

    for file in $(git diff-index --cached --name-only --diff-filter=ACMR $COMMIT | grep \\.py | grep -v node_modules); do
        env python3 -m compileall -q $file

        if [ "$?" != "0" ]; then
            echo "!!! ERROR: $COMMIT $file"
            exit 1
        fi
    done

    echo " Done"
    echo
fi

# Style check with ruff
echo
echo "*Running ruff style checks... "
ruff check "$BASE_PATH/src"
if [ "$?" != "0" ]; then
    echo "!!! ERROR: $COMMIT $file"
    exit 1
fi
echo "Done"
echo

# Record which commit the build came from. The version itself is not touched here: the
# patch part is the git commit count, so it moves on its own and is stamped at build time.
echo "*Updating commit info.. "
./scripts/update_commit_info.bash

# Test for whitespace errors
# This needs to be left as last one as there are scripts before this that trims whitespace
echo
echo "*Testing for whitespace errors.. "
git diff-index --cached --check $COMMIT --
if [ "$?" != "0" ]; then
    echo "!!! ERROR !!!"
    exit 1
fi
echo " Done"
echo

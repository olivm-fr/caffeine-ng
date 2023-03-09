#!/bin/sh
#
# Read the version from version control if possible, or from a fallback file.
# The fallback file is only present in the tarballs.

set -e

git describe --long --tags --dirty --always 2>/dev/null || cat ./version

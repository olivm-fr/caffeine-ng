#!/bin/sh
#
# Write a static version to be used in tarballs.

set -eux

TAG=$(git -C "$MESON_SOURCE_ROOT" describe --exact-match --tags)
echo "$TAG-dist" | cut -c 2- > "$MESON_DIST_ROOT/version"

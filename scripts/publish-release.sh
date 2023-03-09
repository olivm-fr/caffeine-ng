#!/bin/sh
#
# Publishes a new tarball for downstream distributions to pick up.

set -ex

TAG=$(git describe --exact-match --tags)
VERSION=$(./scripts/read_version.sh)

meson dist -C build --formats gztar
tea release create \
  --asset "build/meson-dist/caffeine-ng-$VERSION.tar.gz" \
  --title "$TAG" \
  --tag "$TAG"

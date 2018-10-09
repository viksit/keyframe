#!/bin/bash

#set -o nounset
set -o pipefail
set -o xtrace
set -o errexit

pushd ~/work/keyframe
#source keyframevenv/bin/activate
set -o nounset

#git checkout master
#git pull --rebase

GIT_VERSION=$(git rev-parse HEAD)
KEYFRAME_VERSION="keyframe_$(date +%Y%m%d_%H%M%S)_${GIT_VERSION}"
echo "${KEYFRAME_VERSION}" > keyframe_version.txt

# Some weird errors after deploy:
# ImportError: bad magic number in 'pymyra.api.client'
# Try to clean things out before the deploy.
find . -name "*.pyc" -exec rm {} ';'
zappa update dev  # This does return a non-zero exit code if deploy fails.

popd

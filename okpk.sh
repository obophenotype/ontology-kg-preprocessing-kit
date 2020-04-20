#!/bin/sh
# Wrapper script for docker.
#
# This is used primarily for wrapping the GNU Make workflow.
# Instead of typing "make TARGET", type "./run.sh make TARGET".
# This will run the make workflow within a docker container.
#
# See README-editors.md for more details.
docker run -v $PWD:/work -w /work -e ROBOT_JAVA_ARGS='-Xmx8G' --rm -ti obolibrary/okpk "$@"
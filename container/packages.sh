#!/bin/sh
# The tools in the docker and apptainer images. Both images run this, so add what your projects need here once.
# (The bwrap backend uses the tools installed in your WSL Ubuntu instead.)
set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
    ca-certificates curl git less nano jq ripgrep file procps unzip xz-utils \
    python3 python3-venv python3-pip \
    build-essential \
    nodejs npm
rm -rf /var/lib/apt/lists/*
mkdir -p /home/agent /opt/agy /opt/agybox /run/agybox
chmod 1777 /home/agent

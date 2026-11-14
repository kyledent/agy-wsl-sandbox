# The image for AGYBOX_BACKEND=docker. agy and the entry script are mounted read-only at run time, so updating agy
# does not need a new image. ./agybox rebuilds this when this file or packages.sh changes.
FROM ubuntu:24.04
COPY packages.sh /tmp/packages.sh
RUN sh /tmp/packages.sh && rm /tmp/packages.sh
ENV HOME=/home/agent

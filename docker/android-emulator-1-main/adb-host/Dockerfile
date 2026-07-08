FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    adb curl iputils-ping net-tools \
    && rm -rf /var/lib/apt/lists/*

CMD ["tail", "-f", "/dev/null"]

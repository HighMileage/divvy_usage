FROM ubuntu:14.04

RUN apt-get update && apt-get install --fix-missing -y \
    build-essential \
    vim \
 && rm -rf /var/lib/apt/lists/*

CMD bash

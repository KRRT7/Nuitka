# Use Debian 12 as the base image
FROM debian:12-slim

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_BREAK_SYSTEM_PACKAGES=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    ccache \
    curl \
    git \
    libbz2-dev \
    libexpat1-dev \
    libffi-dev \
    libgdbm-dev \
    liblzma-dev \
    libncurses5-dev \
    libnss3-dev \
    libreadline-dev \
    libsqlite3-dev \
    libssl-dev \
    libzstd-dev \
    patchelf \
    python3 \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    scons \
    wget \
    zlib1g-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /src

# Copy Nuitka source code
COPY . /nuitka-src

# Install Nuitka from source
RUN pip3 install --no-cache-dir /nuitka-src

# Install common Nuitka dependencies for onefile and standalone
RUN pip3 install --no-cache-dir \
    appdirs \
    jinja2 \
    tqdm \
    zstandard

# Configure ccache
RUN mkdir -p /root/.cache/ccache
ENV NUITKA_CCACHE_BINARY=/usr/bin/ccache

# Default entrypoint
ENTRYPOINT ["python3", "-m", "nuitka"]

# Debian 13 "trixie" (current stable), slim, pinned by digest.
#
# Pinned deliberately: valgrind/callgrind instruction counts shift with glibc,
# gcc and CPython builds, so an unpinned tag silently invalidates historical
# benchmark numbers. Bump this digest only when you are prepared to re-baseline.
FROM debian:trixie-slim@sha256:d7e12182ce18b85b93007c1dedf31f2d29e01ccf3182cc4017c709b6259bc132

ENV DEBIAN_FRONTEND=noninteractive

# libc6-dbg is required by valgrind: without it the glibc suppression files
# cannot resolve and callgrind output is unreadable.
RUN apt-get update && apt-get install -y --no-install-recommends \
        valgrind \
        libc6-dbg \
        gcc \
        g++ \
        clang \
        lld \
        llvm \
        make \
        ccache \
        patchelf \
        binutils \
        gdb \
        git \
        curl \
        ca-certificates \
        sudo \
        less \
        procps \
        pkg-config \
        scons \
        chrpath \
    && rm -rf /var/lib/apt/lists/*

# Build dependencies for CPython. Deliberately NOT purged afterwards: apt would
# auto-remove the runtime libs they pulled in (libssl3, libsqlite3-0, liblzma5,
# readline), and since our source-built CPython is not a dpkg package apt cannot
# see that it links against them -- import ssl/sqlite3/lzma would break. They are
# useful for building C extensions in here anyway.
ARG PY_BUILD_DEPS="libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev libncursesw5-dev libffi-dev liblzma-dev uuid-dev tk-dev xz-utils"

# CPython 3.12 from source. The distro ships 3.13; 3.12 keeps parity with the
# previous devcontainer pin, and a source build with -g gives full DWARF so
# Nuitka's --zero-before=PyInit___main__ resolves under callgrind.
ARG PYTHON_VERSION=3.12.14
ARG PYTHON_SHA256=6c6df908d2c3fd24e6d76869e92542abd0f33aec9dfc18df8875f89660286d43

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ${PY_BUILD_DEPS}; \
    curl -fsSL -o /tmp/python.tgz "https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz"; \
    echo "${PYTHON_SHA256}  /tmp/python.tgz" | sha256sum -c -; \
    mkdir -p /tmp/python-src; \
    tar -xzf /tmp/python.tgz -C /tmp/python-src --strip-components=1; \
    cd /tmp/python-src; \
    # --with-valgrind teaches the pymalloc arena allocator to announce itself,
    # removing the flood of false "uninitialised value" reports.
    # No --enable-optimizations: PGO/BOLT make instruction counts unstable
    # between rebuilds, which is exactly what we are trying to avoid.
    ./configure \
        --prefix=/usr/local \
        --enable-shared \
        --with-valgrind \
        --with-ensurepip=install \
        --without-static-libpython \
        CFLAGS="-g -O2 -fno-omit-frame-pointer" \
        LDFLAGS="-Wl,-rpath,/usr/local/lib"; \
    make -j "$(nproc)"; \
    make install; \
    ldconfig; \
    cd /; \
    rm -rf /tmp/python-src /tmp/python.tgz; \
    rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/local/bin/python3.12 /usr/local/bin/python3 \
    && ln -sf /usr/local/bin/python3.12 /usr/local/bin/python \
    && python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel

# Non-root user; Codespaces and the devcontainer features expect uid/gid 1000.
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=1000
RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} --create-home --shell /bin/bash ${USERNAME} \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME}

# Let the non-root user pip-install without sudo (the source-built prefix is
# root-owned, and has no PEP 668 marker, so plain pip install works here).
RUN chown -R ${USER_UID}:${USER_GID} \
        /usr/local/lib/python3.12/site-packages \
        /usr/local/bin

# Deterministic hashing so dict/set iteration order cannot perturb counts.
ENV PYTHONHASHSEED=0 \
    PYTHONDONTWRITEBYTECODE=1 \
    CCACHE_DIR=/home/${USERNAME}/.ccache

USER ${USERNAME}

FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       dbus \
       dbus-user-session \
       dbus-x11 \
       flatpak \
       python3.12 \
       python3.12-venv \
       procps \
       sudo \
       util-linux \
       xdg-dbus-proxy \
    && printf '%s\n' 'root ALL=(ALL:ALL) NOPASSWD: ALL' > /etc/sudoers.d/lunita-ci-root \
    && chmod 0440 /etc/sudoers.d/lunita-ci-root \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
CMD ["sleep", "infinity"]

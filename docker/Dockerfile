# Development container for the Archangel project.
# Ubuntu 24.04 + ROS 2 Jazzy, run on top of a Docker/NVIDIA-enabled Ubuntu 26.04 host.

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8

# --- Base OS setup: locale, keys, useful tools ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    locales \
    curl \
    gnupg2 \
    lsb-release \
    ca-certificates \
    software-properties-common \
    && locale-gen en_US en_US.UTF-8 \
    && update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

# --- ROS 2 apt repository ---
RUN curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
    | tee /etc/apt/sources.list.d/ros2.list > /dev/null

# --- ROS 2 Jazzy desktop + general dev tools ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-jazzy-desktop \
    ros-dev-tools \
    git \
    build-essential \
    python3-pip \
    python3-colcon-common-extensions \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# --- Non-root user matching host UID/GID (passed as build args) ---
ARG USERNAME=devuser
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Ubuntu 24.04 base images ship a pre-existing 'ubuntu' user/group at UID/GID
# 1000, which can collide with the host UID/GID we're about to assign here.
# Remove it first so useradd/groupadd below never hits a conflict.
RUN if getent passwd ubuntu > /dev/null; then userdel -r ubuntu; fi \
    && if getent group ubuntu > /dev/null; then groupdel ubuntu; fi

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m -s /bin/bash $USERNAME \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# --- Auto-source ROS 2 environment on shell entry ---
RUN echo "source /opt/ros/jazzy/setup.bash" >> /home/$USERNAME/.bashrc

USER $USERNAME
WORKDIR /home/$USERNAME/ws

CMD ["/bin/bash"]

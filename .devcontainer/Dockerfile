FROM osrf/ros:jazzy-desktop

ARG USERNAME=ros
# Ubuntu 24.04 already ships a default user on uid 1000, so use 1001
ARG UID=1001
ARG GID=1001

RUN groupadd --gid $GID $USERNAME \
 && useradd --uid $UID --gid $GID -m -s /bin/bash $USERNAME \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
      sudo git nano less tree \
      python3-pip \
      python3-colcon-common-extensions \
      python3-argcomplete \
 && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
 && chmod 0440 /etc/sudoers.d/$USERNAME \
 && rm -rf /var/lib/apt/lists/*

USER $USERNAME

RUN echo "source /opt/ros/jazzy/setup.bash" >> /home/$USERNAME/.bashrc \
 && echo "source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash" \
      >> /home/$USERNAME/.bashrc

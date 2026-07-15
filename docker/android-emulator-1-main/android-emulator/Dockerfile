FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV SDK_URL=https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip

RUN apt-get update && apt-get install -y \
    curl unzip git wget openjdk-11-jdk \
    libgl1-mesa-dev libvirt-clients libvirt-daemon-system qemu-kvm \
    net-tools adb \
    x11vnc xvfb openbox \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/novnc/noVNC.git /opt/novnc && \
    git clone https://github.com/novnc/websockify /opt/novnc/utils/websockify

RUN mkdir -p /opt/android-sdk/cmdline-tools && \
    curl -o /tmp/tools.zip $SDK_URL && \
    unzip /tmp/tools.zip -d /opt/android-sdk/cmdline-tools && \
    mv /opt/android-sdk/cmdline-tools/cmdline-tools /opt/android-sdk/cmdline-tools/latest && \
    rm /tmp/tools.zip

ENV ANDROID_HOME=/opt/android-sdk
ENV PATH=$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/emulator:$ANDROID_HOME/platform-tools:$PATH

RUN yes | sdkmanager --licenses && \
    sdkmanager --install "platform-tools" \
                        "emulator" \
                        "platforms;android-30" \
                        "system-images;android-30;google_apis;x86"

RUN sed -i 's/^# \(deb .*universe\)$/\1/' /etc/apt/sources.list && \
    sed -i 's/^# \(deb .*multiverse\)$/\1/' /etc/apt/sources.list && \
    sed -i 's/^# \(deb .*restricted\)$/\1/' /etc/apt/sources.list && \
    apt-get update

RUN apt-get install -y \
    libxcb-cursor0 \
    libxkbcommon-x11-0 \
    mesa-utils \
    libglu1-mesa

COPY frida-server-17.15.5-android-x86 /data/local/tmp/frida-server
RUN chmod +x /data/local/tmp/frida-server

RUN echo "no" | avdmanager create avd -n test_avd -k "system-images;android-30;google_apis;x86" --device "pixel"

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5555 6080 27042

ENTRYPOINT ["/entrypoint.sh"]
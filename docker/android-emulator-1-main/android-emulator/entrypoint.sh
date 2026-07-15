#!/bin/bash
set -e

export DISPLAY=:0

Xvfb :0 -screen 0 1280x720x24 &
sleep 2
openbox &

x11vnc -display :0 -nopw -listen localhost -xkb -forever &
/opt/novnc/utils/novnc_proxy --vnc localhost:5900 --listen 6080 &

$ANDROID_HOME/emulator/emulator -avd test_avd \
  -no-audio -no-boot-anim -gpu swiftshader_indirect \
  -accel on -no-snapshot -port 5554 -verbose &

echo "⏳ Waiting for ADB device..."
adb wait-for-device

echo "🔧 Trying to switch to root mode..."
adb root || true

sleep 5
adb wait-for-device

echo "🔧 Configuring ADB over TCP..."

sleep 5

adb devices

echo "🎣 Starting Frida Server..."
sleep 10
adb shell /data/local/tmp/frida-server &
echo "✅ Frida Server started"

tail -f /dev/null
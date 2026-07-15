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

# ===== FRIDA SERVER =====
echo "🎣 Installing Frida Server..."

# Проверяем, есть ли файл в контейнере
if [ -f /data/local/tmp/frida-server ]; then
    # Копируем из контейнера в Android
    adb push /data/local/tmp/frida-server /data/local/tmp/frida-server
    adb shell chmod 755 /data/local/tmp/frida-server
    echo "✅ Frida Server installed"
else
    echo "❌ Frida Server not found in /data/local/tmp/"
    echo "   Please copy it manually:"
    echo "   docker cp frida-server android-emulator:/data/local/tmp/frida-server"
fi

echo "🚀 Starting Frida Server..."

# Запускаем на всех интерфейсах
adb shell "/data/local/tmp/frida-server -l 0.0.0.0 >/data/local/tmp/frida.log 2>&1 &"

sleep 3

echo "🔍 Checking Frida Server..."

# Проверка через pidof
FRIDA_PID=$(adb shell pidof frida-server | tr -d '\r')
if [ -n "$FRIDA_PID" ]; then
    echo "✅ Frida Server running (PID: $FRIDA_PID)"
else
    echo "❌ Frida Server not running"
    echo "--- Last 10 lines of frida.log ---"
    adb shell cat /data/local/tmp/frida.log | tail -10 || true
fi

# Проверка порта
echo "🔍 Checking port 27042..."
adb shell netstat -an | grep 27042

tail -f /dev/null
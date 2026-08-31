#!/usr/bin/env bash
set -euo pipefail

SDK_ROOT="${ANDROID_HOME:-/opt/android-sdk}"
BUILD_TOOLS_VERSION="${ANDROID_BUILD_TOOLS_VERSION:-36.0.0}"
PLATFORM_VERSION="${ANDROID_PLATFORM_VERSION:-android-36}"
APKTOOL_VERSION="${APKTOOL_VERSION:-2.11.1}"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
TOOLS_DIR="$ROOT_DIR/server/engine/_android_tools"
CMDTOOLS_URL="${CMDTOOLS_URL:-https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip}"
APKTOOL_URL="${APKTOOL_URL:-https://github.com/iBotPeaches/Apktool/releases/download/v${APKTOOL_VERSION}/apktool_${APKTOOL_VERSION}.jar}"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "missing required command: $1" >&2
    exit 1
  }
}

need_cmd curl
need_cmd unzip
need_cmd java
need_cmd javac
need_cmd keytool

mkdir -p "$SDK_ROOT/cmdline-tools" "$TOOLS_DIR"

if [ ! -x "$SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" ]; then
  tmp_zip="$(mktemp /tmp/cmdline-tools.XXXXXX.zip)"
  tmp_dir="$(mktemp -d /tmp/cmdline-tools.XXXXXX)"
  curl -fL --retry 3 --connect-timeout 30 --max-time 300 -o "$tmp_zip" "$CMDTOOLS_URL"
  unzip -q "$tmp_zip" -d "$tmp_dir"
  rm -rf "$SDK_ROOT/cmdline-tools/latest"
  mkdir -p "$SDK_ROOT/cmdline-tools/latest"
  if [ -d "$tmp_dir/cmdline-tools" ]; then
    cp -a "$tmp_dir/cmdline-tools/." "$SDK_ROOT/cmdline-tools/latest/"
  else
    cp -a "$tmp_dir/." "$SDK_ROOT/cmdline-tools/latest/"
  fi
  rm -rf "$tmp_zip" "$tmp_dir"
fi

export ANDROID_HOME="$SDK_ROOT"
export ANDROID_SDK_ROOT="$SDK_ROOT"
yes | "$SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" --sdk_root="$SDK_ROOT" --licenses >/tmp/android-sdk-licenses.log 2>&1 || true
"$SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" --sdk_root="$SDK_ROOT" \
  "platforms;${PLATFORM_VERSION}" \
  "build-tools;${BUILD_TOOLS_VERSION}" \
  "platform-tools"

if [ ! -s "$TOOLS_DIR/apktool.jar" ] || [ "$(stat -c%s "$TOOLS_DIR/apktool.jar" 2>/dev/null || echo 0)" -lt 1000000 ]; then
  curl -fL --retry 3 --connect-timeout 30 --max-time 300 -o "$TOOLS_DIR/apktool.jar" "$APKTOOL_URL"
fi

cat > /usr/local/bin/apktool << EOF2
#!/bin/sh
exec java -jar "$TOOLS_DIR/apktool.jar" "\$@"
EOF2
chmod +x /usr/local/bin/apktool

export PATH="$SDK_ROOT/build-tools/${BUILD_TOOLS_VERSION}:$SDK_ROOT/platform-tools:/usr/local/bin:$PATH"

echo "ANDROID_HOME=$SDK_ROOT"
echo "aapt2=$(command -v aapt2)"
echo "d8=$(command -v d8)"
echo "apksigner=$(command -v apksigner)"
echo "zipalign=$(command -v zipalign)"
echo "android.jar=$SDK_ROOT/platforms/${PLATFORM_VERSION}/android.jar"
echo "apktool=$(apktool --version 2>/dev/null || true)"
echo "done"

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DIST_DIR="${REPO_ROOT}/backend/dist/wence_ai"
PACKAGE_DIR="${REPO_ROOT}/backend/package"

APP_DISPLAY_NAME="WenCe AI"
APP_EXECUTABLE="wence_ai"
APP_BUNDLE="${PACKAGE_DIR}/${APP_DISPLAY_NAME}.app"
APP_CONTENTS="${APP_BUNDLE}/Contents"
APP_MACOS="${APP_CONTENTS}/MacOS"
APP_RESOURCES="${APP_CONTENTS}/Resources"
APP_VERSION="${APP_VERSION:-0.0.0}"
BUNDLE_VERSION="${APP_VERSION#v}"
ARCH="${WENCE_DARWIN_ARCH:-arm64}"
ZIP_PATH="${PACKAGE_DIR}/wence_ai-macos-${ARCH}-app.zip"
DMG_PATH="${PACKAGE_DIR}/wence_ai-macos-${ARCH}.dmg"
DMG_ROOT="${PACKAGE_DIR}/dmg-root"

if [[ -z "${BUNDLE_VERSION}" ]]; then
  BUNDLE_VERSION="0.0.0"
fi

if [[ ! -d "${DIST_DIR}" ]]; then
  echo "PyInstaller output not found: ${DIST_DIR}" >&2
  exit 1
fi

if [[ ! -f "${REPO_ROOT}/packaging/robot.icns" ]]; then
  echo "macOS icon not found: ${REPO_ROOT}/packaging/robot.icns" >&2
  exit 1
fi

mkdir -p "${PACKAGE_DIR}"
rm -rf "${APP_BUNDLE}" "${DMG_ROOT}" "${ZIP_PATH}" "${DMG_PATH}"
mkdir -p "${APP_MACOS}" "${APP_RESOURCES}"

cp -R "${DIST_DIR}" "${APP_RESOURCES}/wence_ai"
chmod +x "${APP_RESOURCES}/wence_ai/${APP_EXECUTABLE}"
cp "${REPO_ROOT}/packaging/robot.icns" "${APP_RESOURCES}/robot.icns"

cat > "${APP_MACOS}/${APP_EXECUTABLE}" <<'EOF'
#!/bin/sh
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP_DIR/Resources/wence_ai"
exec ./wence_ai "$@"
EOF
chmod +x "${APP_MACOS}/${APP_EXECUTABLE}"

cat > "${APP_CONTENTS}/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>zh_CN</string>
  <key>CFBundleDisplayName</key>
  <string>${APP_DISPLAY_NAME}</string>
  <key>CFBundleExecutable</key>
  <string>${APP_EXECUTABLE}</string>
  <key>CFBundleIdentifier</key>
  <string>ai.wence.WordAgent</string>
  <key>CFBundleIconFile</key>
  <string>robot</string>
  <key>CFBundleName</key>
  <string>${APP_DISPLAY_NAME}</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>${BUNDLE_VERSION}</string>
  <key>CFBundleVersion</key>
  <string>${BUNDLE_VERSION}</string>
  <key>LSMinimumSystemVersion</key>
  <string>10.15</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
EOF

ditto -c -k --sequesterRsrc --keepParent "${APP_BUNDLE}" "${ZIP_PATH}"

mkdir -p "${DMG_ROOT}"
cp -R "${APP_BUNDLE}" "${DMG_ROOT}/"
ln -s /Applications "${DMG_ROOT}/Applications"
hdiutil create -volname "${APP_DISPLAY_NAME}" -srcfolder "${DMG_ROOT}" -ov -format UDZO "${DMG_PATH}"

echo "Created ${ZIP_PATH}"
echo "Created ${DMG_PATH}"

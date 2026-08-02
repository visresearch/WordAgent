#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DIST_DIR="${REPO_ROOT}/backend/dist/wence_ai"
PACKAGE_DIR="${REPO_ROOT}/backend/package"
STAGING_DIR="${REPO_ROOT}/backend/build/fpm-deb"

APP_NAME="wence-ai"
APP_DISPLAY_NAME="WenCe AI"
APP_EXECUTABLE="wence_ai"
APP_VERSION="${APP_VERSION:-0.0.0}"
DEB_VERSION="${APP_VERSION#v}"
# Debian uses '~' for pre-release versions so they sort before the final
# release; convert tags such as 0.6.0-beta.1 to 0.6.0~beta.1.
if [[ "${DEB_VERSION}" == *-* ]]; then
  # Escape '~' in parameter expansion; otherwise Bash expands it to $HOME.
  DEB_VERSION="${DEB_VERSION/-/\~}"
fi

if [[ -z "${DEB_VERSION}" ]]; then
  DEB_VERSION="0.0.0"
fi

if [[ ! -d "${DIST_DIR}" ]]; then
  echo "PyInstaller output not found: ${DIST_DIR}" >&2
  exit 1
fi

if ! command -v fpm >/dev/null 2>&1; then
  echo "fpm is required. Install it with: gem install fpm" >&2
  exit 1
fi

rm -rf "${STAGING_DIR}"
mkdir -p \
  "${PACKAGE_DIR}" \
  "${STAGING_DIR}/opt/${APP_NAME}" \
  "${STAGING_DIR}/usr/bin" \
  "${STAGING_DIR}/usr/share/applications" \
  "${STAGING_DIR}/usr/share/icons/hicolor/256x256/apps"

cp -a "${DIST_DIR}/." "${STAGING_DIR}/opt/${APP_NAME}/"
chmod +x "${STAGING_DIR}/opt/${APP_NAME}/${APP_EXECUTABLE}"
cat > "${STAGING_DIR}/usr/bin/${APP_NAME}" <<LAUNCHER
#!/usr/bin/env bash
set -euo pipefail

export WENCE_DATA_DIR="\${WENCE_DATA_DIR:-\${HOME}/.wence_ai/wence_data}"
mkdir -p "\${WENCE_DATA_DIR}"

cd "/opt/${APP_NAME}"
exec "/opt/${APP_NAME}/${APP_EXECUTABLE}" "\$@"
LAUNCHER
chmod +x "${STAGING_DIR}/usr/bin/${APP_NAME}"
cp "${REPO_ROOT}/packaging/robot.png" "${STAGING_DIR}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"

cat > "${STAGING_DIR}/usr/share/applications/${APP_NAME}.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=${APP_DISPLAY_NAME}
Comment=AI writing assistant for Word documents
Exec=/usr/bin/${APP_NAME}
Icon=${APP_NAME}
Terminal=false
Categories=Office;Utility;
DESKTOP

fpm \
  --input-type dir \
  --output-type deb \
  --chdir "${STAGING_DIR}" \
  --name "${APP_NAME}" \
  --version "${DEB_VERSION}" \
  --architecture amd64 \
  --maintainer "WenCe AI Team" \
  --license "Apache-2.0" \
  --description "WenCe AI Writing Assistant" \
  --url "https://github.com/visresearch/WordAgent" \
  --depends "libxcb-cursor0" \
  --depends "libxcb-xinerama0" \
  --depends "libxkbcommon-x11-0" \
  --depends "libegl1" \
  --depends "libgl1" \
  --deb-compression xz \
  --package "${PACKAGE_DIR}/wence_ai-linux-x86_64.deb" \
  opt usr

echo "Created ${PACKAGE_DIR}/wence_ai-linux-x86_64.deb"

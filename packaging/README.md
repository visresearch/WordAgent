# Packaging

This directory contains the release packaging route used by GitHub Actions.

- `pyinstaller/package.spec` builds the shared `backend/dist/wence_ai` app directory.
- `linux/build-deb.sh` wraps that directory into `backend/package/wence_ai-linux-x86_64.deb` with fpm.
- `darwin/build-packages.sh` wraps that directory into `backend/package/wence_ai-macos-arm64-app.zip` and `backend/package/wence_ai-macos-arm64.dmg`.
- `windows/wence_ai.iss` and `windows/build-installer.ps1` wrap that directory into `backend/package/wence_ai-windows-x86_64-installer.exe` with Inno Setup.

Release artifacts:

- `backend/package/wence_ai-linux-x86_64-full.zip`
- `backend/package/wence_ai-macos-arm64-app.zip`
- `backend/package/wence_ai-macos-arm64.dmg`
- `backend/package/wence_ai-windows-x86_64-full.zip`

Linux runtime defaults are configured in `backend/main.py` before any Qt
imports. Widgets and the embedded WPS installation page use software rendering
so startup does not depend on a working GLX configuration. Frozen Linux builds
also isolate GIO modules from the host's GVfs libraries to avoid mixing them with
the bundled GLib. Explicit environment overrides are preserved.

For an older installed build that exits with `Could not initialize GLX`, launch
it with:

```bash
QT_XCB_GL_INTEGRATION=none QT_QUICK_BACKEND=software QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu wence-ai
```

#!/bin/bash
# Linux 打包脚本 - 支持 DEB 和 AppImage
# 使用方法: ./build_linux.sh [deb|appimage|all]

set -e  # 遇到错误立即退出

# 切换到项目根目录
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

VERSION="0.1.0"
APP_NAME="wence-ai"
BUILD_DIR="dist"
PACKAGE_DIR="deploy/package"

echo "=========================================="
echo "WenCe AI Linux 打包工具"
echo "版本: $VERSION"
echo "=========================================="

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${GREEN}[步骤]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[警告]${NC} $1"
}

print_error() {
    echo -e "${RED}[错误]${NC} $1"
}

# 检查依赖
check_dependencies() {
    print_step "检查依赖..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 未安装"
        exit 1
    fi
    
    if ! command -v uv &> /dev/null; then
        print_warn "uv 未安装，将使用 pip"
        USE_UV=false
    else
        USE_UV=true
    fi
}

# 安装依赖
install_deps() {
    print_step "安装 Python 依赖..."
    
    if [ "$USE_UV" = true ]; then
        uv pip install -e ".[build]"
    else
        pip3 install -e ".[build]"
    fi
}

# 使用 PyInstaller 构建二进制文件
build_binary() {
    print_step "使用 PyInstaller 构建二进制文件..."
    
    rm -rf "$BUILD_DIR" build
    pyinstaller deploy/wence.spec --clean --noconfirm
    
    if [ -f "$BUILD_DIR/$APP_NAME" ]; then
        echo -e "${GREEN}✓${NC} 二进制文件构建成功: $BUILD_DIR/$APP_NAME"
    else
        print_error "二进制文件构建失败"
        exit 1
    fi
}

# 构建 DEB 包
build_deb() {
    print_step "构建 DEB 包..."
    
    DEB_DIR="$PACKAGE_DIR/${APP_NAME}_${VERSION}_amd64"
    
    # 创建目录结构
    mkdir -p "$DEB_DIR/DEBIAN"
    mkdir -p "$DEB_DIR/usr/local/bin"
    mkdir -p "$DEB_DIR/usr/share/applications"
    mkdir -p "$DEB_DIR/usr/share/icons/hicolor/256x256/apps"
    mkdir -p "$DEB_DIR/usr/share/doc/$APP_NAME"
    
    # 复制二进制文件
    cp "$BUILD_DIR/$APP_NAME" "$DEB_DIR/usr/local/bin/"
    chmod +x "$DEB_DIR/usr/local/bin/$APP_NAME"
    
    # 创建 control 文件
    cat > "$DEB_DIR/DEBIAN/control" << EOF
Package: wence-ai
Version: $VERSION
Section: utils
Priority: optional
Architecture: amd64
Maintainer: WenCe AI Team <support@wence.ai>
Description: WenCe AI Writing Assistant
 智能写作助手后端服务
 提供 AI 驱动的文档处理和写作辅助功能
Depends: libc6 (>= 2.31)
EOF

    # 创建 postinst 脚本
    cat > "$DEB_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

# 创建配置目录
mkdir -p /etc/wence-ai
if [ ! -f /etc/wence-ai/.env ]; then
    cat > /etc/wence-ai/.env << 'ENVEOF'
# WenCe AI 配置文件
# 请根据实际情况修改以下配置

# OpenAI API 配置
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1

# 服务配置
HOST=0.0.0.0
PORT=3880

# 数据库路径
DATABASE_URL=sqlite+aiosqlite:///var/lib/wence-ai/wence.db
ENVEOF
fi

# 创建数据目录
mkdir -p /var/lib/wence-ai
chmod 755 /var/lib/wence-ai

echo "WenCe AI 安装完成！"
echo "请编辑 /etc/wence-ai/.env 配置文件，然后运行: wence-ai"

exit 0
EOF
    chmod +x "$DEB_DIR/DEBIAN/postinst"
    
    # 创建 desktop 文件（可选，如果有 GUI）
    cat > "$DEB_DIR/usr/share/applications/wence-ai.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=WenCe AI
Comment=智能写作助手
Exec=/usr/local/bin/wence-ai
Terminal=true
Categories=Office;Utility;
EOF
    
    # 复制文档
    cp README.md "$DEB_DIR/usr/share/doc/$APP_NAME/" 2>/dev/null || echo "README.md not found"
    
    # 构建 DEB 包
    dpkg-deb --build "$DEB_DIR"
    
    DEB_FILE="${APP_NAME}_${VERSION}_amd64.deb"
    mv "${DEB_DIR}.deb" "$PACKAGE_DIR/$DEB_FILE"
    
    echo -e "${GREEN}✓${NC} DEB 包构建成功: $PACKAGE_DIR/$DEB_FILE"
    echo "安装命令: sudo dpkg -i $PACKAGE_DIR/$DEB_FILE"
}

# 构建 AppImage
build_appimage() {
    print_step "构建 AppImage..."
    
    APPDIR="$PACKAGE_DIR/WenCeAI.AppDir"
    
    # 创建 AppDir 结构
    mkdir -p "$APPDIR/usr/bin"
    mkdir -p "$APPDIR/usr/share/applications"
    mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
    
    # 复制二进制文件
    cp "$BUILD_DIR/$APP_NAME" "$APPDIR/usr/bin/"
    chmod +x "$APPDIR/usr/bin/$APP_NAME"
    
    # 创建 AppRun
    cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"

# 设置配置目录
CONFIG_DIR="${HOME}/.config/wence-ai"
mkdir -p "$CONFIG_DIR"

if [ ! -f "$CONFIG_DIR/.env" ]; then
    cat > "$CONFIG_DIR/.env" << 'ENVEOF'
# WenCe AI 配置文件
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
HOST=127.0.0.1
PORT=3880
DATABASE_URL=sqlite+aiosqlite:///${HOME}/.local/share/wence-ai/wence.db
ENVEOF
    echo "已创建配置文件: $CONFIG_DIR/.env"
    echo "请编辑此文件配置 API Key"
fi

cd "$CONFIG_DIR"
exec "${HERE}/usr/bin/wence-ai" "$@"
EOF
    chmod +x "$APPDIR/AppRun"
    
    # 创建 desktop 文件
    cat > "$APPDIR/wence-ai.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=WenCe AI
Comment=智能写作助手
Exec=wence-ai
Icon=wence-ai
Terminal=true
Categories=Office;Utility;
EOF
    
    # 创建默认图标（如果没有的话）
    if [ ! -f "$APPDIR/wence-ai.png" ]; then
        # 使用 ImageMagick 创建简单图标（如果有的话）
        if command -v convert &> /dev/null; then
            convert -size 256x256 xc:#4A90E2 -pointsize 72 -fill white -gravity center \
                -annotate +0+0 "WenCe" "$APPDIR/wence-ai.png"
        else
            print_warn "ImageMagick 未安装，跳过图标创建"
            touch "$APPDIR/wence-ai.png"
        fi
    fi
    
    cp "$APPDIR/wence-ai.desktop" "$APPDIR/usr/share/applications/"
    cp "$APPDIR/wence-ai.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/"
    
    # 检测并下载 appimagetool（支持多个位置）
    APPIMAGETOOL="appimagetool-x86_64.AppImage"
    APPIMAGETOOL_PATH=""
    
    # 脚本已经 cd 到项目根目录，所以检测 deploy/ 子目录
    if [ -f "deploy/$APPIMAGETOOL" ]; then
        APPIMAGETOOL_PATH="deploy/$APPIMAGETOOL"
        echo -e "${GREEN}✓${NC} 使用 deploy 目录的 appimagetool"
    elif [ -f "$APPIMAGETOOL" ]; then
        APPIMAGETOOL_PATH="./$APPIMAGETOOL"
        echo -e "${GREEN}✓${NC} 使用当前目录的 appimagetool"
    elif [ -f "$HOME/$APPIMAGETOOL" ]; then
        APPIMAGETOOL_PATH="$HOME/$APPIMAGETOOL"
        echo -e "${GREEN}✓${NC} 使用 HOME 目录的 appimagetool"
    elif command -v appimagetool &> /dev/null; then
        APPIMAGETOOL_PATH="appimagetool"
        echo -e "${GREEN}✓${NC} 使用系统安装的 appimagetool"
    else
        # 都没找到，下载到 deploy 目录
        print_step "下载 appimagetool..."
        wget -q --show-progress -O "deploy/$APPIMAGETOOL" "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
        chmod +x "deploy/$APPIMAGETOOL"
        APPIMAGETOOL_PATH="deploy/$APPIMAGETOOL"
    fi
    
    # 确保可执行
    if [ -f "$APPIMAGETOOL_PATH" ]; then
        chmod +x "$APPIMAGETOOL_PATH"
    fi
    
    # 构建 AppImage
    ARCH=x86_64 "$APPIMAGETOOL_PATH" "$APPDIR" "$PACKAGE_DIR/${APP_NAME}-${VERSION}-x86_64.AppImage"
    
    echo -e "${GREEN}✓${NC} AppImage 构建成功: $PACKAGE_DIR/${APP_NAME}-${VERSION}-x86_64.AppImage"
    echo "运行命令: ./$PACKAGE_DIR/${APP_NAME}-${VERSION}-x86_64.AppImage"
}

# 主函数
main() {
    BUILD_TYPE=${1:-all}
    
    check_dependencies
    install_deps
    build_binary
    
    mkdir -p "$PACKAGE_DIR"
    
    case $BUILD_TYPE in
        deb)
            build_deb
            ;;
        appimage)
            build_appimage
            ;;
        all)
            build_deb
            build_appimage
            ;;
        *)
            print_error "未知的构建类型: $BUILD_TYPE"
            echo "使用方法: $0 [deb|appimage|all]"
            exit 1
            ;;
    esac
    
    echo ""
    echo -e "${GREEN}=========================================="
    echo "构建完成！"
    echo "==========================================${NC}"
    ls -lh "$PACKAGE_DIR"
}

main "$@"

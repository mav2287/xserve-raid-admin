#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PATCHES="$SCRIPT_DIR/patches"
ORIGINAL="$SCRIPT_DIR/original/RAID_Admin_original.jar"
OUTPUT_JAR="$SCRIPT_DIR/build/RAID_Admin.jar"
APP_DIR="$SCRIPT_DIR/build/RAID Admin.app"

# Find Java 8
JAVA_HOME=$(/usr/libexec/java_home -v 1.8 2>/dev/null || /usr/libexec/java_home 2>/dev/null)
JAVAC="$JAVA_HOME/bin/javac"
JAR="$JAVA_HOME/bin/jar"

if [ ! -x "$JAVAC" ]; then
    echo "Error: Java 8 compiler not found. Install Amazon Corretto 8 or similar."
    exit 1
fi

echo "Using Java: $JAVA_HOME"
echo ""

# Clean
rm -rf "$SCRIPT_DIR/build"
mkdir -p "$SCRIPT_DIR/build/classes"

# Extract original JAR
echo "Extracting original JAR..."
cd "$SCRIPT_DIR/build/classes"
"$JAR" xf "$ORIGINAL"

# Compile patches
echo "Compiling patches..."
"$JAVAC" -source 8 -target 8 -cp "$SCRIPT_DIR/build/classes" \
    "$PATCHES/sun/io/MalformedInputException.java" \
    -d "$SCRIPT_DIR/build/classes"

"$JAVAC" -source 8 -target 8 -cp "$SCRIPT_DIR/build/classes" \
    "$PATCHES/com/apple/eio/FileManager.java" \
    -d "$SCRIPT_DIR/build/classes"

"$JAVAC" -source 8 -target 8 -cp "$SCRIPT_DIR/build/classes" \
    "$PATCHES/com/apple/mrj/MRJFileUtils.java" \
    -d "$SCRIPT_DIR/build/classes"

"$JAVAC" -source 8 -target 8 -cp "$SCRIPT_DIR/build/classes" \
    "$PATCHES/com/apple/mrj/MRJApplicationUtils.java" \
    -d "$SCRIPT_DIR/build/classes"

"$JAVAC" -source 8 -target 8 -cp "$SCRIPT_DIR/build/classes" \
    "$PATCHES/Launcher.java" \
    -d "$SCRIPT_DIR/build/classes"

# Update manifest to use our Launcher
echo "Main-Class: Launcher" > "$SCRIPT_DIR/build/manifest.txt"

# Build patched JAR
echo "Building patched JAR..."
cd "$SCRIPT_DIR/build/classes"
"$JAR" cfm "$OUTPUT_JAR" "$SCRIPT_DIR/build/manifest.txt" .

# Build .app bundle
echo "Building app bundle..."
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

cp "$OUTPUT_JAR" "$APP_DIR/Contents/Resources/RAID_Admin.jar"
cp "$SCRIPT_DIR/original/RAIDAdmin.icns" "$APP_DIR/Contents/Resources/AppIcon.icns"
cp "$SCRIPT_DIR/original/RAIDAdminFirmware.icns" "$APP_DIR/Contents/Resources/"

# Info.plist
cat > "$APP_DIR/Contents/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>RAIDAdmin</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.apple.RAIDAdmin</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>RAID Admin</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.5.1</string>
    <key>CFBundleVersion</key>
    <string>2</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>CFBundleDocumentTypes</key>
    <array>
        <dict>
            <key>CFBundleTypeExtensions</key>
            <array><string>xfb</string></array>
            <key>CFBundleTypeName</key>
            <string>Xserve RAID Firmware Bundle</string>
            <key>CFBundleTypeRole</key>
            <string>Viewer</string>
            <key>CFBundleTypeIconFile</key>
            <string>RAIDAdminFirmware</string>
        </dict>
    </array>
    <key>NSLocalNetworkUsageDescription</key>
    <string>RAID Admin needs access to the local network to discover and manage Xserve RAID systems.</string>
    <key>NSBonjourServices</key>
    <array>
        <string>_xserveraid._tcp</string>
        <string>_xserve._tcp</string>
    </array>
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsArbitraryLoads</key>
        <true/>
        <key>NSAllowsLocalNetworking</key>
        <true/>
    </dict>
</dict>
</plist>
PLIST

# Launcher script
cat > "$APP_DIR/Contents/MacOS/RAIDAdmin" << 'LAUNCHER'
#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
RESOURCES_DIR="$(dirname "$DIR")/Resources"
JAR="$RESOURCES_DIR/RAID_Admin.jar"
ICON="$RESOURCES_DIR/AppIcon.icns"

find_java() {
    if [ -x "$(/usr/libexec/java_home -v 1.8 2>/dev/null)/bin/java" ]; then
        echo "$(/usr/libexec/java_home -v 1.8)/bin/java"; return
    fi
    if [ -x "$(/usr/libexec/java_home -v 11 2>/dev/null)/bin/java" ]; then
        echo "$(/usr/libexec/java_home -v 11)/bin/java"; return
    fi
    if [ -x "$(/usr/libexec/java_home 2>/dev/null)/bin/java" ]; then
        echo "$(/usr/libexec/java_home)/bin/java"; return
    fi
    command -v java 2>/dev/null && return
    return 1
}

JAVA=$(find_java)
if [ -z "$JAVA" ]; then
    osascript -e 'display dialog "Java Runtime not found.\n\nRAID Admin requires Java 8 or later.\n\nInstall Amazon Corretto, Azul Zulu, or Eclipse Temurin." with title "RAID Admin" buttons {"OK"} default button "OK" with icon stop' 2>/dev/null
    exit 1
fi

ICON_PNG="/tmp/RAIDAdmin_icon.png"
if [ -f "$ICON" ] && [ ! -f "$ICON_PNG" ]; then
    sips -s format png "$ICON" --out "$ICON_PNG" --resampleWidth 256 >/dev/null 2>&1
fi

exec "$JAVA" \
    -Xmx256m \
    -Xdock:name="RAID Admin" \
    -Xdock:icon="$ICON_PNG" \
    -Dapple.laf.useScreenMenuBar=true \
    -Dapple.awt.application.name="RAID Admin" \
    -Dcom.apple.mrj.application.apple.menu.about.name="RAID Admin" \
    -Djava.awt.headless=false \
    -Dapple.awt.application.appearance=NSAppearanceNameAqua \
    -Dswing.defaultlaf=com.apple.laf.AquaLookAndFeel \
    -jar "$JAR" \
    "$@"
LAUNCHER
chmod +x "$APP_DIR/Contents/MacOS/RAIDAdmin"

# Sign
codesign --force --deep --sign - "$APP_DIR" 2>/dev/null || true

# Clean up build intermediates
rm -rf "$SCRIPT_DIR/build/classes" "$SCRIPT_DIR/build/manifest.txt"

echo ""
echo "Build complete!"
echo "  JAR: $OUTPUT_JAR"
echo "  App: $APP_DIR"
echo ""
echo "To install: cp -R \"$APP_DIR\" /Applications/"

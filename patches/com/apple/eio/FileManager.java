package com.apple.eio;

import java.io.File;
import java.io.IOException;

/**
 * Replacement for the non-functional Apple Extended IO FileManager stub.
 * Maps the old Mac OS folder type constants to real macOS paths.
 */
public class FileManager {
    public static final int kDesktopFolderType = 0x6465736B;      // 'desk'
    public static final int kPreferencesFolderType = 0x70726566;  // 'pref'
    public static final int kSystemFolderType = 0x6D616373;       // 'macs'

    public static String findFolder(int folderType) {
        String home = System.getProperty("user.home");
        switch (folderType) {
            case kDesktopFolderType:      return home + "/Desktop";
            case kPreferencesFolderType:  return home + "/Library/Preferences";
            default:                      return home;
        }
    }

    public static String findFolder(short domain, int folderType) {
        return findFolder(folderType);
    }

    public static String findFolder(short domain, int folderType, boolean createIfNeeded) {
        String path = findFolder(folderType);
        if (createIfNeeded && path != null) {
            new File(path).mkdirs();
        }
        return path;
    }

    public static void openURL(String url) throws IOException {
        try {
            java.awt.Desktop.getDesktop().browse(new java.net.URI(url));
        } catch (Exception e) {
            Runtime.getRuntime().exec(new String[]{"open", url});
        }
    }

    public static int OSTypeToInt(String type) {
        if (type == null || type.length() != 4) return 0;
        return (type.charAt(0) << 24) | (type.charAt(1) << 16) | (type.charAt(2) << 8) | type.charAt(3);
    }

    public static String getResource(String resourceName) throws IOException {
        java.net.URL url = FileManager.class.getClassLoader().getResource(resourceName);
        return url != null ? url.getPath() : null;
    }

    public static void setFileType(String filename, int type) { }
    public static void setFileCreator(String filename, int creator) { }
    public static void setFileCreatorAndType(String filename, int creator, int type) { }
    public static int getFileType(String filename) { return 0; }
    public static int getFileCreator(String filename) { return 0; }
}

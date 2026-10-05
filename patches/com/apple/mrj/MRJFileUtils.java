package com.apple.mrj;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;

/** Preserve the original stubs; bridge only the Desktop lookup used by both file dialogs. */
public class MRJFileUtils {
    public static final MRJOSType kAppleMenuFolderType = new MRJOSType(1634561653);
    public static final MRJOSType kCachedDataFolderType = new MRJOSType(1667326824);
    public static final MRJOSType kChewableItemsFolderType = new MRJOSType(1718382196);
    public static final MRJOSType kControlPanelFolderType = new MRJOSType(1668575852);
    public static final MRJOSType kDesktopFolderType = new MRJOSType(1684370283);
    public static final MRJOSType kExtensionFolderType = new MRJOSType(1702392942);
    public static final MRJOSType kFontsFolderType = new MRJOSType(1718578804);
    public static final MRJOSType kPreferencesFolderType = new MRJOSType(1886545254);
    public static final MRJOSType kPrintMonitorDocsFolderType = new MRJOSType(1886547572);
    public static final MRJOSType kShutdownFolderType = new MRJOSType(1936221286);
    public static final MRJOSType kStartupFolderType = new MRJOSType(1937011316);
    public static final MRJOSType kSystemFolderType = new MRJOSType(1835098995);
    public static final MRJOSType kTemporaryFolderType = new MRJOSType(1952804208);
    public static final MRJOSType kTrashFolderType = new MRJOSType(1953657704);
    public static final MRJOSType kWhereToEmptyTrashFolderType = new MRJOSType(1701671028);
    public static final short kUserDomain = -32763;

    public static File findApplication(MRJOSType arg0) throws FileNotFoundException { return null; }
    public static File findFolder(MRJOSType arg0) throws FileNotFoundException { return arg0 == kDesktopFolderType ? new File(System.getProperty("user.home"), "Desktop") : null; }
    public static File findFolder(short arg0, MRJOSType arg1) throws FileNotFoundException { return null; }
    public static File findFolder(short arg0, MRJOSType arg1, boolean arg2) throws FileNotFoundException { return null; }
    public static MRJOSType getFileCreateor(File arg0) throws IOException { return null; }
    public static MRJOSType getFileType(File arg0) throws IOException { return null; }
    public static File getResource(String arg0) throws FileNotFoundException { return null; }
    public static File getResource(String arg0, String arg1) throws FileNotFoundException { return null; }
    public static void openURL(String arg0) throws IOException {  }
    public static void setDefaultFileCreator(MRJOSType arg0) {  }
    static void setDefaultFileType(MRJOSType arg0) {  }
    public static void setFileCreator(File arg0, MRJOSType arg1) throws IOException {  }
    public static void setFileLastModified(File arg0, Long arg1) {  }
    public static void setFileType(File arg0, MRJOSType arg1) throws IOException {  }
    public static void setFileTypeAndCreator(File arg0, MRJOSType arg1, MRJOSType arg2) throws IOException {  }
}

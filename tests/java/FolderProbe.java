import com.apple.mrj.MRJFileUtils;
import com.apple.mrj.MRJOSType;
import fixture.OfflineGuard;
import java.io.File;
import java.lang.reflect.Field;

/** No dialogs, firmware, writes or controller initialization. */
public final class FolderProbe {
    public static void main(String[] args) throws Exception {
        OfflineGuard.install();
        boolean fixed = Boolean.parseBoolean(args[0]);
        File desktop = MRJFileUtils.findFolder(MRJFileUtils.kDesktopFolderType);
        if (fixed ? !new File(System.getProperty("user.home"), "Desktop").equals(desktop) : desktop != null)
            throw new AssertionError("Unexpected Desktop lookup");
        for (Field field : MRJFileUtils.class.getFields()) {
            if (field.getType() == MRJOSType.class) {
                MRJOSType value = (MRJOSType) field.get(null);
                if (value != MRJFileUtils.kDesktopFolderType && MRJFileUtils.findFolder(value) != null)
                    throw new AssertionError("Unused folder stub changed");
                if (MRJFileUtils.findFolder(MRJFileUtils.kUserDomain, value) != null ||
                    MRJFileUtils.findFolder(MRJFileUtils.kUserDomain, value, true) != null)
                    throw new AssertionError("Unused overload changed");
            }
        }
        if (MRJFileUtils.findFolder(null) != null || MRJFileUtils.findFolder(new MRJOSType(0x6465736b)) != null)
            throw new AssertionError("Singleton boundary broadened");
        OfflineGuard.assertUntouched();
        System.out.println("PASS desktop_bridge=" + fixed + "; unused constants/overloads preserved; forbidden attempts=0");
    }
}

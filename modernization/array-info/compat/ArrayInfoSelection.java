package compat;

import com.apple.xsr.DriveSelectionPanel;

/** Translate the array-list sentinel only at the information-view boundary. */
public final class ArrayInfoSelection {
    private ArrayInfoSelection() {}

    public static void setArrayIndex(DriveSelectionPanel panel, int id) {
        if (id == 0) id = DriveSelectionPanel.INDEX_NONE;
        panel.setArrayIndex(id);
    }
}

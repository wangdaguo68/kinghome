# 保险箱 Enhancement Design

2026-05-12

## Overview

Four enhancements to the SafeBox WPF application:
1. Application icon
2. MSI installer package
3. UI redesign (Wabi-Sabi Dark aesthetic)
4. In-vault folder management

## 1. Application Icon

Generate a minimal lock + "箱" character icon as `.ico` with sizes 16/32/48/256px.

- Embed in `.csproj` via `<ApplicationIcon>` property
- WiX installer references the same icon for shortcuts and ARP entry

## 2. MSI Installer (WiX Toolset)

Use WiX v4+ to produce a standard Windows MSI.

- Registers in Add/Remove Programs with name "保险箱"
- Creates Start Menu shortcut (with icon)
- Offers desktop shortcut (opt-in)
- Respects user-chosen install directory
- Single-file MSI output placed in `dist/`

## 3. UI Redesign — Wabi-Sabi Dark

### Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| bg-primary | `#1C1C1C` | Window background |
| bg-surface | `rgba(255,255,255,0.03)` | Card/panel surface |
| bg-elevated | `#29211A` | Dialog, context menu |
| border-subtle | `rgba(255,255,255,0.06)` | Panel borders |
| border-accent | `rgba(212,165,116,0.2)` | Active/focus borders |
| text-primary | `#E0D6CC` | Primary text |
| text-secondary | `#888` | Secondary text |
| text-muted | `#6B5B4F` | Muted labels |
| accent | `#D4A574` | Warm gold accent |
| accent-gradient | `linear-gradient(#C4946A, #A0724A)` | Primary buttons |
| danger | `#C06050` | Delete actions |

### Layout Structure

**Login Page:** Centered single-column, password dots instead of plain text field, large unlock button with gold gradient, recovery key section collapsed by default with subtle link.

**Main Vault (unlocked):**
- **Top bar** (48px): Breadcrumb path (保险箱 / 当前文件夹), lock button on right
- **Left sidebar** (200px): Folder tree, "新建文件夹" button at bottom with dashed border
- **Center** (flex): Grid of file/folder cards with icon, name, size, date
- **Right preview** (260px, collapsible): Selected file preview — image, text, or metadata
- **Bottom bar** (28px): Status text, vault storage usage

### Typography
- System UI font (Segoe UI on Windows)
- Title: 24px, weight 400
- Section labels: 9px, letter-spacing 2px, uppercase, muted
- File names: 12px, weight 500
- Meta text: 10px, muted

## 4. Folder Management

### Data Model Changes

`VaultItem` gains an optional `FolderPath` property (relative path string, e.g. `"照片"` or `"工作/合同"`).

`VaultIndex` gains a `Folders` collection: `ObservableCollection<string>` — each entry is a folder path.

### Operations
- **New Folder:** Dialog with name input, creates entry in index, refreshes sidebar
- **Rename Folder:** Context menu on folder, updates all items with that path prefix
- **Delete Folder:** Warns if folder contains items, then deletes folder + removes items (or moves to root)
- **Move File:** Drag-and-drop or context menu to move item between folders
- **Navigate:** Click folder in sidebar to filter view to items in that path

### Default Behavior
- Imported files land in current folder (or root if no folder selected)
- Sidebar always shows "全部文件" (root view, shows items from all folders)

## Implementation Order

1. Data model + folder logic in VaultService
2. UI redesign (XAML + code-behind)
3. Application icon
4. WiX installer project

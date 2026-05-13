# 保险箱 批量操作与性能优化 Design

2026-05-13

## Overview

Three enhancements to the SafeBox WPF application:
1. Fix UI freezing (async file operations)
2. Batch checkbox selection + right-click context menu + double-click to open
3. Export-with-delete option (default: export then delete from vault)

## 1. Fix UI Freezing — Async File Operations

### Root Cause
All encryption/decryption and file I/O runs synchronously on the UI thread. Previewing large video files blocks the UI completely.

### Solution
Offload heavy operations to background threads via `Task.Run`, keep UI thread responsive.

| Operation | Before | After |
|-----------|--------|-------|
| Import files | UI thread encrypt loop | `Task.Run` per file, UI progress update |
| Preview decrypt | UI thread sync decrypt | `Task.Run` decrypt, dispatch result to UI |
| Export file(s) | UI thread sync | `Task.Run` decrypt + write |
| Video cache cleanup | Deleted immediately after write (race) | Clean on vault lock / app close only |

### Thread Safety
- `VaultService` accessed only from UI thread for state mutations (lock, create, import, delete)
- Background tasks receive copies of needed data (byte arrays, paths)
- UI dispatcher used to update controls after background work completes
- Wait cursor shown during background operations to indicate busy state

### Video Preview Fix
- Write temp cache file, play video, do NOT delete immediately
- Delete cache only on vault lock, app close, or when another file is previewed
- Set `PreviewVideo.Source = null` then delete, avoiding file-in-use conflicts

## 2. Batch Checkbox Selection + Right-Click Menu + Double-Click Open

### Data Model Change

`VaultFileRow` gains:
```csharp
public bool IsChecked { get; set; }  // for checkbox binding
```

### ListView Changes

- Add a `CheckBox` as the first column template (no header text, 30px wide)
- Enable `SelectionMode="Extended"` for multi-select with Ctrl/Shift
- Header checkbox for select-all / deselect-all

### Right-Click ContextMenu (single file only)

Menu items:
- **导出** — `SaveFileDialog` to choose save path, decrypt and write
- **导出后删除** — Export then remove from vault
- **删除** — Confirmation dialog, then delete from vault
- **打开** — Decrypt to temp, open with `Process.Start` (system default app)

### Toolbar Batch Operations

When checkbox(es) are checked:
- **导出按钮** → operates on all checked items → prompts for target folder (via `FolderBrowserDialog`) → exports all to that folder
- **删除按钮** → operates on all checked items → confirmation dialog showing count → batch delete

If no items are checked, fall back to single-selection behavior.

### Double-Click
- `ItemsList.MouseDoubleClick` → decrypt selected file to temp → `Process.Start` with system default handler

### Checked Items Tracking
- `GetCheckedItems()` helper method iterates `ItemsList.Items` and returns all `VaultFileRow` where `IsChecked == true`
- Select-all checkbox in header toggles all items
- On folder change or list refresh, clear all checkboxes

## 3. Export With Delete Option

### Single File Export (from context menu or toolbar)

The single-file export flow now shows a choice dialog:
- "仅导出" (Export only) — decrypt and save, keep file in vault
- "导出后删除" (Export then delete, default) — decrypt, save, then remove from vault

### Batch Export

When exporting multiple files:
- All exported to a single target folder
- Same choice: export only vs export then delete
- Default: export then delete

### Delete Confirmation

- Single delete: "确定从保险箱删除'{filename}'？"
- Batch delete: "确定从保险箱删除 {count} 个文件？"

## Implementation Order

1. Add `IsChecked` to `VaultFileRow`, update ListView XAML with checkbox column
2. Add context menu to ListView items
3. Implement async file operations (background decrypt/encrypt)
4. Implement batch export/delete toolbar logic
5. Implement export-with-delete choice
6. Implement double-click open
7. Fix video preview cache cleanup
8. Build and smoke test

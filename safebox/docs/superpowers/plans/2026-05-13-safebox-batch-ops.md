# 保险箱 批量操作与性能优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add async file operations (fix UI freezing), batch checkbox selection, right-click context menu, double-click open, and export-with-delete option.

**Architecture:** WPF .NET 10 desktop app, code-behind pattern. Offload heavy I/O to `Task.Run`, keep UI thread free. Add CheckBox column + ContextMenu to ListView. No changes to VaultService needed.

**Tech Stack:** WPF, .NET 10, C#

---

### Task 1: Add IsChecked and OpenFileTemp method for reuse

**Files:**
- Modify: `SafeBoxApp/MainWindow.xaml.cs`

- [ ] **Step 1: Add IsChecked property to VaultFileRow and OpenFileTemp helper**

In `MainWindow.xaml.cs`, at the `VaultFileRow` class (line 432), add `IsChecked`:

```csharp
private sealed class VaultFileRow(VaultItem item)
{
    public VaultItem Item { get; } = item;
    public string DisplayName => Item.DisplayName;
    public string SizeText => FormatSize(Item.Size);
    public string TypeText => item.ContentType.Split('/')[0];
    public string DateText => Item.ImportedAt.ToString("yyyy-MM-dd");
    public bool IsChecked { get; set; }

    private static string FormatSize(long bytes)
    {
        string[] units = ["B", "KB", "MB", "GB", "TB"];
        var size = (double)bytes;
        var unit = 0;
        while (size >= 1024 && unit < units.Length - 1)
        {
            size /= 1024;
            unit++;
        }
        return $"{size:0.#} {units[unit]}";
    }
}
```

Add `OpenFileTemp` helper method inside `MainWindow` class (before `// ===== HELPERS =====`):

```csharp
private void OpenFileWithDefaultApp(VaultItem item)
{
    if (_vault is null) return;
    try
    {
        var plain = _vault.ReadPlainBytes(item);
        var ext = Path.GetExtension(item.DisplayName);
        if (string.IsNullOrWhiteSpace(ext)) ext = ".tmp";
        var tmpPath = Path.Combine(Path.GetTempPath(), $"safebox-open-{Guid.NewGuid():N}{ext}");
        File.WriteAllBytes(tmpPath, plain);
        Array.Clear(plain);
        System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
        {
            FileName = tmpPath,
            UseShellExecute = true
        });
    }
    catch (Exception ex)
    {
        StatusText.Text = $"打开失败：{ex.Message}";
    }
}
```

- [ ] **Step 2: Build to verify**

Run: `dotnet build SafeBoxApp/SafeBoxApp.csproj`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add SafeBoxApp/MainWindow.xaml.cs
git commit -m "feat: add IsChecked to VaultFileRow and OpenFileTemp helper"
```

---

### Task 2: Update MainWindow.xaml — CheckBox column, ContextMenu, DoubleClick

**Files:**
- Modify: `SafeBoxApp/MainWindow.xaml:169-186` (the file list section)

- [ ] **Step 1: Replace the ListView section with updated XAML**

Replace lines 169-186 (the `<ListView x:Name="ItemsList" ...>` block) with:

```xml
                    <!-- File List -->
                    <ListView x:Name="ItemsList" Grid.Row="1"
                              SelectionChanged="ItemsList_SelectionChanged"
                              MouseDoubleClick="ItemsList_MouseDoubleClick"
                              Margin="20,12,20,12" Background="Transparent"
                              BorderThickness="0">
                        <ListView.View>
                            <GridView>
                                <GridViewColumn Width="32">
                                    <GridViewColumn.CellTemplate>
                                        <DataTemplate>
                                            <CheckBox IsChecked="{Binding IsChecked, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
                                                      VerticalAlignment="Center" HorizontalAlignment="Center" />
                                        </DataTemplate>
                                    </GridViewColumn.CellTemplate>
                                </GridViewColumn>
                                <GridViewColumn Header="名称" DisplayMemberBinding="{Binding DisplayName}"
                                                Width="220" />
                                <GridViewColumn Header="大小" DisplayMemberBinding="{Binding SizeText}"
                                                Width="80" />
                                <GridViewColumn Header="类型" DisplayMemberBinding="{Binding TypeText}"
                                                Width="80" />
                                <GridViewColumn Header="日期" DisplayMemberBinding="{Binding DateText}"
                                                Width="120" />
                            </GridView>
                        </ListView.View>
                        <ListView.ContextMenu>
                            <ContextMenu>
                                <MenuItem Header="📤 导出" Click="ContextMenu_Export_Click" />
                                <MenuItem Header="📤🗑 导出后删除" Click="ContextMenu_ExportDelete_Click" />
                                <Separator />
                                <MenuItem Header="🗑 删除" Click="ContextMenu_Delete_Click" />
                                <Separator />
                                <MenuItem Header="📂 打开" Click="ContextMenu_Open_Click" />
                            </ContextMenu>
                        </ListView.ContextMenu>
                    </ListView>
```

- [ ] **Step 2: Build to verify XAML compiles**

Run: `dotnet build SafeBoxApp/SafeBoxApp.csproj`
Expected: Build succeeds (warnings about missing event handlers are OK).

- [ ] **Step 3: Commit**

```bash
git add SafeBoxApp/MainWindow.xaml
git commit -m "feat: add CheckBox column, ContextMenu, and DoubleClick to file list"
```

---

### Task 3: Async preview and fixed video cache cleanup

**Files:**
- Modify: `SafeBoxApp/MainWindow.xaml.cs:293-393` (preview methods)

- [ ] **Step 1: Make ShowPreview async and fix video cache**

Replace the `ShowPreview` method (lines 295-347) and `WritePreviewCacheFile` (lines 349-363) and `ClearPreview` (lines 365-376) and `ClearPreviewCache` (lines 378-393):

```csharp
private async void ShowPreview(VaultItem item)
{
    if (_vault is null) return;

    ClearPreview();
    PreviewTitle.Text = item.DisplayName;

    var contentType = item.ContentType;
    var vault = _vault; // capture for closure

    try
    {
        if (contentType.StartsWith("image/", StringComparison.OrdinalIgnoreCase))
        {
            var plain = await Task.Run(() => vault.ReadPlainBytes(item));
            try
            {
                using var stream = new MemoryStream(plain);
                var bitmap = new BitmapImage();
                bitmap.BeginInit();
                bitmap.CacheOption = BitmapCacheOption.OnLoad;
                bitmap.StreamSource = stream;
                bitmap.EndInit();
                bitmap.Freeze();
                PreviewImage.Source = bitmap;
                PreviewImage.Visibility = Visibility.Visible;
            }
            finally
            {
                Array.Clear(plain);
            }
        }
        else if (contentType.StartsWith("video/", StringComparison.OrdinalIgnoreCase))
        {
            // Decrypt on background thread
            var plain = await Task.Run(() => vault.ReadPlainBytes(item));
            try
            {
                var cachePath = WritePreviewCacheFile(item, plain);
                PreviewVideo.Source = new Uri(cachePath);
                PreviewVideo.Visibility = Visibility.Visible;
                PreviewVideo.Play();
            }
            finally
            {
                Array.Clear(plain);
            }
        }
        else if (contentType == "text/plain")
        {
            var plain = await Task.Run(() => vault.ReadPlainBytes(item));
            try
            {
                PreviewText.Text = System.Text.Encoding.UTF8.GetString(plain);
                PreviewText.Visibility = Visibility.Visible;
            }
            finally
            {
                Array.Clear(plain);
            }
        }
        else
        {
            PreviewMessage.Text = "此类型暂不支持内置预览，可以导出后打开。";
            PreviewMessage.Visibility = Visibility.Visible;
        }
    }
    catch (Exception ex)
    {
        PreviewMessage.Text = ex.Message;
        PreviewMessage.Visibility = Visibility.Visible;
    }
}

private string WritePreviewCacheFile(VaultItem item, byte[] plain)
{
    // Don't delete existing cache — just clean parent directory once, then write
    Directory.CreateDirectory(_cacheRoot);
    var extension = Path.GetExtension(item.DisplayName);
    if (string.IsNullOrWhiteSpace(extension))
    {
        extension = ".preview";
    }

    var path = Path.Combine(_cacheRoot, $"{Guid.NewGuid():N}{extension.ToLowerInvariant()}");
    File.WriteAllBytes(path, plain);
    File.SetAttributes(path, FileAttributes.Hidden | FileAttributes.Temporary);
    return path;
}

private void ClearPreview()
{
    PreviewVideo.Stop();
    PreviewVideo.Source = null;
    PreviewVideo.Visibility = Visibility.Collapsed;
    PreviewImage.Source = null;
    PreviewImage.Visibility = Visibility.Collapsed;
    PreviewText.Text = "";
    PreviewText.Visibility = Visibility.Collapsed;
    PreviewMessage.Text = "选择一个文件预览";
    PreviewMessage.Visibility = Visibility.Visible;
    // Delete old cache files
    ClearPreviewCache();
}

private void ClearPreviewCache()
{
    try
    {
        if (Directory.Exists(_cacheRoot))
        {
            Directory.Delete(_cacheRoot, true);
        }
        Directory.CreateDirectory(_cacheRoot);
    }
    catch
    {
        // Preview cache cleanup is best effort.
    }
}
```

- [ ] **Step 2: Build to verify**

Run: `dotnet build SafeBoxApp/SafeBoxApp.csproj`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add SafeBoxApp/MainWindow.xaml.cs
git commit -m "fix: async preview decryption and safe video cache cleanup"
```

---

### Task 4: Async import and export

**Files:**
- Modify: `SafeBoxApp/MainWindow.xaml.cs:114-171` (ImportFiles_Click and ExportFile_Click)

- [ ] **Step 1: Make ImportFiles_Click async**

Replace `ImportFiles_Click` (lines 114-148):

```csharp
private async void ImportFiles_Click(object sender, RoutedEventArgs e)
{
    if (_vault is null) return;

    var dialog = new OpenFileDialog
    {
        Multiselect = true,
        Title = "选择要移动进保险箱的文件"
    };

    if (dialog.ShowDialog() != true) return;

    try
    {
        Mouse.OverrideCursor = System.Windows.Input.Cursors.Wait;
        var vault = _vault;
        var currentFolder = _currentFolder;
        var imported = 0;

        await Task.Run(() =>
        {
            foreach (var file in dialog.FileNames)
            {
                vault.ImportFile(file, currentFolder);
                imported++;
            }
        });

        RefreshAll();
        StatusText.Text = $"已导入 {imported} 个文件。源文件已从原位置删除。";
    }
    catch (Exception ex)
    {
        StatusText.Text = ex.Message;
        WinMessageBox.Show(ex.Message, "导入失败", MessageBoxButton.OK, MessageBoxImage.Warning);
    }
    finally
    {
        Mouse.OverrideCursor = null;
    }
}
```

- [ ] **Step 2: Replace single ExportFile_Click with batch-aware version**

Replace `ExportFile_Click` (lines 150-171):

```csharp
private async void ExportFile_Click(object sender, RoutedEventArgs e)
{
    if (_vault is null) return;

    var checkedItems = GetCheckedItems();
    if (checkedItems.Count > 0)
    {
        await BatchExportAsync(checkedItems);
        return;
    }

    // Fall back to single selected item
    if (ItemsList.SelectedItem is not VaultFileRow row) return;
    await SingleExportWithChoiceAsync(row.Item);
}

private async void DeleteFile_Click(object sender, RoutedEventArgs e)
{
    if (_vault is null) return;

    var checkedItems = GetCheckedItems();
    if (checkedItems.Count > 0)
    {
        if (WinMessageBox.Show($"确定从保险箱删除 {checkedItems.Count} 个文件？", "批量删除",
                MessageBoxButton.YesNo, MessageBoxImage.Warning) != MessageBoxResult.Yes) return;

        ClearPreview();
        foreach (var item in checkedItems)
        {
            _vault.DeleteItem(item);
        }
        RefreshAll();
        StatusText.Text = $"已删除 {checkedItems.Count} 个文件。";
        return;
    }

    // Fall back to single selected item
    if (ItemsList.SelectedItem is not VaultFileRow row) return;

    if (WinMessageBox.Show($"确定从保险箱删除"{row.Item.DisplayName}"？", "删除文件",
            MessageBoxButton.YesNo, MessageBoxImage.Warning) != MessageBoxResult.Yes) return;

    ClearPreview();
    _vault.DeleteItem(row.Item);
    RefreshAll();
    StatusText.Text = "文件已从保险箱删除。";
}

private async Task BatchExportAsync(IReadOnlyList<VaultItem> items)
{
    using var dialog = new Forms.FolderBrowserDialog
    {
        Description = "选择导出目标文件夹",
        UseDescriptionForTitle = true
    };

    if (dialog.ShowDialog() != Forms.DialogResult.OK) return;

    var deleteAfter = WinMessageBox.Show("导出后是否从保险箱删除这些文件？", "导出选项",
            MessageBoxButton.YesNo, MessageBoxImage.Question) == MessageBoxResult.Yes;

    try
    {
        Mouse.OverrideCursor = System.Windows.Input.Cursors.Wait;
        var vault = _vault!;
        var targetDir = dialog.SelectedPath;

        await Task.Run(() =>
        {
            foreach (var item in items)
            {
                var destPath = Path.Combine(targetDir, item.DisplayName);
                // Avoid overwriting: append (1), (2), etc.
                destPath = GetUniqueFilePath(destPath);
                vault.ExportFile(item, destPath);
            }
        });

        if (deleteAfter)
        {
            foreach (var item in items)
            {
                _vault.DeleteItem(item);
            }
        }

        RefreshAll();
        var action = deleteAfter ? "导出并删除" : "导出";
        StatusText.Text = $"已{action} {items.Count} 个文件到：{targetDir}";
    }
    catch (Exception ex)
    {
        StatusText.Text = ex.Message;
    }
    finally
    {
        Mouse.OverrideCursor = null;
    }
}

private async Task SingleExportWithChoiceAsync(VaultItem item)
{
    var deleteAfter = WinMessageBox.Show(
        $"导出"{item.DisplayName}"后是否从保险箱删除？\n\n是 = 导出后删除\n否 = 仅导出",
        "导出选项",
        MessageBoxButton.YesNo,
        MessageBoxImage.Question) == MessageBoxResult.Yes;

    var dialog = new SaveFileDialog
    {
        FileName = item.DisplayName,
        Title = "导出解密后的文件"
    };

    if (dialog.ShowDialog() != true) return;

    try
    {
        Mouse.OverrideCursor = System.Windows.Input.Cursors.Wait;
        var vault = _vault!;
        var destPath = dialog.FileName;

        await Task.Run(() => vault.ExportFile(item, destPath));

        if (deleteAfter)
        {
            _vault.DeleteItem(item);
            RefreshAll();
        }

        var action = deleteAfter ? "导出并删除" : "导出";
        StatusText.Text = $"已{action}到：{destPath}";
    }
    catch (Exception ex)
    {
        StatusText.Text = ex.Message;
    }
    finally
    {
        Mouse.OverrideCursor = null;
    }
}
```

- [ ] **Step 3: Build to verify**

Run: `dotnet build SafeBoxApp/SafeBoxApp.csproj`
Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add SafeBoxApp/MainWindow.xaml.cs
git commit -m "feat: async import/export, batch operations, export-with-delete choice"
```

---

### Task 5: Context menu handlers and double-click open

**Files:**
- Modify: `SafeBoxApp/MainWindow.xaml.cs` — add new event handlers

- [ ] **Step 1: Add context menu and double-click handler methods**

Add these methods inside the `// ===== VAULT EVENTS =====` region, after the existing `DeleteFile_Click`:

```csharp
private void ContextMenu_Export_Click(object sender, RoutedEventArgs e)
{
    if (_vault is null || ItemsList.SelectedItem is not VaultFileRow row) return;
    _ = SingleExportWithChoiceAsync(row.Item);
}

private void ContextMenu_ExportDelete_Click(object sender, RoutedEventArgs e)
{
    if (_vault is null || ItemsList.SelectedItem is not VaultFileRow row) return;

    var dialog = new SaveFileDialog
    {
        FileName = row.Item.DisplayName,
        Title = "导出解密后的文件"
    };

    if (dialog.ShowDialog() != true) return;

    try
    {
        Mouse.OverrideCursor = System.Windows.Input.Cursors.Wait;
        var vault = _vault;
        var item = row.Item;
        var destPath = dialog.FileName;

        System.Threading.Tasks.Task.Run(() => vault.ExportFile(item, destPath))
            .ContinueWith(_ =>
            {
                Dispatcher.Invoke(() =>
                {
                    vault.DeleteItem(item);
                    RefreshAll();
                    StatusText.Text = $"已导出并删除到：{destPath}";
                    Mouse.OverrideCursor = null;
                });
            });
    }
    catch (Exception ex)
    {
        StatusText.Text = ex.Message;
        Mouse.OverrideCursor = null;
    }
}

private void ContextMenu_Delete_Click(object sender, RoutedEventArgs e)
{
    if (_vault is null || ItemsList.SelectedItem is not VaultFileRow row) return;

    if (WinMessageBox.Show($"确定从保险箱删除"{row.Item.DisplayName}"？", "删除文件",
            MessageBoxButton.YesNo, MessageBoxImage.Warning) != MessageBoxResult.Yes) return;

    ClearPreview();
    _vault.DeleteItem(row.Item);
    RefreshAll();
    StatusText.Text = "文件已从保险箱删除。";
}

private void ContextMenu_Open_Click(object sender, RoutedEventArgs e)
{
    if (_vault is null || ItemsList.SelectedItem is not VaultFileRow row) return;
    OpenFileWithDefaultApp(row.Item);
}

private void ItemsList_MouseDoubleClick(object sender, System.Windows.Input.MouseButtonEventArgs e)
{
    if (_vault is null || ItemsList.SelectedItem is not VaultFileRow row) return;
    OpenFileWithDefaultApp(row.Item);
}
```

- [ ] **Step 2: Add GetCheckedItems and GetUniqueFilePath helpers**

Add to the `// ===== HELPERS =====` region:

```csharp
private IReadOnlyList<VaultItem> GetCheckedItems()
{
    var result = new List<VaultItem>();
    foreach (var item in ItemsList.Items)
    {
        if (item is VaultFileRow row && row.IsChecked)
        {
            result.Add(row.Item);
            row.IsChecked = false; // reset after read
        }
    }
    return result;
}

private static string GetUniqueFilePath(string path)
{
    if (!File.Exists(path)) return path;
    var dir = Path.GetDirectoryName(path) ?? "";
    var name = Path.GetFileNameWithoutExtension(path);
    var ext = Path.GetExtension(path);
    var counter = 1;
    string newPath;
    do
    {
        newPath = Path.Combine(dir, $"{name} ({counter}){ext}");
        counter++;
    } while (File.Exists(newPath));
    return newPath;
}
```

- [ ] **Step 3: Build to verify**

Run: `dotnet build SafeBoxApp/SafeBoxApp.csproj`
Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add SafeBoxApp/MainWindow.xaml.cs
git commit -m "feat: add context menu handlers, double-click open, and helper methods"
```

---

### Task 6: Build and smoke test

- [ ] **Step 1: Clean release build**

Run: `dotnet build SafeBoxApp/SafeBoxApp.csproj -c Release`
Expected: Build succeeds with no errors.

- [ ] **Step 2: Publish to dist**

Run: `dotnet publish SafeBoxApp/SafeBoxApp.csproj -c Release -o dist`
Expected: Publish succeeds.

- [ ] **Step 3: Smoke test checklist**

Launch `dist/保险箱.exe` and verify:
- [ ] Checkbox column visible in file list
- [ ] Check multiple files, click 导出 → batch export to folder
- [ ] Check multiple files, click 删除 → confirmation → batch delete
- [ ] Right-click single file → context menu with 4 items
- [ ] Context menu: 导出 → choose path → export with choice dialog
- [ ] Context menu: 导出后删除 → exports then removes from vault
- [ ] Context menu: 删除 → confirmation → delete
- [ ] Context menu: 打开 → opens with system default app
- [ ] Double-click file → opens with system default app
- [ ] Single export via toolbar → shows choice dialog (仅导出 / 导出后删除)
- [ ] Video preview → UI does not freeze, video plays
- [ ] Import large file(s) → UI stays responsive (cursor shows wait)
- [ ] Lock vault → preview cache cleaned up
- [ ] Folder list selection preserved on refresh

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: final build and smoke test verification"
```

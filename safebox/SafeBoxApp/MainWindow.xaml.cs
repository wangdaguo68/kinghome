using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media.Imaging;
using Forms = System.Windows.Forms;
using OpenFileDialog = Microsoft.Win32.OpenFileDialog;
using Path = System.IO.Path;
using SaveFileDialog = Microsoft.Win32.SaveFileDialog;
using WinMessageBox = System.Windows.MessageBox;

namespace SafeBoxApp;

public partial class MainWindow : Window
{
    private VaultService? _vault;
    private string _currentFolder = "";
    private readonly string _cacheRoot = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "SafeBox",
        "preview-cache");

    public MainWindow()
    {
        InitializeComponent();
        VaultPathBox.Text = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
            "保险箱");
        ClearPreviewCache();
    }

    // ===== LOGIN EVENTS =====

    private void BrowseVault_Click(object sender, RoutedEventArgs e)
    {
        using var dialog = new Forms.FolderBrowserDialog
        {
            Description = "选择或创建保险箱文件夹",
            UseDescriptionForTitle = true,
            SelectedPath = Directory.Exists(VaultPathBox.Text) ? VaultPathBox.Text : ""
        };

        if (dialog.ShowDialog() == Forms.DialogResult.OK)
        {
            VaultPathBox.Text = dialog.SelectedPath;
        }
    }

    private void CreateVault_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            LoginStatusText.Text = "";
            ValidatePassword(PasswordBox.Password);
            if (PasswordBox.Password != ConfirmPasswordBox.Password)
            {
                throw new InvalidOperationException("两次输入的密码不一致。");
            }

            var vault = new VaultService(RequireVaultPath());
            if (vault.Exists)
            {
                throw new InvalidOperationException("这个文件夹已经是保险箱，请直接解锁。");
            }

            var recoveryKey = vault.Create(PasswordBox.Password);
            _vault = vault;
            RecoveryOutputBox.Visibility = Visibility.Visible;
            RecoveryOutputBox.Text = $"恢复密钥：{recoveryKey}\r\n\r\n请离线保存。忘记主密码时，只有它能重新解锁保险箱。";
            ShowVault();
            WinMessageBox.Show($"保险箱已创建。\n\n恢复密钥：{recoveryKey}\n\n请立刻离线保存。", "恢复密钥", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            LoginStatusText.Text = ex.Message;
        }
    }

    private void UnlockVault_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            LoginStatusText.Text = "";
            var vault = new VaultService(RequireVaultPath());
            vault.UnlockWithPassword(PasswordBox.Password);
            _vault = vault;
            ShowVault();
        }
        catch (Exception ex)
        {
            LoginStatusText.Text = ex.Message;
        }
    }

    private void RecoverVault_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            LoginStatusText.Text = "";
            ValidatePassword(NewPasswordBox.Password);
            var vault = new VaultService(RequireVaultPath());
            vault.UnlockWithRecoveryKey(RecoveryKeyBox.Text, NewPasswordBox.Password);
            _vault = vault;
            ShowVault();
            WinMessageBox.Show("主密码已重设，保险箱已解锁。", "恢复完成", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            LoginStatusText.Text = ex.Message;
        }
    }

    // ===== VAULT EVENTS =====

    private void ImportFiles_Click(object sender, RoutedEventArgs e)
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
            System.Windows.Input.Mouse.OverrideCursor = System.Windows.Input.Cursors.Wait;
            var imported = 0;
            foreach (var file in dialog.FileNames)
            {
                _vault.ImportFile(file, _currentFolder);
                imported++;
            }

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
            System.Windows.Input.Mouse.OverrideCursor = null;
        }
    }

    private void ExportFile_Click(object sender, RoutedEventArgs e)
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
            _vault.ExportFile(row.Item, dialog.FileName);
            StatusText.Text = $"已导出到：{dialog.FileName}";
        }
        catch (Exception ex)
        {
            StatusText.Text = ex.Message;
        }
    }

    private void DeleteFile_Click(object sender, RoutedEventArgs e)
    {
        if (_vault is null || ItemsList.SelectedItem is not VaultFileRow row) return;

        if (WinMessageBox.Show($"确定从保险箱删除“{row.Item.DisplayName}”？", "删除文件",
                MessageBoxButton.YesNo, MessageBoxImage.Warning) != MessageBoxResult.Yes) return;

        ClearPreview();
        _vault.DeleteItem(row.Item);
        RefreshAll();
        StatusText.Text = "文件已从保险箱删除。";
    }

    private void LockVault_Click(object sender, RoutedEventArgs e)
    {
        LockAndReturnToLogin();
    }

    // ===== FOLDER EVENTS =====

    private void FolderList_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (FolderList.SelectedItem is string folderPath)
        {
            // "全部文件" is the root pseudo-folder
            _currentFolder = folderPath == "全部文件" ? "" : folderPath;
            BreadcrumbText.Text = string.IsNullOrEmpty(_currentFolder) ? "全部文件" : _currentFolder;
            RefreshFileList();
        }
    }

    private void NewFolder_Click(object sender, RoutedEventArgs e)
    {
        if (_vault is null) return;

        var dialog = new InputDialog("新建文件夹", "请输入文件夹名称：", this);
        if (dialog.ShowDialog() != true || string.IsNullOrWhiteSpace(dialog.Result))
        {
            return;
        }

        try
        {
            _vault.CreateFolder(dialog.Result);
            RefreshFolderList();
            StatusText.Text = $"文件夹“{dialog.Result}”已创建。";
        }
        catch (Exception ex)
        {
            StatusText.Text = ex.Message;
        }
    }

    private void ItemsList_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (ItemsList.SelectedItem is VaultFileRow row)
        {
            ShowPreview(row.Item);
        }
    }

    private void ItemsList_MouseDoubleClick(object sender, System.Windows.Input.MouseButtonEventArgs e)
    {
        // TODO: Implement in Task 5
    }

    private void ContextMenu_Export_Click(object sender, RoutedEventArgs e)
    {
        // TODO: Implement in Task 5
    }

    private void ContextMenu_ExportDelete_Click(object sender, RoutedEventArgs e)
    {
        // TODO: Implement in Task 5
    }

    private void ContextMenu_Delete_Click(object sender, RoutedEventArgs e)
    {
        // TODO: Implement in Task 5
    }

    private void ContextMenu_Open_Click(object sender, RoutedEventArgs e)
    {
        // TODO: Implement in Task 5
    }

    private void Window_Closing(object? sender, System.ComponentModel.CancelEventArgs e)
    {
        _vault?.Lock();
        ClearPreview();
        ClearPreviewCache();
    }

    // ===== UI STATE =====

    private void ShowVault()
    {
        LoginPanel.Visibility = Visibility.Collapsed;
        VaultPanel.Visibility = Visibility.Visible;
        _currentFolder = "";
        BreadcrumbText.Text = "全部文件";
        RefreshAll();
        StatusText.Text = $"已解锁：{_vault?.VaultDirectory}";
    }

    private void RefreshAll()
    {
        RefreshFolderList();
        RefreshFileList();
    }

    private void RefreshFolderList()
    {
        var previousFolder = _currentFolder;
        var allEntry = new List<string> { "全部文件" };
        if (_vault?.IsUnlocked == true)
        {
            allEntry.AddRange(_vault.Index.Folders.OrderBy(f => f));
        }

        FolderList.ItemsSource = allEntry;

        // Restore previous selection
        var displayName = string.IsNullOrEmpty(previousFolder) ? "全部文件" : previousFolder;
        var index = allEntry.IndexOf(displayName);
        FolderList.SelectedIndex = index >= 0 ? index : 0;
    }

    private void RefreshFileList()
    {
        if (_vault is null) return;

        var items = string.IsNullOrEmpty(_currentFolder)
            ? _vault.Index.Items
            : _vault.GetItemsInFolder(_currentFolder);

        var rows = items
            .OrderByDescending(i => i.ImportedAt)
            .Select(i => new VaultFileRow(i))
            .ToList();

        ItemsList.ItemsSource = rows;
        ItemCountText.Text = $"{rows.Count} 个项目";
    }

    // ===== PREVIEW =====

    private void ShowPreview(VaultItem item)
    {
        if (_vault is null) return;

        ClearPreview();
        PreviewTitle.Text = item.DisplayName;

        try
        {
            var plain = _vault.ReadPlainBytes(item);
            try
            {
                if (item.ContentType.StartsWith("image/", StringComparison.OrdinalIgnoreCase))
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
                else if (item.ContentType.StartsWith("video/", StringComparison.OrdinalIgnoreCase))
                {
                    var cachePath = WritePreviewCacheFile(item, plain);
                    PreviewVideo.Source = new Uri(cachePath);
                    PreviewVideo.Visibility = Visibility.Visible;
                    PreviewVideo.Play();
                }
                else if (item.ContentType == "text/plain")
                {
                    PreviewText.Text = System.Text.Encoding.UTF8.GetString(plain);
                    PreviewText.Visibility = Visibility.Visible;
                }
                else
                {
                    PreviewMessage.Text = "此类型暂不支持内置预览，可以导出后打开。";
                    PreviewMessage.Visibility = Visibility.Visible;
                }
            }
            finally
            {
                Array.Clear(plain);
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
        ClearPreviewCache();
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

    private void LockAndReturnToLogin()
    {
        _vault?.Lock();
        _vault = null;
        _currentFolder = "";
        ClearPreview();
        ClearPreviewCache();
        VaultPanel.Visibility = Visibility.Collapsed;
        LoginPanel.Visibility = Visibility.Visible;
        PasswordBox.Clear();
        ConfirmPasswordBox.Clear();
        NewPasswordBox.Clear();
        StatusText.Text = "";
        LoginStatusText.Text = "保险箱已锁定。";
    }

    private void OpenFileWithDefaultApp(VaultItem item)
    {
        if (_vault is null) return;
        try
        {
            var plain = _vault.ReadPlainBytes(item);
            var ext = Path.GetExtension(item.DisplayName);
            if (string.IsNullOrWhiteSpace(ext)) ext = ".tmp";
            Directory.CreateDirectory(_cacheRoot);
            var tmpPath = Path.Combine(_cacheRoot, $"safebox-open-{Guid.NewGuid():N}{ext}");
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

    // ===== HELPERS =====

    private string RequireVaultPath()
    {
        var path = VaultPathBox.Text.Trim();
        if (string.IsNullOrWhiteSpace(path))
        {
            throw new InvalidOperationException("请选择保险箱文件夹。");
        }

        return path;
    }

    private static void ValidatePassword(string password)
    {
        if (password.Length < 8)
        {
            throw new InvalidOperationException("主密码至少需要 8 个字符。");
        }
    }

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
}

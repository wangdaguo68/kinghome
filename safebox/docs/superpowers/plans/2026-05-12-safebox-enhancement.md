# 保险箱 Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add icon, MSI installer, wabi-sabi dark UI redesign, and folder management to the SafeBox WPF app.

**Architecture:** WPF .NET 10 desktop app with AES-GCM encryption. Model → VaultService → UI (code-behind). Folder support adds `FolderPath` to VaultItem and `Folders` to VaultIndex. UI rewritten in wabi-sabi dark aesthetic (deep brown `#1C1C1C`, warm gold `#D4A574`).

**Tech Stack:** WPF, .NET 10, WiX Toolset v4+, System.Drawing (icon generation)

---

### Task 1: Update Data Models for Folder Support

**Files:**
- Modify: `SafeBoxApp/Models.cs`

- [ ] **Step 1: Add FolderPath to VaultItem and Folders to VaultIndex**

Replace the entire content of `SafeBoxApp/Models.cs`:

```csharp
using System.Collections.ObjectModel;

namespace SafeBoxApp;

public sealed class VaultManifest
{
    public int Version { get; set; } = 1;
    public string VaultId { get; set; } = "";
    public string Kdf { get; set; } = "PBKDF2-SHA256";
    public int Iterations { get; set; } = 600_000;
    public string Salt { get; set; } = "";
    public string RecoverySalt { get; set; } = "";
    public string PasswordVerifier { get; set; } = "";
    public string RecoveryHash { get; set; } = "";
    public string EncryptedMasterKey { get; set; } = "";
    public string RecoveryEncryptedMasterKey { get; set; } = "";
    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public sealed class VaultIndex
{
    public ObservableCollection<VaultItem> Items { get; set; } = [];
    public ObservableCollection<string> Folders { get; set; } = [];
}

public sealed class VaultItem
{
    public string Id { get; set; } = "";
    public string DisplayName { get; set; } = "";
    public string ContentType { get; set; } = "application/octet-stream";
    public long Size { get; set; }
    public DateTimeOffset ImportedAt { get; set; } = DateTimeOffset.UtcNow;
    public string EncryptedFileName { get; set; } = "";
    public string FolderPath { get; set; } = "";
}
```

- [ ] **Step 2: Build to verify no compilation errors**

Run: `dotnet build SafeBoxApp/SafeBoxApp.csproj`
Expected: Build succeeds (VaultService will have some CS1061 on `FolderPath`, that's fine — we fix next).

- [ ] **Step 3: Commit**

```bash
git add SafeBoxApp/Models.cs
git commit -m "feat: add FolderPath to VaultItem and Folders to VaultIndex"
```

---

### Task 2: Add Folder Operations to VaultService

**Files:**
- Modify: `SafeBoxApp/VaultService.cs`

- [ ] **Step 1: Update ImportFile to accept optional folder path**

Replace the `ImportFile` method signature and the item creation line in `VaultService.cs`:

Find line 117-147 (the `ImportFile` method). Replace the method:

```csharp
public VaultItem ImportFile(string sourcePath, string folderPath = "")
{
    EnsureUnlocked();
    if (!File.Exists(sourcePath))
    {
        throw new FileNotFoundException("File to import was not found.", sourcePath);
    }

    var id = Guid.NewGuid().ToString("N");
    var encryptedName = $"{id}.bin";
    var targetPath = Path.Combine(_dataDir, encryptedName);
    var plain = File.ReadAllBytes(sourcePath);
    var item = new VaultItem
    {
        Id = id,
        DisplayName = Path.GetFileName(sourcePath),
        ContentType = GuessContentType(sourcePath),
        Size = plain.LongLength,
        ImportedAt = DateTimeOffset.UtcNow,
        EncryptedFileName = encryptedName,
        FolderPath = folderPath
    };

    var encrypted = _crypto.Encrypt(_masterKey!, plain, Encoding.UTF8.GetBytes(id));
    File.WriteAllBytes(targetPath, encrypted);
    Array.Clear(plain);

    DeleteSourceFile(sourcePath);
    _index.Items.Add(item);
    SaveIndex();
    return item;
}
```

- [ ] **Step 2: Add folder management methods to VaultService**

Add these methods to `VaultService.cs` before the `Lock()` method (around line 176):

```csharp
public void CreateFolder(string folderPath)
{
    EnsureUnlocked();
    if (string.IsNullOrWhiteSpace(folderPath))
    {
        throw new InvalidOperationException("Folder name cannot be empty.");
    }

    if (_index.Folders.Contains(folderPath, StringComparer.OrdinalIgnoreCase))
    {
        throw new InvalidOperationException("A folder with this name already exists.");
    }

    _index.Folders.Add(folderPath);
    SaveIndex();
}

public void RenameFolder(string oldPath, string newPath)
{
    EnsureUnlocked();
    if (!_index.Folders.Remove(oldPath))
    {
        throw new InvalidOperationException("Folder not found.");
    }

    _index.Folders.Add(newPath);

    foreach (var item in _index.Items.Where(i => i.FolderPath == oldPath || i.FolderPath.StartsWith(oldPath + "/")))
    {
        item.FolderPath = newPath + item.FolderPath[oldPath.Length..];
    }

    SaveIndex();
}

public void DeleteFolder(string folderPath)
{
    EnsureUnlocked();
    if (!_index.Folders.Remove(folderPath))
    {
        throw new InvalidOperationException("Folder not found.");
    }

    var itemsInFolder = _index.Items.Where(i => i.FolderPath == folderPath || i.FolderPath.StartsWith(folderPath + "/")).ToList();
    foreach (var item in itemsInFolder)
    {
        var filePath = Path.Combine(_dataDir, item.EncryptedFileName);
        if (File.Exists(filePath))
        {
            File.Delete(filePath);
        }

        _index.Items.Remove(item);
    }

    SaveIndex();
}

public void MoveItem(VaultItem item, string targetFolderPath)
{
    EnsureUnlocked();
    item.FolderPath = targetFolderPath;
    SaveIndex();
}

public IReadOnlyList<VaultItem> GetItemsInFolder(string folderPath)
{
    EnsureUnlocked();
    return _index.Items.Where(i => i.FolderPath == folderPath).ToList();
}
```

- [ ] **Step 3: Build to verify**

Run: `dotnet build SafeBoxApp/SafeBoxApp.csproj`
Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add SafeBoxApp/VaultService.cs
git commit -m "feat: add folder CRUD and file move operations to VaultService"
```

---

### Task 3: Rewrite App.xaml with Global Wabi-Sabi Dark Styles

**Files:**
- Modify: `SafeBoxApp/App.xaml`

- [ ] **Step 1: Replace App.xaml with global resource dictionary**

Replace the entire content of `SafeBoxApp/App.xaml`:

```xml
<Application x:Class="SafeBoxApp.App"
             xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
             StartupUri="MainWindow.xaml">
    <Application.Resources>
        <!-- Color Palette -->
        <SolidColorBrush x:Key="BgPrimary" Color="#1C1C1C" />
        <SolidColorBrush x:Key="BgSurface" Color="#252320" />
        <SolidColorBrush x:Key="BgElevated" Color="#29211A" />
        <SolidColorBrush x:Key="BorderSubtle" Color="#33302B" />
        <SolidColorBrush x:Key="BorderAccent" Color="#8B7355" />
        <SolidColorBrush x:Key="TextPrimary" Color="#E0D6CC" />
        <SolidColorBrush x:Key="TextSecondary" Color="#888888" />
        <SolidColorBrush x:Key="TextMuted" Color="#6B5B4F" />
        <SolidColorBrush x:Key="Accent" Color="#D4A574" />
        <SolidColorBrush x:Key="AccentDark" Color="#A0724A" />
        <SolidColorBrush x:Key="Danger" Color="#C06050" />
        <SolidColorBrush x:Key="DangerDark" Color="#8B3A3A" />

        <!-- Button Styles -->
        <Style x:Key="PrimaryButton" TargetType="Button">
            <Setter Property="Background">
                <Setter.Value>
                    <LinearGradientBrush StartPoint="0,0" EndPoint="0,1">
                        <GradientStop Color="#C4946A" Offset="0" />
                        <GradientStop Color="#A0724A" Offset="1" />
                    </LinearGradientBrush>
                </Setter.Value>
            </Setter>
            <Setter Property="Foreground" Value="#1C1C1C" />
            <Setter Property="BorderThickness" Value="0" />
            <Setter Property="FontSize" Value="13" />
            <Setter Property="FontWeight" Value="SemiBold" />
            <Setter Property="Padding" Value="24,10" />
            <Setter Property="Cursor" Value="Hand" />
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="Button">
                        <Border Background="{TemplateBinding Background}" CornerRadius="4"
                                Padding="{TemplateBinding Padding}">
                            <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center" />
                        </Border>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>

        <Style x:Key="SecondaryButton" TargetType="Button">
            <Setter Property="Background" Value="Transparent" />
            <Setter Property="Foreground" Value="#888888" />
            <Setter Property="BorderBrush" Value="#33302B" />
            <Setter Property="BorderThickness" Value="1" />
            <Setter Property="FontSize" Value="12" />
            <Setter Property="Padding" Value="16,8" />
            <Setter Property="Cursor" Value="Hand" />
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="Button">
                        <Border Background="{TemplateBinding Background}"
                                BorderBrush="{TemplateBinding BorderBrush}"
                                BorderThickness="{TemplateBinding BorderThickness}"
                                CornerRadius="4"
                                Padding="{TemplateBinding Padding}">
                            <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center" />
                        </Border>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>

        <Style x:Key="DangerButton" TargetType="Button">
            <Setter Property="Background" Value="#C06050" />
            <Setter Property="Foreground" Value="#FFFFFF" />
            <Setter Property="BorderThickness" Value="0" />
            <Setter Property="FontSize" Value="12" />
            <Setter Property="Padding" Value="16,8" />
            <Setter Property="Cursor" Value="Hand" />
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="Button">
                        <Border Background="{TemplateBinding Background}" CornerRadius="4"
                                Padding="{TemplateBinding Padding}">
                            <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center" />
                        </Border>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>

        <Style x:Key="GhostButton" TargetType="Button">
            <Setter Property="Background" Value="Transparent" />
            <Setter Property="Foreground" Value="#888888" />
            <Setter Property="BorderThickness" Value="0" />
            <Setter Property="FontSize" Value="12" />
            <Setter Property="Padding" Value="12,6" />
            <Setter Property="Cursor" Value="Hand" />
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="Button">
                        <Border Background="{TemplateBinding Background}" CornerRadius="4"
                                Padding="{TemplateBinding Padding}">
                            <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center" />
                        </Border>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>

        <!-- TextBox / PasswordBox Style -->
        <Style TargetType="TextBox">
            <Setter Property="Background" Value="#1C1C1C" />
            <Setter Property="Foreground" Value="#E0D6CC" />
            <Setter Property="BorderBrush" Value="#33302B" />
            <Setter Property="BorderThickness" Value="1" />
            <Setter Property="FontSize" Value="14" />
            <Setter Property="Padding" Value="14,10" />
            <Setter Property="CaretBrush" Value="#D4A574" />
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="TextBox">
                        <Border Background="{TemplateBinding Background}"
                                BorderBrush="{TemplateBinding BorderBrush}"
                                BorderThickness="{TemplateBinding BorderThickness}"
                                CornerRadius="4">
                            <ScrollViewer x:Name="PART_ContentHost" Margin="{TemplateBinding Padding}" />
                        </Border>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>

        <Style TargetType="PasswordBox">
            <Setter Property="Background" Value="#1C1C1C" />
            <Setter Property="Foreground" Value="#E0D6CC" />
            <Setter Property="BorderBrush" Value="#33302B" />
            <Setter Property="BorderThickness" Value="1" />
            <Setter Property="FontSize" Value="14" />
            <Setter Property="Padding" Value="14,10" />
            <Setter Property="CaretBrush" Value="#D4A574" />
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="PasswordBox">
                        <Border Background="{TemplateBinding Background}"
                                BorderBrush="{TemplateBinding BorderBrush}"
                                BorderThickness="{TemplateBinding BorderThickness}"
                                CornerRadius="4">
                            <ScrollViewer x:Name="PART_ContentHost" Margin="{TemplateBinding Padding}" />
                        </Border>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>

        <!-- ListView Style -->
        <Style x:Key="VaultListView" TargetType="ListView">
            <Setter Property="Background" Value="Transparent" />
            <Setter Property="BorderThickness" Value="0" />
            <Setter Property="Foreground" Value="#E0D6CC" />
        </Style>

        <!-- ListViewItem Style -->
        <Style TargetType="ListViewItem">
            <Setter Property="Background" Value="Transparent" />
            <Setter Property="Foreground" Value="#E0D6CC" />
            <Setter Property="BorderThickness" Value="0" />
            <Setter Property="Padding" Value="0" />
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="ListViewItem">
                        <Border x:Name="Border" Background="{TemplateBinding Background}"
                                BorderThickness="0" CornerRadius="6"
                                Padding="{TemplateBinding Padding}" Margin="0,1,0,1">
                            <GridViewRowPresenter />
                        </Border>
                        <ControlTemplate.Triggers>
                            <Trigger Property="IsMouseOver" Value="True">
                                <Setter TargetName="Border" Property="Background" Value="#252320" />
                            </Trigger>
                            <Trigger Property="IsSelected" Value="True">
                                <Setter TargetName="Border" Property="Background" Value="#2A2520" />
                            </Trigger>
                        </ControlTemplate.Triggers>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>

        <!-- ScrollBar Style for dark theme -->
        <Style TargetType="ScrollBar">
            <Setter Property="Background" Value="Transparent" />
            <Setter Property="Width" Value="6" />
        </Style>

        <Style TargetType="ScrollViewer">
            <Setter Property="Background" Value="Transparent" />
        </Style>
    </Application.Resources>
</Application>
```

- [ ] **Step 2: Build to verify styles compile**

Run: `dotnet build SafeBoxApp/SafeBoxApp.csproj`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add SafeBoxApp/App.xaml
git commit -m "feat: add wabi-sabi dark global styles to App.xaml"
```

---

### Task 4: Rewrite MainWindow.xaml — Login Page

**Files:**
- Modify: `SafeBoxApp/MainWindow.xaml`

- [ ] **Step 1: Replace MainWindow.xaml with complete wabi-sabi dark UI**

Replace the entire content of `SafeBoxApp/MainWindow.xaml`:

```xml
<Window x:Class="SafeBoxApp.MainWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="保险箱" Height="720" Width="1120" MinHeight="620" MinWidth="980"
        Background="#1C1C1C" Closing="Window_Closing"
        WindowStartupLocation="CenterScreen">
    <Grid>
        <!-- ===== LOGIN PANEL ===== -->
        <Grid x:Name="LoginPanel" VerticalAlignment="Center">
            <Border MaxWidth="380" Padding="0" Background="Transparent">
                <StackPanel>
                    <!-- Icon Area -->
                    <Border Width="64" Height="64" CornerRadius="16"
                            Background="#252320" BorderBrush="#33302B" BorderThickness="1"
                            HorizontalAlignment="Center" Margin="0,0,0,20">
                        <TextBlock Text="箱" FontSize="28" Foreground="#D4A574"
                                   HorizontalAlignment="Center" VerticalAlignment="Center" />
                    </Border>

                    <!-- Title -->
                    <TextBlock Text="保险箱" FontSize="28" FontWeight="Normal"
                               Foreground="#E0D6CC" TextAlignment="Center" Margin="0,0,0,4" />
                    <TextBlock Text="本地加密 · 安全存储" FontSize="12" Foreground="#6B5B4F"
                               TextAlignment="Center" Margin="0,0,0,28" />

                    <!-- Vault Path -->
                    <TextBlock Text="保险箱文件夹" FontSize="10" Foreground="#6B5B4F"
                               LetterSpacing="2" Margin="0,0,0,6" />
                    <DockPanel Margin="0,0,0,14">
                        <Button Content="选择" DockPanel.Dock="Right" Click="BrowseVault_Click"
                                Style="{StaticResource PrimaryButton}" FontSize="11" Padding="14,8" />
                        <TextBox x:Name="VaultPathBox" Margin="0,0,8,0" />
                    </DockPanel>

                    <!-- Password -->
                    <TextBlock Text="主密码" FontSize="10" Foreground="#6B5B4F"
                               LetterSpacing="2" Margin="0,0,0,6" />
                    <PasswordBox x:Name="PasswordBox" Margin="0,0,0,10" />

                    <!-- Confirm Password -->
                    <TextBlock Text="确认密码（创建时填写）" FontSize="10" Foreground="#6B5B4F"
                               LetterSpacing="2" Margin="0,0,0,6" />
                    <PasswordBox x:Name="ConfirmPasswordBox" Margin="0,0,0,20" />

                    <!-- Action Buttons -->
                    <StackPanel Orientation="Horizontal" HorizontalAlignment="Center" Margin="0,0,0,12">
                        <Button Content="创建保险箱" Click="CreateVault_Click"
                                Style="{StaticResource SecondaryButton}" Margin="0,0,8,0" />
                        <Button Content="解 锁" Click="UnlockVault_Click"
                                Style="{StaticResource PrimaryButton}" />
                    </StackPanel>

                    <!-- Recovery Section -->
                    <Expander Header="忘记密码？使用恢复密钥" Margin="0,8,0,0"
                              Foreground="#6B5B4F" FontSize="11" BorderThickness="0">
                        <StackPanel Margin="0,14,0,0">
                            <TextBlock Text="恢复密钥" FontSize="10" Foreground="#6B5B4F"
                                       LetterSpacing="2" Margin="0,0,0,6" />
                            <TextBox x:Name="RecoveryKeyBox" Margin="0,0,0,10" />
                            <TextBlock Text="新主密码" FontSize="10" Foreground="#6B5B4F"
                                       LetterSpacing="2" Margin="0,0,0,6" />
                            <PasswordBox x:Name="NewPasswordBox" Margin="0,0,0,12" />
                            <Button Content="用恢复密钥重设并解锁" Click="RecoverVault_Click"
                                    Style="{StaticResource SecondaryButton}" HorizontalAlignment="Left" />
                        </StackPanel>
                    </Expander>

                    <!-- Recovery Output -->
                    <TextBox x:Name="RecoveryOutputBox" Visibility="Collapsed" IsReadOnly="True"
                             TextWrapping="Wrap" Margin="0,14,0,0"
                             Background="#252320" Foreground="#D4A574" BorderThickness="0"
                             FontSize="11" />

                    <!-- Status -->
                    <TextBlock x:Name="LoginStatusText" Margin="0,16,0,0" Foreground="#C06050"
                               FontSize="11" TextWrapping="Wrap" TextAlignment="Center" />
                </StackPanel>
            </Border>
        </Grid>

        <!-- ===== VAULT PANEL (UNLOCKED) ===== -->
        <Grid x:Name="VaultPanel" Visibility="Collapsed">
            <Grid.RowDefinitions>
                <RowDefinition Height="48" />
                <RowDefinition Height="*" />
                <RowDefinition Height="28" />
            </Grid.RowDefinitions>

            <!-- Top Bar -->
            <Border Grid.Row="0" BorderBrush="#33302B" BorderThickness="0,0,0,1"
                    Background="#1C1C1C">
                <Grid Margin="16,0">
                    <StackPanel Orientation="Horizontal" VerticalAlignment="Center">
                        <TextBlock Text="保险箱" FontSize="11" Foreground="#8B7355"
                                   LetterSpacing="2" VerticalAlignment="Center" />
                        <TextBlock Text=" / " FontSize="11" Foreground="#3A3028"
                                   VerticalAlignment="Center" />
                        <TextBlock x:Name="BreadcrumbText" Text="全部文件" FontSize="11"
                                   Foreground="#D4A574" VerticalAlignment="Center" />
                    </StackPanel>

                    <Button Content="🔒 锁定" Click="LockVault_Click"
                            Style="{StaticResource SecondaryButton}"
                            FontSize="10" Padding="10,5"
                            HorizontalAlignment="Right" VerticalAlignment="Center" />
                </Grid>
            </Border>

            <!-- Main Content -->
            <Grid Grid.Row="1">
                <Grid.ColumnDefinitions>
                    <ColumnDefinition Width="200" />
                    <ColumnDefinition Width="*" />
                    <ColumnDefinition Width="Auto" />
                </Grid.ColumnDefinitions>

                <!-- Left Sidebar -->
                <Border Grid.Column="0" BorderBrush="#33302B" BorderThickness="0,0,1,0"
                        Background="#1C1C1C">
                    <Grid>
                        <Grid.RowDefinitions>
                            <RowDefinition Height="*" />
                            <RowDefinition Height="Auto" />
                        </Grid.RowDefinitions>

                        <ListView x:Name="FolderList" Grid.Row="0"
                                  Background="Transparent" BorderThickness="0"
                                  SelectionChanged="FolderList_SelectionChanged"
                                  Margin="0,12,0,0">
                            <ListView.ItemTemplate>
                                <DataTemplate>
                                    <TextBlock Text="{Binding}" FontSize="12" Foreground="#888"
                                               Padding="16,7" />
                                </DataTemplate>
                            </ListView.ItemTemplate>
                        </ListView>

                        <Button x:Name="NewFolderBtn" Grid.Row="1"
                                Content="+ 新建文件夹" Click="NewFolder_Click"
                                Style="{StaticResource GhostButton}"
                                FontSize="10" Foreground="#6B5B4F"
                                HorizontalAlignment="Stretch" Margin="8,0,8,12" />
                    </Grid>
                </Border>

                <!-- Center File Grid -->
                <Grid Grid.Column="1" Background="#1A1A1A">
                    <Grid.RowDefinitions>
                        <RowDefinition Height="Auto" />
                        <RowDefinition Height="*" />
                    </Grid.RowDefinitions>

                    <!-- Toolbar -->
                    <StackPanel Orientation="Horizontal" Margin="20,14,20,0" Grid.Row="0">
                        <Button Content="📥 导入并加密" Click="ImportFiles_Click"
                                Style="{StaticResource PrimaryButton}" FontSize="11" Padding="14,7" />
                        <Button Content="📤 导出" Click="ExportFile_Click"
                                Style="{StaticResource SecondaryButton}" FontSize="11"
                                Margin="8,0,0,0" />
                        <Button Content="🗑 删除" Click="DeleteFile_Click"
                                Style="{StaticResource SecondaryButton}" FontSize="11"
                                Margin="8,0,0,0" />
                        <TextBlock x:Name="ItemCountText" Text="0 个项目"
                                   FontSize="10" Foreground="#4A3F35"
                                   VerticalAlignment="Center" Margin="16,0,0,0" />
                    </StackPanel>

                    <!-- File List -->
                    <ListView x:Name="ItemsList" Grid.Row="1"
                              SelectionChanged="ItemsList_SelectionChanged"
                              Margin="20,12,20,12" Background="Transparent"
                              BorderThickness="0">
                        <ListView.View>
                            <GridView>
                                <GridViewColumn Header="名称" DisplayMemberBinding="{Binding DisplayName}"
                                                Width="240" />
                                <GridViewColumn Header="大小" DisplayMemberBinding="{Binding SizeText}"
                                                Width="80" />
                                <GridViewColumn Header="类型" DisplayMemberBinding="{Binding TypeText}"
                                                Width="80" />
                                <GridViewColumn Header="日期" DisplayMemberBinding="{Binding DateText}"
                                                Width="120" />
                            </GridView>
                        </ListView.View>
                    </ListView>
                </Grid>

                <!-- Right Preview Panel -->
                <Border Grid.Column="2" BorderBrush="#33302B" BorderThickness="1,0,0,0"
                        Background="#1C1C1C" Width="260">
                    <Grid Margin="14">
                        <Grid.RowDefinitions>
                            <RowDefinition Height="Auto" />
                            <RowDefinition Height="*" />
                        </Grid.RowDefinitions>

                        <TextBlock x:Name="PreviewTitle" Grid.Row="0" Text="选择文件预览"
                                   FontSize="10" Foreground="#6B5B4F" LetterSpacing="2"
                                   Margin="0,0,0,12" />

                        <Grid Grid.Row="1" Background="#252320" CornerRadius="6">
                            <Image x:Name="PreviewImage" Stretch="Uniform" Visibility="Collapsed" />
                            <MediaElement x:Name="PreviewVideo" LoadedBehavior="Manual"
                                          UnloadedBehavior="Manual" Stretch="Uniform"
                                          Visibility="Collapsed" />
                            <TextBox x:Name="PreviewText" Visibility="Collapsed" IsReadOnly="True"
                                     TextWrapping="Wrap" AcceptsReturn="True"
                                     VerticalScrollBarVisibility="Auto"
                                     Background="#252320" Foreground="#E0D6CC"
                                     BorderThickness="0" FontSize="12" />
                            <TextBlock x:Name="PreviewMessage" Text="选择一个文件预览"
                                       Foreground="#6B5B4F" FontSize="12"
                                       TextAlignment="Center" VerticalAlignment="Center"
                                       TextWrapping="Wrap" />
                        </Grid>
                    </Grid>
                </Border>
            </Grid>

            <!-- Bottom Status Bar -->
            <Border Grid.Row="2" BorderBrush="#33302B" BorderThickness="0,1,0,0"
                    Background="#1C1C1C">
                <TextBlock x:Name="StatusText" FontSize="9" Foreground="#4A3F35"
                           VerticalAlignment="Center" Margin="16,0" TextWrapping="Wrap" />
            </Border>
        </Grid>
    </Grid>
</Window>
```

- [ ] **Step 2: Build to verify XAML compiles**

Run: `dotnet build SafeBoxApp/SafeBoxApp.csproj`
Expected: Build succeeds. Warnings about event handlers that don't exist yet are OK.

- [ ] **Step 3: Commit**

```bash
git add SafeBoxApp/MainWindow.xaml
git commit -m "feat: rewrite MainWindow.xaml with wabi-sabi dark theme"
```

---

### Task 5: Update MainWindow.xaml.cs for New UI and Folders

**Files:**
- Modify: `SafeBoxApp/MainWindow.xaml.cs`

- [ ] **Step 1: Replace MainWindow.xaml.cs**

Replace the entire content of `SafeBoxApp/MainWindow.xaml.cs`:

```csharp
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
            Mouse.OverrideCursor = System.Windows.Input.Cursors.Wait;
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
            Mouse.OverrideCursor = null;
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

        if (WinMessageBox.Show($"确定从保险箱删除"{row.Item.DisplayName}"？", "删除文件",
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
            _currentFolder = folderPath;
            BreadcrumbText.Text = string.IsNullOrEmpty(folderPath) ? "全部文件" : folderPath;
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
            StatusText.Text = $"文件夹"{dialog.Result}"已创建。";
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
        var allEntry = new List<string> { "全部文件" };
        if (_vault?.IsUnlocked == true)
        {
            allEntry.AddRange(_vault.Index.Folders.OrderBy(f => f));
        }

        FolderList.ItemsSource = allEntry;
        FolderList.SelectedIndex = 0;
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
```

- [ ] **Step 2: Build — will fail due to missing InputDialog**

Run: `dotnet build SafeBoxApp/SafeBoxApp.csproj`
Expected: CS0246 error — `InputDialog` not found. This is expected, we create it next.

- [ ] **Step 3: Create InputDialog helper control**

Create file `SafeBoxApp/InputDialog.cs`:

```csharp
using System.Windows;
using System.Windows.Controls;

namespace SafeBoxApp;

public sealed class InputDialog : Window
{
    public string? Result { get; private set; }

    public InputDialog(string title, string prompt, Window owner)
    {
        Owner = owner;
        Title = title;
        Width = 340;
        Height = 200;
        ResizeMode = ResizeMode.NoResize;
        WindowStartupLocation = WindowStartupLocation.CenterOwner;
        WindowStyle = WindowStyle.None;
        AllowsTransparency = true;
        Background = System.Windows.Media.Brushes.Transparent;

        var mainBorder = new Border
        {
            Background = (System.Windows.Media.Brush)FindResource("BgElevated"),
            BorderBrush = (System.Windows.Media.Brush)FindResource("BorderAccent"),
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(8),
            Margin = new Thickness(1)
        };

        var grid = new Grid();
        grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        grid.Margin = new Thickness(20);
        grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

        var titleBlock = new TextBlock
        {
            Text = prompt,
            Foreground = (System.Windows.Media.Brush)FindResource("TextPrimary"),
            FontSize = 13,
            Margin = new Thickness(0, 0, 0, 14)
        };
        Grid.SetRow(titleBlock, 0);
        grid.Children.Add(titleBlock);

        var textBox = new TextBox
        {
            Margin = new Thickness(0, 0, 0, 16)
        };
        Grid.SetRow(textBox, 1);
        grid.Children.Add(textBox);

        var buttons = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right };
        var cancelBtn = new Button
        {
            Content = "取消",
            Style = (Style)FindResource("SecondaryButton"),
            Margin = new Thickness(0, 0, 8, 0)
        };
        cancelBtn.Click += (_, _) => { Result = null; DialogResult = false; Close(); };
        buttons.Children.Add(cancelBtn);

        var okBtn = new Button
        {
            Content = "创建",
            Style = (Style)FindResource("PrimaryButton")
        };
        okBtn.Click += (_, _) => { Result = textBox.Text.Trim(); DialogResult = true; Close(); };
        buttons.Children.Add(okBtn);

        Grid.SetRow(buttons, 2);
        grid.Children.Add(buttons);

        mainBorder.Child = grid;
        Content = mainBorder;
    }
}
```

- [ ] **Step 4: Build to verify all files compile**

Run: `dotnet build SafeBoxApp/SafeBoxApp.csproj`
Expected: Build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
git add SafeBoxApp/MainWindow.xaml.cs SafeBoxApp/InputDialog.cs
git commit -m "feat: update code-behind for new UI, folders, and InputDialog"
```

---

### Task 6: Add Vault Index Public Accessor

**Files:**
- Modify: `SafeBoxApp/VaultService.cs`

The code-behind needs to access `_vault.Index` to read the Folders list. Add a public property.

- [ ] **Step 1: Add public Index property to VaultService**

In `VaultService.cs`, add after the `IsUnlocked` property (around line 35):

```csharp
public VaultIndex Index => _index;
```

- [ ] **Step 2: Build**

Run: `dotnet build SafeBoxApp/SafeBoxApp.csproj`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add SafeBoxApp/VaultService.cs
git commit -m "feat: expose VaultIndex publicly for UI binding"
```

---

### Task 7: Build and Sanity Test

- [ ] **Step 1: Full build**

Run: `dotnet build SafeBoxApp/SafeBoxApp.csproj -c Release`
Expected: Build succeeds.

- [ ] **Step 2: Publish to dist**

Run: `dotnet publish SafeBoxApp/SafeBoxApp.csproj -c Release -o dist`
Expected: Publish succeeds, `dist/保险箱.exe` created.

- [ ] **Step 3: Smoke test — launch app, verify UI loads**

Run: `start dist/保险箱.exe`
Expected: Window opens with dark wabi-sabi login page. Verify:
- Dark background visible
- Password fields styled correctly
- No crash on launch

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: build and publish to dist"
```

---

### Task 8: Generate Application Icon

**Files:**
- Create: `SafeBoxApp/icon.ico`

Use a small C# helper to generate the .ico file programmatically.

- [ ] **Step 1: Create icon generation script**

Create file `generate-icon.csx` (C# script):

```csharp
// Run with: dotnet-script generate-icon.csx
// Or: create a simple console project to run this

using System.Drawing;
using System.Drawing.Imaging;
using System.Drawing.Drawing2D;
using System.Runtime.InteropServices;

var sizes = new[] { 16, 32, 48, 256 };
var iconDir = new List<byte[]>();

foreach (var size in sizes)
{
    using var bmp = new Bitmap(size, size);
    using var g = Graphics.FromImage(bmp);
    g.SmoothingMode = SmoothingMode.AntiAlias;
    g.Clear(Color.FromArgb(28, 28, 28));

    // Rounded rect background
    using var bgBrush = new SolidBrush(Color.FromArgb(37, 35, 32));
    var rect = new Rectangle(size / 6, size / 6, size - size / 3, size - size / 3);
    g.FillEllipse(bgBrush, size / 4, size / 4, size / 2, size / 2);

    // Gold border
    using var borderPen = new Pen(Color.FromArgb(212, 165, 116), Math.Max(1, size / 16f));
    g.DrawEllipse(borderPen, size / 4f, size / 4f, size / 2f, size / 2f);

    // "箱" character
    var fontSize = size * 0.45f;
    using var font = new Font("Microsoft YaHei", fontSize, FontStyle.Bold, GraphicsUnit.Pixel);
    using var textBrush = new SolidBrush(Color.FromArgb(212, 165, 116));
    var textSize = g.MeasureString("箱", font);
    g.DrawString("箱", font, textBrush, (size - textSize.Width) / 2, (size - textSize.Height) / 2);

    using var ms = new MemoryStream();
    bmp.Save(ms, ImageFormat.Png);
    iconDir.Add(ms.ToArray());
}

// Build .ico file
using var fs = new FileStream("SafeBoxApp/icon.ico", FileMode.Create);
using var writer = new BinaryWriter(fs);

// ICO header
writer.Write((short)0);   // reserved
writer.Write((short)1);   // icon
writer.Write((short)sizes.Length); // count

var imageDataOffset = 6 + 16 * sizes.Length;
for (int i = 0; i < sizes.Length; i++)
{
    var data = iconDir[i];
    writer.Write((byte)sizes[i]); // width
    writer.Write((byte)sizes[i]); // height
    writer.Write((byte)0);        // palette
    writer.Write((byte)0);        // reserved
    writer.Write((short)1);       // color planes
    writer.Write((short)32);      // bpp
    writer.Write(data.Length);    // size
    writer.Write(imageDataOffset);
    imageDataOffset += data.Length;
}

foreach (var data in iconDir)
{
    writer.Write(data);
}

Console.WriteLine("icon.ico created.");
```

Run with:
```bash
dotnet script generate-icon.csx
```

If `dotnet-script` is not available, use this alternative command:

```bash
pwsh -Command "
Add-Type -AssemblyName System.Drawing
\$bmp = New-Object System.Drawing.Bitmap(256,256)
\$g = [System.Drawing.Graphics]::FromImage(\$bmp)
\$g.SmoothingMode = 'AntiAlias'
\$g.Clear([System.Drawing.Color]::FromArgb(28,28,28))
\$g.FillEllipse((New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(37,35,32))), 32, 32, 192, 192)
\$g.DrawEllipse((New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(212,165,116), 8)), 32, 32, 192, 192)
\$font = New-Object System.Drawing.Font('Microsoft YaHei', 96, [System.Drawing.FontStyle]::Bold)
\$g.DrawString('箱', \$font, (New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(212,165,116))), 64, 60)
\$bmp.Save('SafeBoxApp/icon.ico', 'Icon')
\$g.Dispose()
\$bmp.Dispose()
Write-Output 'icon.ico created'
"
```

- [ ] **Step 2: Add icon to .csproj**

Add this line inside the `<PropertyGroup>` in `SafeBoxApp/SafeBoxApp.csproj`:

```xml
<ApplicationIcon>icon.ico</ApplicationIcon>
```

- [ ] **Step 3: Build with icon**

Run: `dotnet build SafeBoxApp/SafeBoxApp.csproj`
Expected: Build succeeds, .exe has icon embedded.

- [ ] **Step 4: Commit**

```bash
git add SafeBoxApp/icon.ico SafeBoxApp/SafeBoxApp.csproj
git commit -m "feat: add application icon"
```

---

### Task 9: Create WiX Installer Project

**Files:**
- Create: `installer/保险箱.wxs`
- Create: `installer/build.cmd`

- [ ] **Step 1: Install WiX Toolset**

Run: `dotnet tool install --global wix`
If that fails, download from: https://github.com/wixtoolset/wix/releases and install manually. Then:

```bash
dotnet new install WixToolset.Sdk
```

- [ ] **Step 2: Create WiX project file**

Create `installer/installer.wixproj`:

```xml
<Project Sdk="WixToolset.Sdk">
  <PropertyGroup>
    <OutputType>Msi</OutputType>
    <OutputName>保险箱安装包</OutputName>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="WixToolset.UI.wixext" Version="5.0.0" />
  </ItemGroup>
</Project>
```

- [ ] **Step 3: Create WiX source file**

Create `installer/Package.wxs`:

```xml
<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs"
     xmlns:ui="http://wixtoolset.org/schemas/v4/wxs/ui">

  <Package Name="保险箱" Manufacturer="SafeBox"
           Version="1.0.0" UpgradeCode="12345678-1234-1234-1234-123456789ABC"
           Language="2052" Codepage="936">
    <MediaTemplate EmbedCab="yes" />

    <StandardDirectory Id="ProgramFiles6432Folder">
      <Directory Id="INSTALLFOLDER" Name="保险箱" />
    </StandardDirectory>

    <StandardDirectory Id="ProgramMenuFolder">
      <Directory Id="StartMenuFolder" Name="保险箱" />
    </StandardDirectory>

    <StandardDirectory Id="DesktopFolder" />

    <ComponentGroup Id="AppComponents" Directory="INSTALLFOLDER">
      <Files Include="..\dist\**" />
    </ComponentGroup>

    <Component Id="StartMenuShortcut" Directory="StartMenuFolder">
      <Shortcut Id="StartMenuLink" Name="保险箱"
                Target="[INSTALLFOLDER]保险箱.exe"
                WorkingDirectory="INSTALLFOLDER" />
      <RegistryValue Root="HKCU" Key="Software\SafeBox\保险箱"
                     Name="installed" Type="integer" Value="1" KeyPath="yes" />
    </Component>

    <Component Id="DesktopShortcut" Directory="DesktopFolder">
      <Shortcut Id="DesktopLink" Name="保险箱"
                Target="[INSTALLFOLDER]保险箱.exe"
                WorkingDirectory="INSTALLFOLDER" />
      <Condition>INSTALLDESKTOPSHORTCUT</Condition>
    </Component>

    <Feature Id="Main">
      <ComponentGroupRef Id="AppComponents" />
      <ComponentRef Id="StartMenuShortcut" />
      <ComponentRef Id="DesktopShortcut" />
    </Feature>

    <ui:WixUI Id="WixUI_InstallDir" />
    <WixVariable Id="WixUILicenseRtf" Value="license.rtf" />
  </Package>
</Wix>
```

- [ ] **Step 4: Build MSI**

```bash
cd installer
dotnet build -c Release
```

Expected: `installer/bin/Release/保险箱安装包.msi` created.

- [ ] **Step 5: Copy MSI to dist**

```bash
cp installer/bin/Release/*.msi dist/
```

- [ ] **Step 6: Commit**

```bash
git add installer/
git commit -m "feat: add WiX installer project"
```

---

### Task 10: Final Build and Verification

- [ ] **Step 1: Clean build from scratch**

```bash
dotnet clean SafeBoxApp/SafeBoxApp.csproj
dotnet publish SafeBoxApp/SafeBoxApp.csproj -c Release -o dist
```

- [ ] **Step 2: Verify output files**

Run: `ls dist/`
Expected:
- `保险箱.exe` (with embedded icon)
- All required .dll files

- [ ] **Step 3: Verify .exe has icon**

Run: `pwsh -Command "(Get-Item dist/保险箱.exe).VersionInfo"`
Expected: Shows file info.

- [ ] **Step 4: Launch smoke test**

Run: `start dist/保险箱.exe`
Verify:
- Login page with dark wabi-sabi design
- Create vault → unlock → see file grid
- Create folder → see in sidebar
- Import file → see in list
- Preview working
- Lock and re-login works

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: final build and verification"
```

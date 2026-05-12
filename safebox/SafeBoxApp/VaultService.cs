using System.Buffers.Binary;
using System.Collections.ObjectModel;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace SafeBoxApp;

public sealed class VaultService
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        WriteIndented = true
    };

    private readonly CryptoService _crypto = new();
    private readonly string _manifestPath;
    private readonly string _indexPath;
    private readonly string _dataDir;

    private byte[]? _masterKey;
    private VaultManifest? _manifest;
    private VaultIndex _index = new();

    public VaultService(string vaultDirectory)
    {
        VaultDirectory = vaultDirectory;
        _manifestPath = Path.Combine(vaultDirectory, "manifest.json");
        _indexPath = Path.Combine(vaultDirectory, "index.bin");
        _dataDir = Path.Combine(vaultDirectory, "data");
    }

    public string VaultDirectory { get; }
    public bool Exists => File.Exists(_manifestPath);
    public bool IsUnlocked => _masterKey is not null;
    public VaultIndex Index => _index;
    public ObservableCollection<VaultItem> Items => _index.Items;

    public string Create(string password)
    {
        Directory.CreateDirectory(VaultDirectory);
        Directory.CreateDirectory(_dataDir);

        var salt = _crypto.CreateSalt();
        var recoverySalt = _crypto.CreateSalt();
        var recoveryKey = _crypto.CreateRecoveryKey();
        var passwordKey = _crypto.DeriveKeyFromPassword(password, salt, 600_000);
        var recoveryWrapKey = _crypto.DeriveKeyFromRecoveryKey(recoveryKey, recoverySalt, 600_000);
        var masterKey = RandomNumberGenerator.GetBytes(CryptoService.KeySize);
        _manifest = new VaultManifest
        {
            VaultId = _crypto.CreateVaultId(),
            Salt = Convert.ToBase64String(salt),
            RecoverySalt = Convert.ToBase64String(recoverySalt),
            PasswordVerifier = _crypto.CreatePasswordVerifier(passwordKey),
            RecoveryHash = _crypto.HashRecoveryKey(recoveryKey, recoverySalt),
            EncryptedMasterKey = Convert.ToBase64String(_crypto.Encrypt(passwordKey, masterKey, Encoding.UTF8.GetBytes("master-key:password"))),
            RecoveryEncryptedMasterKey = Convert.ToBase64String(_crypto.Encrypt(recoveryWrapKey, masterKey, Encoding.UTF8.GetBytes("master-key:recovery")))
        };
        _masterKey = masterKey;
        _index = new VaultIndex();

        SaveManifest();
        SaveIndex();
        Array.Clear(passwordKey);
        Array.Clear(recoveryWrapKey);
        return recoveryKey;
    }

    public void UnlockWithPassword(string password)
    {
        var manifest = LoadManifest();
        var salt = Convert.FromBase64String(manifest.Salt);
        var passwordKey = _crypto.DeriveKeyFromPassword(password, salt, manifest.Iterations);
        if (!_crypto.VerifyPassword(passwordKey, manifest.PasswordVerifier))
        {
            throw new InvalidOperationException("Password is incorrect.");
        }

        _manifest = manifest;
        _masterKey = _crypto.Decrypt(
            passwordKey,
            Convert.FromBase64String(manifest.EncryptedMasterKey),
            Encoding.UTF8.GetBytes("master-key:password"));
        Array.Clear(passwordKey);
        LoadIndex();
    }

    public void UnlockWithRecoveryKey(string recoveryKey, string newPassword)
    {
        var manifest = LoadManifest();
        var salt = Convert.FromBase64String(manifest.Salt);
        var recoverySalt = Convert.FromBase64String(manifest.RecoverySalt);
        var expected = manifest.RecoveryHash;
        var actual = _crypto.HashRecoveryKey(recoveryKey, recoverySalt);
        if (!CryptographicCompare(expected, actual))
        {
            throw new InvalidOperationException("Recovery key is incorrect.");
        }

        var recoveryWrapKey = _crypto.DeriveKeyFromRecoveryKey(recoveryKey, recoverySalt, manifest.Iterations);
        var newPasswordKey = _crypto.DeriveKeyFromPassword(newPassword, salt, manifest.Iterations);
        var masterKey = _crypto.Decrypt(
            recoveryWrapKey,
            Convert.FromBase64String(manifest.RecoveryEncryptedMasterKey),
            Encoding.UTF8.GetBytes("master-key:recovery"));
        manifest.PasswordVerifier = _crypto.CreatePasswordVerifier(newPasswordKey);
        manifest.EncryptedMasterKey = Convert.ToBase64String(_crypto.Encrypt(newPasswordKey, masterKey, Encoding.UTF8.GetBytes("master-key:password")));
        _manifest = manifest;
        _masterKey = masterKey;
        LoadIndex();
        SaveManifest();
        SaveIndex();
        Array.Clear(recoveryWrapKey);
        Array.Clear(newPasswordKey);
    }

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
        var fileInfo = new FileInfo(sourcePath);
        var item = new VaultItem
        {
            Id = id,
            DisplayName = Path.GetFileName(sourcePath),
            ContentType = GuessContentType(sourcePath),
            Size = fileInfo.Length,
            ImportedAt = DateTimeOffset.UtcNow,
            EncryptedFileName = encryptedName,
            FolderPath = folderPath
        };

        _crypto.EncryptChunked(_masterKey!, sourcePath, targetPath, Encoding.UTF8.GetBytes(id));

        DeleteSourceFile(sourcePath);
        _index.Items.Add(item);
        SaveIndex();
        return item;
    }

    public byte[] ReadPlainBytes(VaultItem item)
    {
        EnsureUnlocked();
        var path = Path.Combine(_dataDir, item.EncryptedFileName);
        // Try new chunked format first, fall back to legacy single-chunk format
        var payload = File.ReadAllBytes(path);
        var version = BinaryPrimitives.ReadInt32LittleEndian(payload.AsSpan(0, 4));
        if (version == 2)
        {
            Array.Clear(payload);
            return _crypto.DecryptChunked(_masterKey!, path, Encoding.UTF8.GetBytes(item.Id));
        }
        return _crypto.Decrypt(_masterKey!, payload, Encoding.UTF8.GetBytes(item.Id));
    }

    public void ExportFile(VaultItem item, string destinationPath)
    {
        var plain = ReadPlainBytes(item);
        File.WriteAllBytes(destinationPath, plain);
        Array.Clear(plain);
    }

    public void DeleteItem(VaultItem item)
    {
        EnsureUnlocked();
        var path = Path.Combine(_dataDir, item.EncryptedFileName);
        if (File.Exists(path))
        {
            File.Delete(path);
        }

        _index.Items.Remove(item);
        SaveIndex();
    }

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
        if (string.IsNullOrWhiteSpace(newPath))
            throw new InvalidOperationException("Folder name cannot be empty.");

        if (_index.Folders.Contains(newPath, StringComparer.OrdinalIgnoreCase))
            throw new InvalidOperationException("A folder with this name already exists.");

        var existingFolder = _index.Folders.FirstOrDefault(f => f.Equals(oldPath, StringComparison.OrdinalIgnoreCase));
        if (existingFolder is null || !_index.Folders.Remove(existingFolder))
            throw new InvalidOperationException("Folder not found.");

        _index.Folders.Add(newPath);

        foreach (var item in _index.Items.Where(i => i.FolderPath == oldPath || i.FolderPath.StartsWith(oldPath + "/")).ToList())
        {
            item.FolderPath = newPath + item.FolderPath[oldPath.Length..];
        }

        var childFolders = _index.Folders.Where(f => f.StartsWith(oldPath + "/")).ToList();
        foreach (var child in childFolders)
        {
            _index.Folders.Remove(child);
            _index.Folders.Add(newPath + child[oldPath.Length..]);
        }

        SaveIndex();
    }

    public void DeleteFolder(string folderPath)
    {
        EnsureUnlocked();
        var existingFolder = _index.Folders.FirstOrDefault(f => f.Equals(folderPath, StringComparison.OrdinalIgnoreCase));
        if (existingFolder is null || !_index.Folders.Remove(existingFolder))
            throw new InvalidOperationException("Folder not found.");

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

        var childFolders = _index.Folders.Where(f => f.StartsWith(folderPath + "/")).ToList();
        foreach (var child in childFolders)
        {
            _index.Folders.Remove(child);
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

    public void Lock()
    {
        if (_masterKey is not null)
        {
            Array.Clear(_masterKey);
        }

        _masterKey = null;
        _manifest = null;
        _index = new VaultIndex();
    }

    private void LoadIndex()
    {
        EnsureUnlocked();
        if (!File.Exists(_indexPath))
        {
            _index = new VaultIndex();
            return;
        }

        var plain = _crypto.Decrypt(_masterKey!, File.ReadAllBytes(_indexPath), Encoding.UTF8.GetBytes("index"));
        try
        {
            _index = JsonSerializer.Deserialize<VaultIndex>(plain, JsonOptions) ?? new VaultIndex();
        }
        finally
        {
            Array.Clear(plain);
        }
    }

    private void SaveIndex()
    {
        EnsureUnlocked();
        Directory.CreateDirectory(_dataDir);
        var plain = JsonSerializer.SerializeToUtf8Bytes(_index, JsonOptions);
        try
        {
            var encrypted = _crypto.Encrypt(_masterKey!, plain, Encoding.UTF8.GetBytes("index"));
            File.WriteAllBytes(_indexPath, encrypted);
        }
        finally
        {
            Array.Clear(plain);
        }
    }

    private VaultManifest LoadManifest()
    {
        if (!File.Exists(_manifestPath))
        {
            throw new InvalidOperationException("Current directory is not a vault.");
        }

        return JsonSerializer.Deserialize<VaultManifest>(File.ReadAllText(_manifestPath), JsonOptions)
               ?? throw new InvalidOperationException("Vault manifest is damaged.");
    }

    private void SaveManifest()
    {
        if (_manifest is null)
        {
            throw new InvalidOperationException("Vault manifest is not loaded.");
        }

        File.WriteAllText(_manifestPath, JsonSerializer.Serialize(_manifest, JsonOptions));
    }

    private void EnsureUnlocked()
    {
        if (_masterKey is null)
        {
            throw new InvalidOperationException("Vault is locked.");
        }
    }

    private static void DeleteSourceFile(string sourcePath)
    {
        try
        {
            File.Delete(sourcePath);
        }
        catch (Exception ex)
        {
            throw new IOException("File was encrypted into the vault, but deleting the source file failed. Delete it manually.", ex);
        }
    }

    private static string GuessContentType(string path)
    {
        return Path.GetExtension(path).ToLowerInvariant() switch
        {
            ".jpg" or ".jpeg" => "image/jpeg",
            ".png" => "image/png",
            ".gif" => "image/gif",
            ".bmp" => "image/bmp",
            ".webp" => "image/webp",
            ".mp4" => "video/mp4",
            ".mov" => "video/quicktime",
            ".avi" => "video/x-msvideo",
            ".mkv" => "video/x-matroska",
            ".txt" or ".md" or ".csv" or ".log" => "text/plain",
            ".pdf" => "application/pdf",
            _ => "application/octet-stream"
        };
    }

    private static bool CryptographicCompare(string left, string right)
    {
        var leftBytes = Encoding.UTF8.GetBytes(left);
        var rightBytes = Encoding.UTF8.GetBytes(right);
        return System.Security.Cryptography.CryptographicOperations.FixedTimeEquals(leftBytes, rightBytes);
    }
}

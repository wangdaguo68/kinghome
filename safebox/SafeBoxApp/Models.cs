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

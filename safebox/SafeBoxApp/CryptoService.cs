using System.Buffers.Binary;
using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace SafeBoxApp;

public sealed class CryptoService
{
    public const int KeySize = 32;
    private const int NonceSize = 12;
    private const int TagSize = 16;

    public byte[] CreateSalt() => RandomNumberGenerator.GetBytes(32);

    public string CreateVaultId() => Convert.ToHexString(RandomNumberGenerator.GetBytes(16)).ToLowerInvariant();

    public string CreateRecoveryKey()
    {
        var bytes = RandomNumberGenerator.GetBytes(24);
        return string.Join("-", Convert.ToHexString(bytes).Chunk(6).Select(c => new string(c))).ToLowerInvariant();
    }

    public byte[] DeriveKeyFromPassword(string password, byte[] salt, int iterations)
    {
        return Rfc2898DeriveBytes.Pbkdf2(
            password,
            salt,
            iterations,
            HashAlgorithmName.SHA256,
            KeySize);
    }

    public byte[] DeriveKeyFromRecoveryKey(string recoveryKey, byte[] salt, int iterations)
    {
        return DeriveKeyFromPassword(NormalizeRecoveryKey(recoveryKey), salt, iterations);
    }

    public string HashRecoveryKey(string recoveryKey, byte[] salt)
    {
        using var hmac = new HMACSHA256(salt);
        return Convert.ToBase64String(hmac.ComputeHash(Encoding.UTF8.GetBytes(NormalizeRecoveryKey(recoveryKey))));
    }

    public string CreatePasswordVerifier(byte[] key)
    {
        using var hmac = new HMACSHA256(key);
        return Convert.ToBase64String(hmac.ComputeHash(Encoding.UTF8.GetBytes("SafeBox password verifier v1")));
    }

    public bool VerifyPassword(byte[] key, string verifier)
    {
        var expected = Convert.FromBase64String(verifier);
        var actual = Convert.FromBase64String(CreatePasswordVerifier(key));
        return CryptographicOperations.FixedTimeEquals(expected, actual);
    }

    public byte[] Encrypt(byte[] key, byte[] plaintext, ReadOnlySpan<byte> associatedData = default)
    {
        var nonce = RandomNumberGenerator.GetBytes(NonceSize);
        var ciphertext = new byte[plaintext.Length];
        var tag = new byte[TagSize];

        using var aes = new AesGcm(key, TagSize);
        aes.Encrypt(nonce, plaintext, ciphertext, tag, associatedData);

        var output = new byte[4 + NonceSize + TagSize + ciphertext.Length];
        BinaryPrimitives.WriteInt32LittleEndian(output.AsSpan(0, 4), 1);
        nonce.CopyTo(output.AsSpan(4, NonceSize));
        tag.CopyTo(output.AsSpan(4 + NonceSize, TagSize));
        ciphertext.CopyTo(output.AsSpan(4 + NonceSize + TagSize));
        return output;
    }

    public byte[] Decrypt(byte[] key, byte[] payload, ReadOnlySpan<byte> associatedData = default)
    {
        if (payload.Length < 4 + NonceSize + TagSize)
        {
            throw new InvalidDataException("Encrypted payload is damaged.");
        }

        var version = BinaryPrimitives.ReadInt32LittleEndian(payload.AsSpan(0, 4));
        if (version != 1)
        {
            throw new InvalidDataException("Unsupported encryption version.");
        }

        var nonce = payload.AsSpan(4, NonceSize);
        var tag = payload.AsSpan(4 + NonceSize, TagSize);
        var ciphertext = payload.AsSpan(4 + NonceSize + TagSize);
        var plaintext = new byte[ciphertext.Length];

        using var aes = new AesGcm(key, TagSize);
        aes.Decrypt(nonce, ciphertext, tag, plaintext, associatedData);
        return plaintext;
    }

    private static string NormalizeRecoveryKey(string recoveryKey)
    {
        return recoveryKey.Trim().Replace(" ", "", StringComparison.Ordinal).ToLowerInvariant();
    }
}

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

    private const int ChunkSize = 10 * 1024 * 1024; // 10MB chunks

    public void EncryptChunked(byte[] key, string sourcePath, string destPath, ReadOnlySpan<byte> associatedData)
    {
        using var input = File.OpenRead(sourcePath);
        using var output = File.Create(destPath);

        // Version header
        var version = new byte[4];
        BinaryPrimitives.WriteInt32LittleEndian(version, 2);
        output.Write(version);

        var buffer = new byte[ChunkSize];
        var lengthBytes = new byte[4];
        int chunkIndex = 0;

        while (true)
        {
            var read = input.Read(buffer, 0, ChunkSize);
            if (read == 0) break;

            var chunkPlain = buffer.AsSpan(0, read);
            var nonce = new byte[NonceSize];
            RandomNumberGenerator.Fill(nonce);
            var ciphertext = new byte[read];
            var tag = new byte[TagSize];

            using var aes = new AesGcm(key, TagSize);
            var chunkAd = new byte[associatedData.Length + 4];
            associatedData.CopyTo(chunkAd);
            BinaryPrimitives.WriteInt32LittleEndian(chunkAd.AsSpan(associatedData.Length), chunkIndex);
            aes.Encrypt(nonce, chunkPlain, ciphertext, tag, chunkAd);

            // Chunk header: [length:4][nonce:12][tag:16][ciphertext:N]
            BinaryPrimitives.WriteInt32LittleEndian(lengthBytes, read);
            output.Write(lengthBytes);
            output.Write(nonce);
            output.Write(tag);
            output.Write(ciphertext);

            chunkIndex++;
        }
    }

    public byte[] DecryptChunked(byte[] key, string sourcePath, ReadOnlySpan<byte> associatedData)
    {
        using var input = File.OpenRead(sourcePath);

        var versionBytes = new byte[4];
        input.ReadExactly(versionBytes);
        var version = BinaryPrimitives.ReadInt32LittleEndian(versionBytes);
        if (version != 2)
            throw new InvalidDataException("Unsupported encryption version.");

        using var output = new MemoryStream();
        int chunkIndex = 0;

        while (input.Position < input.Length)
        {
            var lengthBytes = new byte[4];
            input.ReadExactly(lengthBytes);
            var chunkLength = BinaryPrimitives.ReadInt32LittleEndian(lengthBytes);

            var nonce = new byte[NonceSize];
            input.ReadExactly(nonce);
            var tag = new byte[TagSize];
            input.ReadExactly(tag);
            var ciphertext = new byte[chunkLength];
            input.ReadExactly(ciphertext);

            var plaintext = new byte[chunkLength];
            using var aes = new AesGcm(key, TagSize);
            var chunkAd = new byte[associatedData.Length + 4];
            associatedData.CopyTo(chunkAd);
            BinaryPrimitives.WriteInt32LittleEndian(chunkAd.AsSpan(associatedData.Length), chunkIndex);
            aes.Decrypt(nonce, ciphertext, tag, plaintext, chunkAd);

            output.Write(plaintext);
            Array.Clear(plaintext);
            chunkIndex++;
        }

        return output.ToArray();
    }

    private static string NormalizeRecoveryKey(string recoveryKey)
    {
        return recoveryKey.Trim().Replace(" ", "", StringComparison.Ordinal).ToLowerInvariant();
    }
}

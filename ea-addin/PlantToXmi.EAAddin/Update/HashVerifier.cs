using System;
using System.IO;
using System.Security.Cryptography;

namespace PlantToXmi.EAAddin.Update
{
    public static class HashVerifier
    {
        public static bool VerifySha256(string path, string expectedHex)
        {
            if (!File.Exists(path) || string.IsNullOrWhiteSpace(expectedHex))
            {
                return false;
            }

            using (var stream = File.OpenRead(path))
            using (var sha = SHA256.Create())
            {
                var actual = BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", string.Empty);
                return string.Equals(actual, expectedHex.Trim(), StringComparison.OrdinalIgnoreCase);
            }
        }
    }
}

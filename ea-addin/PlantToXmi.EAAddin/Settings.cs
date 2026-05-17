using System;
using System.IO;
using Microsoft.Win32;
using PlantToXmi.EAAddin.Runtime;

namespace PlantToXmi.EAAddin
{
    public sealed class Settings
    {
        public const string RegistryPath = @"Software\PlantToXMI\EAAddin";

        public string PlantToXmiPath { get; private set; }
        public bool KeepTempFiles { get; private set; }
        public int TimeoutSeconds { get; private set; }

        private Settings()
        {
        }

        public static Settings Load()
        {
            using (var key = Registry.CurrentUser.OpenSubKey(RegistryPath))
            {
                var configuredPath = ReadString(key, "PlantToXmiPath");
                return new Settings
                {
                    PlantToXmiPath = RuntimeLocator.Locate(ResolveExecutable(configuredPath)),
                    KeepTempFiles = ReadBool(key, "KeepTempFiles", false),
                    TimeoutSeconds = Math.Max(1, ReadInt(key, "TimeoutSeconds", 60))
                };
            }
        }

        private static string ResolveExecutable(string registryPath)
        {
            if (File.Exists(registryPath))
            {
                return registryPath;
            }

            var envPath = Environment.GetEnvironmentVariable("PLANTTOXMI_EXE");
            if (File.Exists(envPath))
            {
                return envPath;
            }

            return FindOnPath("planttoxmi.exe") ?? FindOnPath("planttoxmi") ?? "planttoxmi";
        }

        private static string FindOnPath(string executableName)
        {
            var path = Environment.GetEnvironmentVariable("PATH") ?? string.Empty;
            foreach (var directory in path.Split(Path.PathSeparator))
            {
                if (string.IsNullOrWhiteSpace(directory))
                {
                    continue;
                }

                try
                {
                    var candidate = Path.Combine(directory.Trim(), executableName);
                    if (File.Exists(candidate))
                    {
                        return candidate;
                    }
                }
                catch
                {
                    // Ignore malformed PATH entries.
                }
            }

            return null;
        }

        private static string ReadString(RegistryKey key, string name)
        {
            return key == null ? null : key.GetValue(name) as string;
        }

        private static bool ReadBool(RegistryKey key, string name, bool defaultValue)
        {
            var value = key == null ? null : key.GetValue(name);
            if (value == null)
            {
                return defaultValue;
            }

            bool parsed;
            if (bool.TryParse(Convert.ToString(value), out parsed))
            {
                return parsed;
            }

            return Convert.ToString(value) == "1";
        }

        private static int ReadInt(RegistryKey key, string name, int defaultValue)
        {
            var value = key == null ? null : key.GetValue(name);
            int parsed;
            return int.TryParse(Convert.ToString(value), out parsed) ? parsed : defaultValue;
        }
    }
}

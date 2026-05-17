using System;
using System.IO;

namespace PlantToXmi.EAAddin.Update
{
    public sealed class LocalRuntimeState
    {
        public int schemaVersion { get; set; }
        public string channel { get; set; }
        public string currentVersion { get; set; }
        public string currentExecutable { get; set; }
        public string previousVersion { get; set; }
        public string lastUpdateCheckUtc { get; set; }
        public string lastSuccessfulLaunchUtc { get; set; }

        public static string RootDirectory
        {
            get
            {
                return Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "PlantToXMI");
            }
        }

        public static string StatePath
        {
            get { return Path.Combine(RootDirectory, "current.json"); }
        }

        public static LocalRuntimeState Load()
        {
            var state = Json.ReadFile<LocalRuntimeState>(StatePath);
            if (state.schemaVersion == 0)
            {
                state.schemaVersion = 1;
            }

            if (string.IsNullOrWhiteSpace(state.channel))
            {
                state.channel = "stable";
            }

            return state;
        }

        public void Save()
        {
            Json.WriteFileAtomic(StatePath, this);
        }

        public string VersionDirectory(string version)
        {
            return Path.Combine(RootDirectory, "versions", version);
        }
    }
}

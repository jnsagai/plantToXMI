using System;
using System.IO;

namespace PlantToXmi.EAAddin.Update
{
    public sealed class UpdateSourceSettings
    {
        public string type { get; set; }
        public string owner { get; set; }
        public string repo { get; set; }
        public string channel { get; set; }
    }

    public sealed class UpdateSettings
    {
        public string updateMode { get; set; }
        public UpdateSourceSettings updateSource { get; set; }

        public static string SettingsPath
        {
            get { return Path.Combine(LocalRuntimeState.RootDirectory, "settings.json"); }
        }

        public static UpdateSettings Load()
        {
            var settings = Json.ReadFile<UpdateSettings>(SettingsPath);
            if (string.IsNullOrWhiteSpace(settings.updateMode))
            {
                settings.updateMode = "Daily";
            }

            if (settings.updateSource == null)
            {
                settings.updateSource = new UpdateSourceSettings
                {
                    type = "github-releases",
                    owner = Environment.GetEnvironmentVariable("PLANTTOXMI_GITHUB_OWNER") ?? string.Empty,
                    repo = Environment.GetEnvironmentVariable("PLANTTOXMI_GITHUB_REPO") ?? "planttoxmi",
                    channel = "stable"
                };
            }

            if (string.IsNullOrWhiteSpace(settings.updateSource.channel))
            {
                settings.updateSource.channel = "stable";
            }

            return settings;
        }
    }
}

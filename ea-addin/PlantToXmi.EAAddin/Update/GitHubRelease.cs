namespace PlantToXmi.EAAddin.Update
{
    public sealed class GitHubReleaseAsset
    {
        public string name { get; set; }
        public string browser_download_url { get; set; }
    }

    public sealed class GitHubRelease
    {
        public string tag_name { get; set; }
        public string body { get; set; }
        public bool prerelease { get; set; }
        public GitHubReleaseAsset[] assets { get; set; }

        public GitHubReleaseAsset FindAsset(string name)
        {
            if (assets == null)
            {
                return null;
            }

            foreach (var asset in assets)
            {
                if (asset != null && asset.name == name)
                {
                    return asset;
                }
            }

            return null;
        }
    }
}

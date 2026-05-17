using System;
using System.IO;
using System.Net;
using System.Web.Script.Serialization;

namespace PlantToXmi.EAAddin.Update
{
    public sealed class GitHubReleaseClient
    {
        private readonly string _bootstrapperVersion;

        public GitHubReleaseClient(string bootstrapperVersion)
        {
            _bootstrapperVersion = bootstrapperVersion;
        }

        public GitHubRelease GetLatestRelease(UpdateSourceSettings source)
        {
            if (source == null || string.IsNullOrWhiteSpace(source.owner) || string.IsNullOrWhiteSpace(source.repo))
            {
                throw new InvalidOperationException("GitHub owner/repo is not configured.");
            }

            var url = "https://api.github.com/repos/" + source.owner + "/" + source.repo + "/releases/latest";
            var json = DownloadString(url, "application/vnd.github+json");
            return new JavaScriptSerializer().Deserialize<GitHubRelease>(json);
        }

        public string DownloadManifest(GitHubRelease release)
        {
            var asset = release == null ? null : release.FindAsset("manifest.json");
            if (asset == null)
            {
                return null;
            }

            return DownloadString(asset.browser_download_url, "application/octet-stream");
        }

        public void DownloadAsset(GitHubReleaseAsset asset, string destination)
        {
            if (asset == null)
            {
                throw new ArgumentNullException("asset");
            }

            Directory.CreateDirectory(Path.GetDirectoryName(destination));
            using (var client = CreateWebClient("application/octet-stream"))
            {
                client.DownloadFile(asset.browser_download_url, destination);
            }
        }

        private string DownloadString(string url, string accept)
        {
            using (var client = CreateWebClient(accept))
            {
                return client.DownloadString(url);
            }
        }

        private WebClient CreateWebClient(string accept)
        {
            var client = new WebClient();
            client.Headers[HttpRequestHeader.UserAgent] = "PlantToXMI-EA-AddIn/" + _bootstrapperVersion;
            client.Headers[HttpRequestHeader.Accept] = accept;
            client.Headers["X-GitHub-Api-Version"] = "2022-11-28";
            return client;
        }
    }
}

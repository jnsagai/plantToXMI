using System;
using System.IO;
using System.Reflection;

namespace PlantToXmi.EAAddin.Update
{
    public sealed class UpdateService
    {
        public const string Platform = "win-x64";
        private readonly string _bootstrapperVersion;
        private readonly GitHubReleaseClient _client;

        public UpdateService()
        {
            _bootstrapperVersion = Assembly.GetExecutingAssembly().GetName().Version.ToString();
            _client = new GitHubReleaseClient(_bootstrapperVersion);
        }

        public UpdateResult CheckForUpdates()
        {
            try
            {
                var state = LocalRuntimeState.Load();
                var settings = UpdateSettings.Load();
                state.lastUpdateCheckUtc = DateTime.UtcNow.ToString("o");
                state.Save();

                var release = _client.GetLatestRelease(settings.updateSource);
                if (release == null)
                {
                    return UpdateResult.From(UpdateResultCode.UPDATE_FAILED_NETWORK, "GitHub returned no release.");
                }

                if (release.prerelease && settings.updateSource.channel != "beta" && settings.updateSource.channel != "dev")
                {
                    return UpdateResult.From(UpdateResultCode.NO_UPDATE_AVAILABLE, "Latest release is a prerelease and the channel is stable.");
                }

                var manifestJson = _client.DownloadManifest(release);
                if (string.IsNullOrWhiteSpace(manifestJson))
                {
                    return UpdateResult.From(UpdateResultCode.UPDATE_FAILED_MANIFEST_MISSING, "Release has no manifest.json asset.");
                }

                var manifest = UpdateManifest.Parse(manifestJson);
                if (string.IsNullOrWhiteSpace(manifest.releaseNotes))
                {
                    manifest.releaseNotes = release.body ?? string.Empty;
                }

                var errors = manifest.Validate(Platform, _bootstrapperVersion);
                if (errors.Count > 0)
                {
                    var bootstrapperRequired = false;
                    foreach (var error in errors)
                    {
                        if (error.IndexOf("bootstrapper", StringComparison.OrdinalIgnoreCase) >= 0)
                        {
                            bootstrapperRequired = true;
                        }
                    }

                    var invalid = UpdateResult.From(
                        bootstrapperRequired ? UpdateResultCode.BOOTSTRAPPER_UPGRADE_REQUIRED : UpdateResultCode.UPDATE_FAILED_MANIFEST_INVALID,
                        string.Join(Environment.NewLine, errors));
                    invalid.Manifest = manifest;
                    return invalid;
                }

                if (!VersionComparer.IsNewer(manifest.version, state.currentVersion))
                {
                    return UpdateResult.From(UpdateResultCode.NO_UPDATE_AVAILABLE, "PlantToXMI runtime is already up to date.");
                }

                var available = UpdateResult.From(UpdateResultCode.UPDATE_AVAILABLE, "PlantToXMI runtime " + manifest.version + " is available.");
                available.Manifest = manifest;
                return available;
            }
            catch (Exception ex)
            {
                return new UpdateResult
                {
                    Code = UpdateResultCode.UPDATE_FAILED_NETWORK,
                    Success = false,
                    Message = "Update check failed.",
                    Detail = ex.ToString()
                };
            }
        }

        public UpdateResult InstallUpdate(UpdateManifest manifest)
        {
            try
            {
                var settings = UpdateSettings.Load();
                var release = _client.GetLatestRelease(settings.updateSource);
                var asset = release == null ? null : release.FindAsset(manifest.assetName);
                if (asset == null)
                {
                    return UpdateResult.From(UpdateResultCode.UPDATE_FAILED_ASSET_MISSING, "Release asset is missing: " + manifest.assetName);
                }

                var cache = Path.Combine(LocalRuntimeState.RootDirectory, "update-cache");
                Directory.CreateDirectory(cache);
                var zip = Path.Combine(cache, manifest.assetName);
                _client.DownloadAsset(asset, zip);
                return new RuntimeInstaller().Install(manifest, zip);
            }
            catch (Exception ex)
            {
                return new UpdateResult
                {
                    Code = UpdateResultCode.UPDATE_FAILED_NETWORK,
                    Success = false,
                    Message = "Update install failed.",
                    Detail = ex.ToString()
                };
            }
        }
    }
}

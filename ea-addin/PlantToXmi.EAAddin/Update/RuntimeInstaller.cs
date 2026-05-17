using System;
using System.IO;
using System.IO.Compression;
using PlantToXmi.EAAddin.Runtime;

namespace PlantToXmi.EAAddin.Update
{
    public sealed class RuntimeInstaller
    {
        public UpdateResult Install(UpdateManifest manifest, string zipPath)
        {
            if (!HashVerifier.VerifySha256(zipPath, manifest.sha256))
            {
                return UpdateResult.From(UpdateResultCode.UPDATE_FAILED_HASH_MISMATCH, "Downloaded package failed SHA-256 verification.");
            }

            var state = LocalRuntimeState.Load();
            var versionDir = state.VersionDirectory(manifest.version);
            var stagingDir = versionDir + ".staging";
            if (Directory.Exists(stagingDir))
            {
                Directory.Delete(stagingDir, true);
            }

            if (Directory.Exists(versionDir))
            {
                return UpdateResult.From(UpdateResultCode.UPDATE_FAILED_EXTRACT, "Version is already installed: " + manifest.version);
            }

            try
            {
                ExtractZipSafely(zipPath, stagingDir);
            }
            catch (Exception ex)
            {
                return new UpdateResult
                {
                    Code = UpdateResultCode.UPDATE_FAILED_EXTRACT,
                    Success = false,
                    Message = "Could not extract runtime package.",
                    Detail = ex.ToString()
                };
            }

            var executable = Path.Combine(stagingDir, manifest.entryPoint);
            string smokeDetail;
            if (!new RuntimeSmokeTester().SmokeTest(executable, out smokeDetail))
            {
                TryDeleteDirectory(stagingDir);
                return new UpdateResult
                {
                    Code = UpdateResultCode.UPDATE_FAILED_SMOKE_TEST,
                    Success = false,
                    Message = "Runtime smoke test failed.",
                    Detail = smokeDetail
                };
            }

            Directory.Move(stagingDir, versionDir);
            state.previousVersion = state.currentVersion;
            state.currentVersion = manifest.version;
            state.currentExecutable = Path.Combine(versionDir, manifest.entryPoint);
            state.channel = string.IsNullOrWhiteSpace(manifest.channel) ? "stable" : manifest.channel;
            state.lastSuccessfulLaunchUtc = DateTime.UtcNow.ToString("o");
            state.Save();
            return UpdateResult.From(UpdateResultCode.UPDATE_INSTALLED, "PlantToXMI runtime " + manifest.version + " installed.");
        }

        public UpdateResult Rollback()
        {
            var state = LocalRuntimeState.Load();
            if (string.IsNullOrWhiteSpace(state.previousVersion))
            {
                return UpdateResult.From(UpdateResultCode.ROLLBACK_FAILED, "No previous runtime version is recorded.");
            }

            var previousDir = state.VersionDirectory(state.previousVersion);
            var executable = Path.Combine(previousDir, "planttoxmi.exe");
            if (!File.Exists(executable))
            {
                return UpdateResult.From(UpdateResultCode.ROLLBACK_FAILED, "Previous runtime executable was not found.");
            }

            var oldCurrent = state.currentVersion;
            state.currentVersion = state.previousVersion;
            state.currentExecutable = executable;
            state.previousVersion = oldCurrent;
            state.Save();
            return UpdateResult.From(UpdateResultCode.ROLLBACK_COMPLETED, "Rolled back to PlantToXMI runtime " + state.currentVersion + ".");
        }

        private static void ExtractZipSafely(string zipPath, string destination)
        {
            Directory.CreateDirectory(destination);
            var root = Path.GetFullPath(destination);
            using (var archive = ZipFile.OpenRead(zipPath))
            {
                foreach (var entry in archive.Entries)
                {
                    var target = Path.GetFullPath(Path.Combine(root, entry.FullName));
                    if (!target.StartsWith(root, StringComparison.OrdinalIgnoreCase))
                    {
                        throw new InvalidOperationException("Runtime package contains an unsafe path: " + entry.FullName);
                    }

                    if (string.IsNullOrEmpty(entry.Name))
                    {
                        Directory.CreateDirectory(target);
                        continue;
                    }

                    Directory.CreateDirectory(Path.GetDirectoryName(target));
                    entry.ExtractToFile(target, false);
                }
            }
        }

        private static void TryDeleteDirectory(string path)
        {
            try
            {
                if (Directory.Exists(path))
                {
                    Directory.Delete(path, true);
                }
            }
            catch
            {
                // Leave failed staging content for diagnostics if cleanup fails.
            }
        }
    }
}

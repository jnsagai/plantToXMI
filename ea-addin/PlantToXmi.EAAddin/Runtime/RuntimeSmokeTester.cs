using System.Diagnostics;
using System.IO;

namespace PlantToXmi.EAAddin.Runtime
{
    public sealed class RuntimeSmokeTester
    {
        public bool SmokeTest(string executablePath, out string detail)
        {
            detail = string.Empty;
            if (!File.Exists(executablePath))
            {
                detail = "Runtime executable was not found: " + executablePath;
                return false;
            }

            var startInfo = new ProcessStartInfo
            {
                FileName = executablePath,
                Arguments = "--version",
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true
            };

            using (var process = Process.Start(startInfo))
            {
                if (process == null)
                {
                    detail = "Could not start runtime.";
                    return false;
                }

                if (!process.WaitForExit(30000))
                {
                    process.Kill();
                    detail = "Runtime smoke test timed out.";
                    return false;
                }

                detail = process.StandardOutput.ReadToEnd() + process.StandardError.ReadToEnd();
                return process.ExitCode == 0;
            }
        }
    }
}

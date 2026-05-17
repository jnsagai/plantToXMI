using System;
using System.Diagnostics;
using System.IO;
using System.Text;

namespace PlantToXmi.EAAddin
{
    public sealed class PlantToXmiResult
    {
        public bool Success { get; set; }
        public string InputPath { get; set; }
        public string OutputXmiPath { get; set; }
        public string ExecutablePath { get; set; }
        public string Arguments { get; set; }
        public int ExitCode { get; set; }
        public string StdOut { get; set; }
        public string StdErr { get; set; }
        public string ErrorMessage { get; set; }
    }

    public sealed class PlantToXmiRunner
    {
        private readonly Settings _settings;

        public PlantToXmiRunner(Settings settings)
        {
            if (settings == null)
            {
                throw new ArgumentNullException("settings");
            }

            _settings = settings;
        }

        public PlantToXmiResult ConvertToEaXmi(string inputPath)
        {
            if (string.IsNullOrWhiteSpace(inputPath))
            {
                throw new ArgumentException("Input PlantUML path is required.", "inputPath");
            }

            if (!File.Exists(inputPath))
            {
                throw new FileNotFoundException("PlantUML file not found.", inputPath);
            }

            var outputPath = Path.Combine(
                Path.GetTempPath(),
                "planttoxmi-ea-addin-" + Guid.NewGuid().ToString("N") + ".xmi");
            return Run(inputPath, outputPath, "convert", inputPath, "-o", outputPath, "--profile", "ea");
        }

        public PlantToXmiResult ValidateInstallation()
        {
            var version = Run(null, null, "--version");
            if (!version.Success)
            {
                return version;
            }

            var help = Run(null, null, "inspect", "--help");
            return new PlantToXmiResult
            {
                Success = help.Success,
                ExecutablePath = _settings.PlantToXmiPath,
                Arguments = version.Arguments + Environment.NewLine + help.Arguments,
                ExitCode = help.ExitCode,
                StdOut = "Version:" + Environment.NewLine + version.StdOut + Environment.NewLine +
                         "Inspect help:" + Environment.NewLine + help.StdOut,
                StdErr = version.StdErr + Environment.NewLine + help.StdErr,
                ErrorMessage = help.Success ? string.Empty : help.ErrorMessage
            };
        }

        private PlantToXmiResult Run(string inputPath, string outputPath, params string[] args)
        {
            var arguments = JoinArguments(args);
            var result = new PlantToXmiResult
            {
                InputPath = inputPath ?? string.Empty,
                OutputXmiPath = outputPath ?? string.Empty,
                ExecutablePath = _settings.PlantToXmiPath,
                Arguments = arguments,
                ExitCode = -1,
                StdOut = string.Empty,
                StdErr = string.Empty,
                ErrorMessage = string.Empty
            };

            try
            {
                var startInfo = new ProcessStartInfo
                {
                    FileName = _settings.PlantToXmiPath,
                    Arguments = arguments,
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true,
                    StandardOutputEncoding = Encoding.UTF8,
                    StandardErrorEncoding = Encoding.UTF8
                };

                using (var process = new Process())
                {
                    process.StartInfo = startInfo;
                    process.Start();
                    var stdout = process.StandardOutput.ReadToEnd();
                    var stderr = process.StandardError.ReadToEnd();

                    if (!process.WaitForExit(_settings.TimeoutSeconds * 1000))
                    {
                        try
                        {
                            process.Kill();
                        }
                        catch
                        {
                            // Best effort cleanup.
                        }

                        result.StdOut = stdout;
                        result.StdErr = stderr;
                        result.ErrorMessage = "planttoxmi timed out after " + _settings.TimeoutSeconds + " seconds.";
                        return result;
                    }

                    result.ExitCode = process.ExitCode;
                    result.StdOut = stdout;
                    result.StdErr = stderr;
                    result.Success = process.ExitCode == 0;
                    result.ErrorMessage = result.Success ? string.Empty : "planttoxmi exited with code " + process.ExitCode + ".";
                    return result;
                }
            }
            catch (Exception ex)
            {
                result.ErrorMessage = ex.Message;
                result.StdErr = ex.ToString();
                return result;
            }
        }

        private static string JoinArguments(string[] args)
        {
            var builder = new StringBuilder();
            for (var i = 0; i < args.Length; i++)
            {
                if (i > 0)
                {
                    builder.Append(' ');
                }

                builder.Append(Quote(args[i]));
            }

            return builder.ToString();
        }

        private static string Quote(string value)
        {
            if (value == null)
            {
                return "\"\"";
            }

            if (value.Length == 0)
            {
                return "\"\"";
            }

            var builder = new StringBuilder();
            builder.Append('"');
            var backslashes = 0;
            foreach (var character in value)
            {
                if (character == '\\')
                {
                    backslashes++;
                    continue;
                }

                if (character == '"')
                {
                    builder.Append('\\', backslashes * 2 + 1);
                    builder.Append('"');
                    backslashes = 0;
                    continue;
                }

                builder.Append('\\', backslashes);
                builder.Append(character);
                backslashes = 0;
            }

            builder.Append('\\', backslashes * 2);
            builder.Append('"');
            return builder.ToString();
        }
    }
}

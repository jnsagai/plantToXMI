using System;
using System.IO;
using System.Text;
using System.Windows.Forms;
using PlantToXmi.EAAddin.Update;

namespace PlantToXmi.EAAddin
{
    public static class Diagnostics
    {
        public static void ShowConversionFailure(PlantToXmiResult result)
        {
            ShowWithLog(
                "PlantToXMI conversion failed.",
                "PlantToXMI Conversion Failed",
                MessageBoxIcon.Error,
                BuildConversionDiagnostic(result, null));
        }

        public static void ShowImportFailure(PlantToXmiResult conversion, EaImportResult importResult)
        {
            ShowWithLog(
                "PlantToXMI import into Enterprise Architect failed.",
                "PlantToXMI Import Failed",
                MessageBoxIcon.Error,
                BuildConversionDiagnostic(conversion, importResult));
        }

        public static void ShowSuccess(PlantToXmiResult conversion, EaImportResult importResult)
        {
            var diagramText = string.IsNullOrWhiteSpace(importResult.DiagramName)
                ? "No EA diagram was created for this import."
                : "Created diagram: " + importResult.DiagramName + " (" + importResult.DiagramType + ")";

            MessageBox.Show(
                "PlantUML imported successfully into package:" + Environment.NewLine +
                importResult.PackageName + Environment.NewLine + Environment.NewLine +
                diagramText,
                "PlantToXMI",
                MessageBoxButtons.OK,
                MessageBoxIcon.Information);
        }

        public static void ShowInstallationStatus(PlantToXmiResult result)
        {
            ShowWithLog(
                result.Success ? "planttoxmi installation validated." : "planttoxmi installation validation failed.",
                "PlantToXMI Installation",
                result.Success ? MessageBoxIcon.Information : MessageBoxIcon.Error,
                BuildConversionDiagnostic(result, null));
        }

        public static void ShowUpdateResult(UpdateResult result)
        {
            ShowWithLog(
                result.Message ?? result.Code.ToString(),
                "PlantToXMI Updates",
                result.Success ? MessageBoxIcon.Information : MessageBoxIcon.Error,
                (result.Message ?? string.Empty) + Environment.NewLine + Environment.NewLine +
                (result.Detail ?? string.Empty));
        }

        public static void ShowAbout()
        {
            var state = LocalRuntimeState.Load();
            var updateSettings = UpdateSettings.Load();
            MessageBox.Show(
                "PlantToXMI Enterprise Architect Add-In" + Environment.NewLine +
                "Bootstrapper version: 0.1.0" + Environment.NewLine +
                "Runtime version: " + (state.currentVersion ?? "(not managed)") + Environment.NewLine +
                "Runtime path: " + (state.currentExecutable ?? Settings.Load().PlantToXmiPath) + Environment.NewLine +
                "Update channel: " + (state.channel ?? updateSettings.updateSource.channel) + Environment.NewLine +
                "Last update check: " + (state.lastUpdateCheckUtc ?? "(never)") + Environment.NewLine +
                "GitHub source: " + (updateSettings.updateSource.owner ?? string.Empty) + "/" + (updateSettings.updateSource.repo ?? string.Empty),
                "About PlantToXMI",
                MessageBoxButtons.OK,
                MessageBoxIcon.Information);
        }

        private static void ShowWithLog(string summary, string title, MessageBoxIcon icon, string detail)
        {
            var logPath = WriteLog(detail);
            MessageBox.Show(
                summary + Environment.NewLine + Environment.NewLine + "Diagnostic log:" + Environment.NewLine + logPath,
                title,
                MessageBoxButtons.OK,
                icon);
        }

        private static string BuildConversionDiagnostic(PlantToXmiResult result, EaImportResult importResult)
        {
            var builder = new StringBuilder();
            builder.AppendLine("Operation:");
            builder.AppendLine(importResult == null ? "planttoxmi conversion" : "EA XMI import");
            builder.AppendLine();
            builder.AppendLine("Input:");
            builder.AppendLine(result.InputPath ?? string.Empty);
            builder.AppendLine();
            builder.AppendLine("Output XMI:");
            builder.AppendLine(result.OutputXmiPath ?? string.Empty);
            builder.AppendLine();
            builder.AppendLine("Executable:");
            builder.AppendLine(result.ExecutablePath ?? string.Empty);
            builder.AppendLine();
            builder.AppendLine("Command arguments:");
            builder.AppendLine(result.Arguments ?? string.Empty);
            builder.AppendLine();
            builder.AppendLine("Exit code:");
            builder.AppendLine(result.ExitCode.ToString());
            builder.AppendLine();
            builder.AppendLine("Error:");
            builder.AppendLine(result.ErrorMessage ?? string.Empty);
            builder.AppendLine();
            builder.AppendLine("stdout:");
            builder.AppendLine(result.StdOut ?? string.Empty);
            builder.AppendLine();
            builder.AppendLine("stderr:");
            builder.AppendLine(result.StdErr ?? string.Empty);

            if (importResult != null)
            {
                builder.AppendLine();
                builder.AppendLine("EA package:");
                builder.AppendLine(importResult.PackageName + " " + importResult.PackageGuid);
                builder.AppendLine();
                builder.AppendLine("EA import result:");
                builder.AppendLine(importResult.EaResult ?? string.Empty);
                builder.AppendLine();
                builder.AppendLine("EA diagram:");
                builder.AppendLine(importResult.DiagramName ?? string.Empty);
                builder.AppendLine(importResult.DiagramType ?? string.Empty);
                builder.AppendLine("Objects: " + importResult.DiagramObjects);
                builder.AppendLine("Links: " + importResult.DiagramLinks);
            }

            return builder.ToString();
        }

        private static string WriteLog(string content)
        {
            var path = Path.Combine(
                Update.LocalRuntimeState.RootDirectory,
                "logs",
                "planttoxmi-ea-addin-" + DateTime.Now.ToString("yyyyMMdd-HHmmss") + ".log");
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            File.WriteAllText(path, content ?? string.Empty, Encoding.UTF8);
            return path;
        }
    }
}

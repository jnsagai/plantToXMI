using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using PlantToXmi.EAAddin.Update;

namespace PlantToXmi.EAAddin
{
    [ComVisible(true)]
    [Guid("A4D10C22-FC47-4F3F-BC10-91B8473C4206")]
    [ProgId("PlantToXmi.EAAddin.Main")]
    public class Main
    {
        private const string MenuRoot = "-&PlantToXMI";
        private const string MenuImport = "&Import PlantUML...";
        private const string MenuValidate = "&Validate planttoxmi Installation";
        private const string MenuCheckUpdates = "&Check for Updates";
        private const string MenuAbout = "&About PlantToXMI";
        private static bool _dailyUpdateChecked;

        public string EA_Connect(EA.Repository repository)
        {
            return string.Empty;
        }

        public void EA_Disconnect()
        {
            GC.Collect();
            GC.WaitForPendingFinalizers();
        }

        public object EA_GetMenuItems(EA.Repository repository, string menuLocation, string menuName)
        {
            if (string.IsNullOrEmpty(menuName))
            {
                return MenuRoot;
            }

            if (menuName == MenuRoot)
            {
                MaybeCheckDailyUpdates();
                return new[] { MenuImport, MenuValidate, MenuCheckUpdates, "-", MenuAbout };
            }

            return null;
        }

        public void EA_GetMenuState(
            EA.Repository repository,
            string menuLocation,
            string menuName,
            string itemName,
            ref bool isEnabled,
            ref bool isChecked)
        {
            isChecked = false;
            isEnabled = IsProjectOpen(repository);
        }

        public void EA_MenuClick(
            EA.Repository repository,
            string menuLocation,
            string menuName,
            string itemName)
        {
            try
            {
                switch (itemName)
                {
                    case MenuImport:
                        ImportPlantUml(repository);
                        break;
                    case MenuValidate:
                        ValidateInstallation();
                        break;
                    case MenuCheckUpdates:
                        CheckForUpdates();
                        break;
                    case MenuAbout:
                        Diagnostics.ShowAbout();
                        break;
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    ex.ToString(),
                    "PlantToXMI Add-In Error",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error);
            }
        }

        private static bool IsProjectOpen(EA.Repository repository)
        {
            try
            {
                return repository != null && repository.Models != null;
            }
            catch
            {
                return false;
            }
        }

        private static void ImportPlantUml(EA.Repository repository)
        {
            var selectedPackage = repository.GetTreeSelectedPackage();
            if (selectedPackage == null)
            {
                MessageBox.Show(
                    "Please select a target package in the Enterprise Architect Browser before importing PlantUML.",
                    "PlantToXMI",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Warning);
                return;
            }

            using (var dialog = new OpenFileDialog())
            {
                dialog.Filter = "PlantUML files (*.puml;*.plantuml)|*.puml;*.plantuml|All files (*.*)|*.*";
                dialog.Title = "Select PlantUML file";

                if (dialog.ShowDialog() != DialogResult.OK)
                {
                    return;
                }

                var settings = Settings.Load();
                var runner = new PlantToXmiRunner(settings);
                var conversion = runner.ConvertToEaXmi(dialog.FileName);

                try
                {
                    if (!conversion.Success)
                    {
                        Diagnostics.ShowConversionFailure(conversion);
                        return;
                    }

                    var importer = new EaImporter(repository);
                    var importResult = importer.ImportXmiIntoPackage(selectedPackage, conversion.OutputXmiPath);

                    if (!importResult.Success)
                    {
                        Diagnostics.ShowImportFailure(conversion, importResult);
                        return;
                    }

                    var materializer = new EaDiagramMaterializer(repository);
                    materializer.CreateDiagramForImport(importResult, dialog.FileName);

                    repository.RefreshModelView(selectedPackage.PackageID);
                    Diagnostics.ShowSuccess(conversion, importResult);
                }
                finally
                {
                    if (!settings.KeepTempFiles && File.Exists(conversion.OutputXmiPath))
                    {
                        File.Delete(conversion.OutputXmiPath);
                    }
                }
            }
        }

        private static void ValidateInstallation()
        {
            var runner = new PlantToXmiRunner(Settings.Load());
            var result = runner.ValidateInstallation();
            Diagnostics.ShowInstallationStatus(result);
        }

        private static void CheckForUpdates()
        {
            var service = new UpdateService();
            var check = service.CheckForUpdates();
            if (check.Code != UpdateResultCode.UPDATE_AVAILABLE)
            {
                Diagnostics.ShowUpdateResult(check);
                return;
            }

            var choice = MessageBox.Show(
                check.Message + Environment.NewLine + Environment.NewLine +
                "Install this runtime update now?",
                "PlantToXMI Update Available",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Question);
            if (choice != DialogResult.Yes)
            {
                Diagnostics.ShowUpdateResult(check);
                return;
            }

            Diagnostics.ShowUpdateResult(service.InstallUpdate(check.Manifest));
        }

        private static void MaybeCheckDailyUpdates()
        {
            if (_dailyUpdateChecked)
            {
                return;
            }

            _dailyUpdateChecked = true;
            var settings = UpdateSettings.Load();
            if (settings.updateMode == "Disabled" || settings.updateMode == "Manual")
            {
                return;
            }

            if (settings.updateSource == null || string.IsNullOrWhiteSpace(settings.updateSource.owner))
            {
                return;
            }

            var state = LocalRuntimeState.Load();
            DateTime lastCheck;
            if (DateTime.TryParse(state.lastUpdateCheckUtc, out lastCheck) &&
                DateTime.UtcNow.Subtract(lastCheck.ToUniversalTime()).TotalHours < 24)
            {
                return;
            }

            var service = new UpdateService();
            var check = service.CheckForUpdates();
            if (check.Code != UpdateResultCode.UPDATE_AVAILABLE)
            {
                return;
            }

            var choice = MessageBox.Show(
                check.Message + Environment.NewLine + Environment.NewLine +
                "Install this runtime update now?",
                "PlantToXMI Update Available",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Question);
            if (choice == DialogResult.Yes)
            {
                Diagnostics.ShowUpdateResult(service.InstallUpdate(check.Manifest));
            }
        }
    }
}

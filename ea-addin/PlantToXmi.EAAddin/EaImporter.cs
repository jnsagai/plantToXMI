using System;
using System.IO;

namespace PlantToXmi.EAAddin
{
    public sealed class EaImportResult
    {
        public bool Success { get; set; }
        public string PackageGuid { get; set; }
        public string PackageName { get; set; }
        public string ImportedPackageGuid { get; set; }
        public string XmiPath { get; set; }
        public string EaResult { get; set; }
        public string DiagramName { get; set; }
        public string DiagramType { get; set; }
        public int DiagramObjects { get; set; }
        public int DiagramLinks { get; set; }
    }

    public sealed class EaImporter
    {
        private readonly EA.Repository _repository;

        public EaImporter(EA.Repository repository)
        {
            if (repository == null)
            {
                throw new ArgumentNullException("repository");
            }

            _repository = repository;
        }

        public EaImportResult ImportXmiIntoPackage(EA.Package package, string xmiPath)
        {
            if (package == null)
            {
                throw new ArgumentNullException("package");
            }

            if (string.IsNullOrWhiteSpace(xmiPath))
            {
                throw new ArgumentException("XMI path is required.", "xmiPath");
            }

            if (!File.Exists(xmiPath))
            {
                throw new FileNotFoundException("XMI file not found.", xmiPath);
            }

            var project = _repository.GetProjectInterface();
            var packageGuidXml = project.GUIDtoXML(package.PackageGUID);
            var importResult = project.ImportPackageXMI(packageGuidXml, xmiPath, 1, 1) ?? string.Empty;

            return new EaImportResult
            {
                Success = IsImportSuccess(importResult),
                PackageGuid = package.PackageGUID,
                PackageName = package.Name,
                ImportedPackageGuid = ExtractImportedPackageGuid(importResult),
                XmiPath = xmiPath,
                EaResult = importResult,
                DiagramName = string.Empty,
                DiagramType = string.Empty
            };
        }

        private static bool IsImportSuccess(string result)
        {
            var value = (result ?? string.Empty).Trim();
            if (value.Length == 0)
            {
                return true;
            }

            if (value.Length == 38 && value.StartsWith("{", StringComparison.Ordinal) && value.EndsWith("}", StringComparison.Ordinal))
            {
                Guid parsed;
                return Guid.TryParse(value, out parsed);
            }

            return false;
        }

        private static string ExtractImportedPackageGuid(string result)
        {
            var value = (result ?? string.Empty).Trim();
            if (value.Length == 38 && value.StartsWith("{", StringComparison.Ordinal) && value.EndsWith("}", StringComparison.Ordinal))
            {
                Guid parsed;
                if (Guid.TryParse(value, out parsed))
                {
                    return value;
                }
            }

            return string.Empty;
        }
    }
}

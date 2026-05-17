using System.Collections.Generic;
using System.Web.Script.Serialization;

namespace PlantToXmi.EAAddin.Update
{
    public sealed class UpdateManifest
    {
        public int schemaVersion { get; set; }
        public string product { get; set; }
        public string version { get; set; }
        public string channel { get; set; }
        public string platform { get; set; }
        public string minimumBootstrapperVersion { get; set; }
        public string assetName { get; set; }
        public string sha256 { get; set; }
        public string entryPoint { get; set; }
        public string releaseNotes { get; set; }

        public static UpdateManifest Parse(string json)
        {
            return new JavaScriptSerializer().Deserialize<UpdateManifest>(json);
        }

        public IList<string> Validate(string localPlatform, string bootstrapperVersion)
        {
            var errors = new List<string>();
            if (schemaVersion != 1)
            {
                errors.Add("Unsupported schemaVersion.");
            }

            if (product != "planttoxmi")
            {
                errors.Add("Manifest product is not planttoxmi.");
            }

            if (platform != localPlatform)
            {
                errors.Add("Manifest platform does not match this runtime.");
            }

            if (string.IsNullOrWhiteSpace(version))
            {
                errors.Add("Manifest version is missing.");
            }

            if (string.IsNullOrWhiteSpace(assetName))
            {
                errors.Add("Manifest assetName is missing.");
            }

            if (string.IsNullOrWhiteSpace(sha256))
            {
                errors.Add("Manifest sha256 is missing.");
            }

            if (string.IsNullOrWhiteSpace(entryPoint))
            {
                errors.Add("Manifest entryPoint is missing.");
            }

            if (!string.IsNullOrWhiteSpace(minimumBootstrapperVersion) &&
                VersionComparer.Compare(minimumBootstrapperVersion, bootstrapperVersion) > 0)
            {
                errors.Add("This release requires a newer EA Add-In bootstrapper.");
            }

            return errors;
        }
    }
}

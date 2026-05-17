namespace PlantToXmi.EAAddin.Runtime
{
    public sealed class RuntimeLauncher
    {
        public PlantToXmiResult RunVersion(Settings settings)
        {
            return new PlantToXmiRunner(settings).ValidateInstallation();
        }
    }
}

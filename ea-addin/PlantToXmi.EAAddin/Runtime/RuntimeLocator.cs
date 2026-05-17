using System.IO;
using PlantToXmi.EAAddin.Update;

namespace PlantToXmi.EAAddin.Runtime
{
    public static class RuntimeLocator
    {
        public static string Locate(string configuredPath)
        {
            var state = LocalRuntimeState.Load();
            if (!string.IsNullOrWhiteSpace(state.currentExecutable) && File.Exists(state.currentExecutable))
            {
                return state.currentExecutable;
            }

            return configuredPath;
        }
    }
}

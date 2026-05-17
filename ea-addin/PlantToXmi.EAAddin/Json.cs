using System.IO;
using System.Text;
using System.Web.Script.Serialization;

namespace PlantToXmi.EAAddin
{
    internal static class Json
    {
        public static T ReadFile<T>(string path) where T : class, new()
        {
            if (!File.Exists(path))
            {
                return new T();
            }

            var serializer = new JavaScriptSerializer();
            return serializer.Deserialize<T>(File.ReadAllText(path, Encoding.UTF8)) ?? new T();
        }

        public static void WriteFileAtomic<T>(string path, T value)
        {
            var serializer = new JavaScriptSerializer();
            var tempPath = path + ".tmp";
            var backupPath = path + ".bak";
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            File.WriteAllText(tempPath, serializer.Serialize(value), Encoding.UTF8);
            if (File.Exists(path))
            {
                File.Replace(tempPath, path, backupPath, true);
            }
            else
            {
                File.Move(tempPath, path);
            }
        }
    }
}

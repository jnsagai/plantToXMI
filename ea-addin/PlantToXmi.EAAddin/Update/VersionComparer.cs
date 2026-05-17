using System;

namespace PlantToXmi.EAAddin.Update
{
    public static class VersionComparer
    {
        public static int Compare(string left, string right)
        {
            var leftParts = Parse(left);
            var rightParts = Parse(right);
            for (var index = 0; index < 3; index++)
            {
                if (leftParts[index] != rightParts[index])
                {
                    return leftParts[index].CompareTo(rightParts[index]);
                }
            }

            return 0;
        }

        public static bool IsNewer(string candidate, string current)
        {
            return Compare(candidate, current) > 0;
        }

        private static int[] Parse(string value)
        {
            var normalized = (value ?? string.Empty).Trim();
            if (normalized.StartsWith("v", StringComparison.OrdinalIgnoreCase))
            {
                normalized = normalized.Substring(1);
            }

            var parts = normalized.Split('.');
            var result = new[] { 0, 0, 0 };
            for (var index = 0; index < parts.Length && index < 3; index++)
            {
                var token = parts[index];
                var dash = token.IndexOf('-');
                if (dash >= 0)
                {
                    token = token.Substring(0, dash);
                }

                int parsed;
                result[index] = int.TryParse(token, out parsed) ? parsed : 0;
            }

            return result;
        }
    }
}

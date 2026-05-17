using System;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;

namespace PlantToXmi.EAAddin
{
    public sealed class EaDiagramMaterializer
    {
        private readonly EA.Repository _repository;

        public EaDiagramMaterializer(EA.Repository repository)
        {
            if (repository == null)
            {
                throw new ArgumentNullException("repository");
            }

            _repository = repository;
        }

        public void CreateDiagramForImport(EaImportResult importResult, string inputPath)
        {
            if (importResult == null || !importResult.Success)
            {
                return;
            }

            var package = ResolveImportedPackage(importResult);
            if (package == null)
            {
                return;
            }

            var diagramType = DetectDiagramType(package, inputPath);
            if (string.IsNullOrEmpty(diagramType))
            {
                return;
            }

            var diagramName = UniqueDiagramName(package, Path.GetFileNameWithoutExtension(inputPath));
            var diagram = package.Diagrams.AddNew(diagramName, diagramType) as EA.Diagram;
            if (diagram == null)
            {
                return;
            }

            diagram.Update();

            if (diagramType == "Sequence")
            {
                AddSequenceObjectsAndLinks(package, diagram);
            }
            else if (diagramType == "Requirements")
            {
                AddRequirementObjectsAndLinks(package, diagram, inputPath);
            }
            else
            {
                AddComponentObjects(package, diagram);
            }

            diagram.Update();
            package.Update();
            _repository.ReloadDiagram(diagram.DiagramID);

            importResult.DiagramName = diagram.Name;
            importResult.DiagramType = diagram.Type;
            importResult.DiagramObjects = diagram.DiagramObjects.Count;
            importResult.DiagramLinks = diagram.DiagramLinks.Count;
        }

        private EA.Package ResolveImportedPackage(EaImportResult importResult)
        {
            if (!string.IsNullOrWhiteSpace(importResult.ImportedPackageGuid))
            {
                try
                {
                    return _repository.GetPackageByGuid(importResult.ImportedPackageGuid);
                }
                catch
                {
                    return null;
                }
            }

            return null;
        }

        private static string DetectDiagramType(EA.Package package, string inputPath)
        {
            if (IsRequirementsSource(inputPath))
            {
                return "Requirements";
            }

            if (HasSequenceContent(package))
            {
                return "Sequence";
            }

            if (HasComponentContent(package))
            {
                return "Component";
            }

            return string.Empty;
        }

        private static bool IsRequirementsSource(string inputPath)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(inputPath) || !File.Exists(inputPath))
                {
                    return false;
                }

                var source = File.ReadAllText(inputPath);
                return Regex.IsMatch(source, @"<<\s*requirement\s*>>|\brequirement\s+[""\w]", RegexOptions.IgnoreCase);
            }
            catch
            {
                return false;
            }
        }

        private static bool HasComponentContent(EA.Package package)
        {
            for (short i = 0; i < package.Elements.Count; i++)
            {
                var element = package.Elements.GetAt(i) as EA.Element;
                if (element == null)
                {
                    continue;
                }

                if (element.Type == "Component" || element.Type == "Interface")
                {
                    return true;
                }
            }

            return false;
        }

        private static bool HasSequenceContent(EA.Package package)
        {
            for (short i = 0; i < package.Elements.Count; i++)
            {
                var element = package.Elements.GetAt(i) as EA.Element;
                if (element == null)
                {
                    continue;
                }

                if (element.Type == "Interaction")
                {
                    return true;
                }
            }

            return false;
        }

        private static string UniqueDiagramName(EA.Package package, string baseName)
        {
            if (string.IsNullOrWhiteSpace(baseName))
            {
                baseName = "PlantUML Import";
            }

            var candidate = baseName;
            var suffix = 2;
            while (DiagramExists(package, candidate))
            {
                candidate = baseName + " " + suffix;
                suffix++;
            }

            return candidate;
        }

        private static bool DiagramExists(EA.Package package, string name)
        {
            for (short i = 0; i < package.Diagrams.Count; i++)
            {
                var diagram = package.Diagrams.GetAt(i) as EA.Diagram;
                if (diagram != null && string.Equals(diagram.Name, name, StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }

            return false;
        }

        private static void AddComponentObjects(EA.Package package, EA.Diagram diagram)
        {
            var nodes = new List<EA.Element>();
            for (short i = 0; i < package.Elements.Count; i++)
            {
                var element = package.Elements.GetAt(i) as EA.Element;
                if (element == null)
                {
                    continue;
                }

                if (element.Type == "Component" || element.Type == "Interface" || element.Type == "Class")
                {
                    nodes.Add(element);
                }
            }

            var columns = Math.Max(2, Math.Min(4, (int)Math.Ceiling(Math.Sqrt(Math.Max(nodes.Count, 1)))));
            for (var index = 0; index < nodes.Count; index++)
            {
                var column = index % columns;
                var row = index / columns;
                AddDiagramObject(diagram, nodes[index].ElementID, 40 + column * 230, 40 + row * 150, 150, 80);
            }
        }

        private static void AddRequirementObjectsAndLinks(EA.Package package, EA.Diagram diagram, string inputPath)
        {
            var model = ParseRequirements(inputPath);
            if (model.Requirements.Count == 0)
            {
                return;
            }

            var elementsByAlias = new Dictionary<string, EA.Element>(StringComparer.OrdinalIgnoreCase);
            foreach (var requirement in model.Requirements)
            {
                var element = package.Elements.AddNew(RequirementDisplayName(requirement), "Requirement") as EA.Element;
                if (element == null)
                {
                    continue;
                }

                element.Notes = requirement.Text ?? string.Empty;
                element.Stereotype = "Requirement";
                element.Update();
                elementsByAlias[requirement.Alias] = element;
                elementsByAlias[requirement.Name] = element;
            }

            package.Elements.Refresh();
            RemoveRequirementPlaceholders(package, model.Requirements);

            var levels = RequirementLevels(model.Requirements, model.Containment);
            foreach (var pair in levels)
            {
                var level = pair.Key;
                var requirements = pair.Value;
                var count = requirements.Count;
                for (var index = 0; index < requirements.Count; index++)
                {
                    EA.Element element;
                    if (!elementsByAlias.TryGetValue(requirements[index].Alias, out element))
                    {
                        continue;
                    }

                    var left = 60 + index * 310 + Math.Max(0, 4 - count) * 130;
                    var top = 40 + level * 170;
                    AddDiagramObject(diagram, element.ElementID, left, top, 260, 110);
                }
            }

            foreach (var relation in model.Containment)
            {
                EA.Element source;
                EA.Element target;
                if (!elementsByAlias.TryGetValue(relation.SourceAlias, out source) ||
                    !elementsByAlias.TryGetValue(relation.TargetAlias, out target))
                {
                    continue;
                }

                var connector = source.Connectors.AddNew(string.Empty, "Aggregation") as EA.Connector;
                if (connector == null)
                {
                    continue;
                }

                connector.SupplierID = target.ElementID;
                connector.Direction = "Source -> Destination";
                try
                {
                    connector.ClientEnd.Aggregation = 1;
                }
                catch
                {
                    // Some EA interop versions do not allow setting end aggregation.
                }

                connector.Update();
                source.Connectors.Refresh();

                var link = diagram.DiagramLinks.AddNew(string.Empty, string.Empty) as EA.DiagramLink;
                if (link == null)
                {
                    continue;
                }

                link.ConnectorID = connector.ConnectorID;
                link.Update();
            }
        }

        private static RequirementModel ParseRequirements(string inputPath)
        {
            var model = new RequirementModel();
            var source = File.ReadAllText(inputPath);
            var blockPattern = new Regex(
                @"(?:class|requirement)\s+""(?<name>[^""]+)""\s+as\s+(?<alias>[A-Za-z_][\w-]*)[^{\r\n]*(?:<<\s*requirement\s*>>)?\s*\{(?<body>.*?)\}",
                RegexOptions.IgnoreCase | RegexOptions.Singleline);

            foreach (Match match in blockPattern.Matches(source))
            {
                var body = match.Groups["body"].Value;
                model.Requirements.Add(
                    new RequirementNode
                    {
                        Alias = match.Groups["alias"].Value,
                        Name = match.Groups["name"].Value,
                        Id = ExtractRequirementProperty(body, "id"),
                        Text = ExtractRequirementProperty(body, "text")
                    });
            }

            var relationPattern = new Regex(
                @"(?<source>[A-Za-z_][\w-]*)\s+[.ox<|*#]*[-.]+[.ox>|*#]*\s+(?<target>[A-Za-z_][\w-]*)",
                RegexOptions.IgnoreCase);
            foreach (Match match in relationPattern.Matches(source))
            {
                var line = match.Value;
                if (!line.Contains("*"))
                {
                    continue;
                }

                model.Containment.Add(
                    new RequirementRelation
                    {
                        SourceAlias = match.Groups["source"].Value,
                        TargetAlias = match.Groups["target"].Value
                    });
            }

            return model;
        }

        private static string ExtractRequirementProperty(string body, string name)
        {
            var match = Regex.Match(body, @"^\s*" + Regex.Escape(name) + @"\s*[:=]\s*(?<value>.+?)\s*$", RegexOptions.IgnoreCase | RegexOptions.Multiline);
            if (!match.Success)
            {
                return string.Empty;
            }

            return match.Groups["value"].Value.Trim().Trim('"');
        }

        private static string RequirementDisplayName(RequirementNode requirement)
        {
            if (!string.IsNullOrWhiteSpace(requirement.Id) &&
                !requirement.Name.StartsWith(requirement.Id, StringComparison.OrdinalIgnoreCase))
            {
                return requirement.Id + " " + requirement.Name;
            }

            return requirement.Name;
        }

        private static void RemoveRequirementPlaceholders(EA.Package package, List<RequirementNode> requirements)
        {
            var names = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var requirement in requirements)
            {
                names.Add(requirement.Name);
                names.Add(requirement.Alias);
            }

            for (short index = (short)(package.Elements.Count - 1); index >= 0; index--)
            {
                var element = package.Elements.GetAt(index) as EA.Element;
                if (element == null || element.Type == "Requirement")
                {
                    continue;
                }

                if (names.Contains(element.Name))
                {
                    package.Elements.DeleteAt(index, false);
                }
            }

            package.Elements.Refresh();
        }

        private static SortedDictionary<int, List<RequirementNode>> RequirementLevels(List<RequirementNode> requirements, List<RequirementRelation> containment)
        {
            var byAlias = new Dictionary<string, RequirementNode>(StringComparer.OrdinalIgnoreCase);
            var childrenByParent = new Dictionary<string, List<string>>(StringComparer.OrdinalIgnoreCase);
            var childAliases = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var requirement in requirements)
            {
                byAlias[requirement.Alias] = requirement;
            }

            foreach (var relation in containment)
            {
                if (!childrenByParent.ContainsKey(relation.SourceAlias))
                {
                    childrenByParent[relation.SourceAlias] = new List<string>();
                }

                childrenByParent[relation.SourceAlias].Add(relation.TargetAlias);
                childAliases.Add(relation.TargetAlias);
            }

            var levels = new SortedDictionary<int, List<RequirementNode>>();
            var queue = new Queue<Tuple<string, int>>();
            foreach (var requirement in requirements)
            {
                if (!childAliases.Contains(requirement.Alias))
                {
                    queue.Enqueue(Tuple.Create(requirement.Alias, 0));
                }
            }

            var visited = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            while (queue.Count > 0)
            {
                var item = queue.Dequeue();
                if (visited.Contains(item.Item1) || !byAlias.ContainsKey(item.Item1))
                {
                    continue;
                }

                visited.Add(item.Item1);
                if (!levels.ContainsKey(item.Item2))
                {
                    levels[item.Item2] = new List<RequirementNode>();
                }

                levels[item.Item2].Add(byAlias[item.Item1]);
                List<string> children;
                if (childrenByParent.TryGetValue(item.Item1, out children))
                {
                    foreach (var child in children)
                    {
                        queue.Enqueue(Tuple.Create(child, item.Item2 + 1));
                    }
                }
            }

            foreach (var requirement in requirements)
            {
                if (!visited.Contains(requirement.Alias))
                {
                    if (!levels.ContainsKey(0))
                    {
                        levels[0] = new List<RequirementNode>();
                    }

                    levels[0].Add(requirement);
                }
            }

            return levels;
        }

        private static void AddSequenceObjectsAndLinks(EA.Package package, EA.Diagram diagram)
        {
            var lifelines = new List<EA.Element>();
            var connectors = new SortedDictionary<int, EA.Connector>();

            for (short i = 0; i < package.Elements.Count; i++)
            {
                var interaction = package.Elements.GetAt(i) as EA.Element;
                if (interaction == null || interaction.Type != "Interaction")
                {
                    continue;
                }

                for (short j = 0; j < interaction.Elements.Count; j++)
                {
                    var lifeline = interaction.Elements.GetAt(j) as EA.Element;
                    if (lifeline == null)
                    {
                        continue;
                    }

                    if (lifeline.Type == "Sequence" || lifeline.Type == "Actor" || lifeline.Type == "Object")
                    {
                        lifelines.Add(lifeline);
                        for (short k = 0; k < lifeline.Connectors.Count; k++)
                        {
                            var connector = lifeline.Connectors.GetAt(k) as EA.Connector;
                            if (connector != null && connector.Type == "Sequence")
                            {
                                connectors[connector.ConnectorID] = connector;
                            }
                        }
                    }
                }
            }

            for (var index = 0; index < lifelines.Count; index++)
            {
                AddDiagramObject(diagram, lifelines[index].ElementID, 40 + index * 145, 30, 112, 420);
            }

            var orderedConnectors = new List<EA.Connector>(connectors.Values);
            orderedConnectors.Sort(CompareSequenceConnectors);

            for (var index = 0; index < orderedConnectors.Count; index++)
            {
                var connector = orderedConnectors[index];
                try
                {
                    connector.SequenceNo = index + 1;
                    connector.Update();
                }
                catch
                {
                    // Older EA interop builds can expose SequenceNo as read-only.
                }

                var link = diagram.DiagramLinks.AddNew(string.Empty, string.Empty) as EA.DiagramLink;
                if (link == null)
                {
                    continue;
                }

                link.ConnectorID = connector.ConnectorID;
                link.Geometry = "EDGE=3;";
                link.Update();
            }
        }

        private static int CompareSequenceConnectors(EA.Connector left, EA.Connector right)
        {
            var leftOrder = ExtractTrailingNumber(left == null ? string.Empty : left.Name);
            var rightOrder = ExtractTrailingNumber(right == null ? string.Empty : right.Name);
            if (leftOrder != rightOrder)
            {
                return leftOrder.CompareTo(rightOrder);
            }

            var leftId = left == null ? 0 : left.ConnectorID;
            var rightId = right == null ? 0 : right.ConnectorID;
            return leftId.CompareTo(rightId);
        }

        private static int ExtractTrailingNumber(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return int.MaxValue;
            }

            var match = Regex.Match(value, @"(\d+)\s*$");
            if (!match.Success)
            {
                return int.MaxValue;
            }

            int parsed;
            return int.TryParse(match.Groups[1].Value, out parsed) ? parsed : int.MaxValue;
        }

        private sealed class RequirementModel
        {
            public readonly List<RequirementNode> Requirements = new List<RequirementNode>();
            public readonly List<RequirementRelation> Containment = new List<RequirementRelation>();
        }

        private sealed class RequirementNode
        {
            public string Alias;
            public string Name;
            public string Id;
            public string Text;
        }

        private sealed class RequirementRelation
        {
            public string SourceAlias;
            public string TargetAlias;
        }

        private static void AddDiagramObject(EA.Diagram diagram, int elementId, int left, int top, int width, int height)
        {
            var eaTop = -top;
            var eaBottom = -(top + height);
            var style = string.Format("l={0};r={1};t={2};b={3};", left, left + width, eaTop, eaBottom);
            var diagramObject = diagram.DiagramObjects.AddNew(style, string.Empty) as EA.DiagramObject;
            if (diagramObject == null)
            {
                return;
            }

            diagramObject.ElementID = elementId;
            diagramObject.Update();
        }
    }
}

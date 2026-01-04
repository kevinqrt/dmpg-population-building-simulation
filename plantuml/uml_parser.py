import re
import os
from collections import defaultdict
import logging


def prepare_plantuml_file(file_path):
    """
    Removes all occurrences of '{abstract}' from the file and overwrites it.
    This is necessary because curly brackets would otherwise cause errors.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    # Remove all occurrences of '{abstract}'
    cleaned_content = content.replace("{abstract}", "").strip()

    # Overwrite the file with the cleaned version
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(cleaned_content)


def parse_plantuml_classes(file_path):
    package_classes = defaultdict(list)  # Stores packages and their associated class names
    class_definitions = {}  # Stores complete class definitions (all attributes/methods) for each class
    relationships = []  # Stores relationships (inheritance, associations)
    current_class = None  # Tracks the current class being processed

    # Regex for class definition and package assignment
    class_pattern = re.compile(r'class\s+"([^"]+)"\s+as\s+([\w\.]+)')

    # Check if the file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} was not found!")

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            match = class_pattern.search(line)
            if match:
                class_name, full_path = match.groups()
                parts = full_path.split(".")
                package = ".".join(parts[1:3]) if len(parts) >= 3 else ".".join(parts[:-1])

                package_classes[package].append(class_name)
                class_definitions[class_name] = line  # Store the class definition
                current_class = class_name
                continue

            if current_class:
                if "}" in line:  # End of class definition
                    class_definitions[current_class] += line
                    current_class = None
                else:
                    class_definitions[current_class] += line
                continue

            # Store relationships (excluding association names after `:`)
            if "--|>" in line:
                relation_only = line.split(":")[0].strip()  # Remove everything after `:` + whitespace
                relationships.append(relation_only + "\n")  # Store the cleaned relationship

    return package_classes, class_definitions, relationships


def generate_new_puml(package_classes, class_definitions, relationships, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("@startuml\n"
                "set namespaceSeparator none\n"
                "top to bottom direction\n"
                "skinparam lineType ortho\n"
                "skinparam class {\n"
                "    BackgroundColor White\n"
                "    BorderColor Black\n"
                "    ArrowColor Black\n"
                "    FontSize 12\n"
                "    AttributeFontSize 11\n"
                "}\n"
                "skinparam package {\n"
                "    FontSize 14\n"
                "    BorderColor #666666\n"
                "}\n"
                "skinparam ClassFontStyle bold\n"
                "skinparam padding 2\n"
                "skinparam nodesep 80\n"
                "skinparam ranksep 80\n\n"
                "package \"core\" #ACD8FF{\n\n")

        # Generate package structure with 3 classes per together block
        for package, classes in package_classes.items():
            f.write(f'package "{package}" #82B4E6 {{\n')

            for i in range(0, len(classes), 3):
                grouped_classes = classes[i:i + 3]  # Always takes 3 classes
                f.write("\n  together {\n")
                for cls in grouped_classes:
                    f.write(class_definitions[cls] + "\n")
                f.write("  }\n")

            f.write("}\n\n")  # Close package

        f.write("}\n\n")

        # Write relationships back
        for relation in relationships:
            f.write(relation)

        f.write("\n@enduml")


# Generate dynamic paths
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # Base directory of the script
uml_file = os.path.join(base_dir, "plantuml", "uml_diagrams", "raw_diagrams", "classes_raw_UML.plantuml")
output_file = os.path.join(base_dir, "plantuml", "uml_diagrams", "optimized_diagrams", "optimized_DMPG_UML.puml")

# Prepare the .puml file
prepare_plantuml_file(uml_file)

# Run the parser and generate the UML file
parsed_packages, parsed_classes, parsed_relations = parse_plantuml_classes(uml_file)
generate_new_puml(parsed_packages, parsed_classes, parsed_relations, output_file)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

logging.info(f"Optimized PlantUML file created: {output_file}")

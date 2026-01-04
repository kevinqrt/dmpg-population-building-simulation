# DMPG – Digital Model Play Ground

## Overview
DMPG (Digital Model PlayGround) is a framework for developing and executing discrete event simulations with support for advanced analysis, visualization, and optimization.

## Features (In Development)
- **Discrete Simulations**
- **Core Components:** Entity, Source, Server, Sink, Vehicle, Storage, Combiner, Separator, Tally Statistics
- **Replications & Multiprocessing**
- **Database Connection:** ORM-based results/statistics storage
- **Experiments:** Multiple scenarios
- **Visualization:**
    - 7 plot types: Bar, Histogram, Pie, Box, Violin, Scatter, SMORE analysis
    - Topology 2D visualization
- **Processing Time Based on Entities and Servers**
- **Work Scheduling & Resource Management:** Worker pools with dynamic scheduling
- **Distributed Simulations**
- **ML-Based Optimization**
- **Animated Simulations in Unreal Engine**
- **Analysis Functions:** Sensitivity analysis, steady-state analysis, traditional optimizations

**Version details:** See the `CHANGELOG`.

---

## Development Guidelines

<details><summary>Running flake8 Before Pushing</summary>

## Running flake8 Before Pushing

To ensure code quality and PEP 8 compliance, run `flake8` before committing your changes.

1. **Activate your Python virtual environment:**
   ```bash
   source venv/bin/activate  # macOS/Linux
   venv\Scripts\activate  # Windows
   ```

2. Run flake8:
   ```bash
   flake8
   ```
---
</details>

<details><summary>Connecting IntelliJ IDEA to SonarCloud via SonarLint</summary>

### Connecting IntelliJ IDEA to SonarCloud via SonarLint

SonarCloud is used for static analysis and tracking code quality metrics.

1. **Install SonarLint Plugin in IntelliJ IDEA**
   - Open Settings → Plugins
   - Search for SonarLint
   - Click Install and restart IntelliJ IDEA

2. **Configure SonarLint to Connect to SonarCloud**
   - Go to Settings → Tools → SonarLint
   - Under Connections, click ➕ → SonarCloud
   - Authenticate with your SonarCloud credentials
   - Select the corresponding SonarCloud Project for DMPG
   - Enable Automatic Mode to analyze files on-the-fly

3. **Run SonarLint Analysis**
   - Right-click the project folder in IntelliJ IDEA
   - Select Analyze with SonarLint
---
</details>

<details><summary>Using the Pylint Plugin in IntelliJ IDEA</summary>

### Using the Pylint Plugin in IntelliJ IDEA

Pylint helps maintain consistency and enforces Python best practices.

1. **Install the Pylint Plugin**

   - Open Settings → Plugins
   - Search for Pylint
   - Click Install and restart IntelliJ IDEA

2. **Configure Pylint for Your Project**
   - Open Settings → Languages & Frameworks → Pylint
   - Set the Pylint executable to:
     ```bash
     <your_virtualenv_path>/bin/pylint  # macOS/Linux
     <your_virtualenv_path>\Scripts\pylint.exe  # Windows
     ```
   - Add project-specific .pylintrc settings

3. **Run Pylint in IntelliJ IDEA**
   - Scan a Python file via the Plugin
   - Or analyze whole module via the Plugin

---
</details>

<details><summary>Creating UML-Diagramms with PlantUML</summary>

### Creating UML-Diagramms with PlantUML

PlantUML automatically generates UML diagrams from text-based descriptions. 
The UML parser ensures that the diagrams are correctly structured and formatted.

**How to create a class diagramm with PlantUML**

1. **Install PlantUML**
   - Pylint-Pyreverse

         pip install pylint   # Linux, macOS, Windows

   - PlantUML

         sudo apt install plantuml  # Linux  
         brew install plantuml      # macOS  
         choco install plantuml     # Windows


2. **Generate an Incomplete Diagram with PlantUML**
   - Run the following command:
   
         pyreverse -o plantuml -p raw_UML -d plantuml/uml_diagrams/raw_diagrams src/

   - This generates the file classes_raw_UML.puml
   - The output is a text-based class diagram created from the src/ directory


3. **Use the UML Parser to Complete the Diagram**
   - Run the UML Parser in the terminal or manually in `plantuml/uml_parser.py`:
     ```bash
     python plantuml/uml_parser.py
     ```  
   - This will:
      - Read the `.puml` file from **`plantuml/uml_diagrams/raw_diagrams/`**
      - Apply corrections and formatting
      - Save the optimized file to **`plantuml/uml_diagrams/optimized_diagrams/`**
   - **Expected Output:**
     ```
     plantuml/
     │── uml_diagrams/
     │   ├── raw_diagrams/
     │   │   ├── raw_UML.puml        # Raw output from Pyreverse
     │   ├── optimized_diagrams/
     │   │   ├── optimized_DMPG_UML.puml  # Processed & structured version
     ```
     

4. **Export the UML Diagram as SVG or PNG**
   - Run the following command to generate an **SVG file**:

       ```
       plantuml -tsvg plantuml/uml_diagrams/optimized_diagrams/optimized_DMPG_UML.puml
       ```
    
   - Run the following command to generate an **PNG file**:

       ```
       plantuml plantuml/uml_diagrams/optimized_diagrams/optimized_DMPG_UML.puml
       ```

   - This will create `optimized_DMPG_UML.svg` or `optimized_DMPG_UML.png` in the same directory as the `.puml` file.
---

</details>

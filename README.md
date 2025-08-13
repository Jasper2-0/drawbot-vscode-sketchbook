# DrawBot VSCode Sketchbook

A Processing-like creative coding environment for Python using DrawBot, integrated with VSCode for seamless sketch development, experimentation, and iteration.

> **⚠️ Platform Requirement**: This project requires **macOS** as DrawBot is a macOS-only graphics library. DrawBot leverages macOS's Core Text and Core Graphics frameworks for high-quality typography and graphics rendering.

## 🎨 Overview

DrawBot VSCode Sketchbook enables artists, designers, and creative coders to rapidly prototype and iterate on generative art, data visualizations, and interactive graphics using Python and DrawBot's powerful 2D graphics capabilities within a familiar development environment.

## ✨ Features

### 🏗️ Core System

- **Project Structure Management** - Automatic scaffolding of organized project directories
- **Sketch Management** - Create, organize, and manage sketch files with metadata
- **Template System** - Professional sketch templates for different creative patterns
- **Safe Execution** - Isolated sketch running with timeout protection and error handling
- **DrawBot Integration** - Consistent API wrapper with mock support for testing

### 🖥️ Command Line Interface

- **Professional CLI** - Simple and intuitive `sketchbook` command.
- **Project Initialization** - Set up complete project structure with one command
- **Sketch Creation** - Generate new sketches from templates with automatic naming
- **Template Browsing** - List and explore available sketch starting points
- **Sketch Execution** - Run sketches safely with comprehensive error reporting
- **Validation** - Check syntax before execution to catch errors early
- **Project Status** - View project information and statistics

### 📝 Built-in Templates

- **Minimal Sketch** - Clean starting point for any creative idea
- **Basic Shapes** - Rectangles, ovals, and polygons demonstration
- **Simple Animation** - Frame-based animation with trail effects
- **Generative Pattern** - Procedural grid patterns with randomization
- **Typography Art** - Creative text arrangements and effects

## 🚀 Quick Start

### Installation

**Prerequisites**: macOS 10.12+ with Python 3.8+

1. Clone the repository:

    ```bash
    git clone [https://github.com/your-username/drawbot-vscode-sketchbook.git](https://github.com/your-username/drawbot-vscode-sketchbook.git)
    cd drawbot-vscode-sketchbook
    ```

2. Set up Python virtual environment:

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. Install the project in editable mode:

    ```bash
    pip install -e .
    ```

    This command installs the project and creates the `sketchbook` command-line tool.

4. Install development dependencies (for running tests):

    ```bash
    pip install -r requirements-dev.txt
    ```

### Initialize Your First Project

```bash
# Initialize project in a specific directory
sketchbook init my-art-project
cd my-art-project
```

### Create and Run Your First Sketch

```bash
# Create a new sketch from template
sketchbook new my_first_sketch --template minimal_sketch

# Validate the sketch
sketchbook validate my_first_sketch

# Run the sketch
sketchbook run my_first_sketch

# List all sketches
sketchbook list
```

## 📚 Documentation

- **[CLI Usage Guide](CLI_USAGE.md)** - Complete command-line interface reference
- **[Product Requirements](docs/prd_sketchbook.md)** - Vision and feature specifications
- **[TDD Implementation Plan](docs/tdd_implementation_plan.md)** - Test-driven development approach

## 🏗️ Architecture

The project follows a modular, test-driven architecture:

```bash
drawbot-vscode-sketchbook/
├── src/
│   ├── core/                 # Core system components
│   └── cli/                  # Command-line interface
├── templates/                # Sketch templates
├── sketches/                 # User sketch files
├── tests/                    # Comprehensive test suite
├── docs/                     # Documentation
└── pyproject.toml            # Project packaging configuration
```

## 🧪 Testing

The project uses comprehensive Test-Driven Development with 35+ passing tests:

```bash
# Run all tests
source venv/bin/activate
pytest -v
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Implement features following TDD approach
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the terms specified in the LICENSE file.

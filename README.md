# DrawBot VSCode Sketchbook

A Processing-inspired creative coding sketchbook for Python using DrawBot. Create, organize, and preview generative art sketches with an intuitive command-line interface and real-time web-based live preview studio.

> **⚠️ Platform Requirement**: This project requires **macOS** as DrawBot is a macOS-only graphics library. DrawBot leverages macOS's Core Text and Core Graphics frameworks for high-quality typography and graphics rendering.

## 🎨 Overview

DrawBot VSCode Sketchbook enables artists, designers, and creative coders to rapidly prototype and iterate on generative art, data visualizations, and creative graphics using Python and DrawBot's powerful 2D graphics capabilities. The system features a **live preview web studio** for instant visual feedback, organized project management, template-based sketch creation, and safe execution with comprehensive error handling.

## ✨ Features

### 🎨 Live Preview Studio (NEW!)

- **Web-Based Interface** - Beautiful browser-based sketch preview and management
- **Real-Time Execution** - Click "Execute Sketch" to instantly see your art
- **Multi-Format Support** - PNG, GIF, JPEG, PDF with automatic retina scaling
- **Error Debugging** - Helpful visual placeholders for Python errors with debugging tips
- **Categorized Gallery** - Separate sections for your sketches vs educational examples
- **Live Stats Dashboard** - Overview of your creative work with execution metrics

### 🏗️ Core System

- **Clean Organization** - User sketches separated from examples and system tests
- **Project Structure Management** - Automatic scaffolding of organized project directories
- **Template System** - Professional sketch templates for different creative patterns
- **Safe Execution** - Isolated sketch running with timeout protection and error handling
- **Educational Examples** - Learn from DrawBot + library examples (drawbotgrid, etc.)
- **Cache System** - Intelligent preview caching with version control

### 🖥️ Command Line Interface

- **Professional CLI** - Simple and intuitive `sketchbook` command with 7 core commands
- **Live Preview Server** - Start web interface with `sketchbook live`
- **Project Initialization** - Set up complete project structure with one command (`init`)
- **Sketch Creation** - Generate new sketches from templates with automatic naming (`new`)
- **Template Browsing** - List and explore available sketch starting points (`templates`)
- **Sketch Management** - List all sketches in the project (`list`)
- **Sketch Execution** - Run sketches safely with comprehensive error reporting (`run`)
- **Validation** - Check syntax before execution to catch errors early (`validate`)
- **Project Status** - View project information and statistics (`info`)

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

### Create and Preview Your First Sketch

```bash
# Create a new sketch from template
sketchbook new my_first_sketch --template minimal_sketch

# Start the live preview studio
sketchbook live

# Opens http://localhost:8083 in your browser
# Click your sketch to open the live preview
# Click "Execute Sketch" to see instant results!
```

**Traditional CLI workflow** (if you prefer command-line):

```bash
# Validate the sketch syntax
sketchbook validate my_first_sketch

# Run the sketch from command line
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
│   ├── cli/                  # Command-line interface
│   └── server/               # Live preview web server
├── templates/                # Sketch templates
├── sketches/                 # User creative workspace (clean!)
├── examples/                 # Educational examples (DrawBot + libraries)
├── tests/
│   ├── sketches/             # System test sketches (hidden from users)
│   └── *.py                  # Test suite
├── cache/                    # Preview image cache
├── docs/                     # Documentation
└── pyproject.toml            # Project packaging configuration
```

## 🧪 Testing

The project uses comprehensive Test-Driven Development with 43 passing tests:

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

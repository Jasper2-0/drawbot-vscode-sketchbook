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
git clone <repository-url>
cd drawbot-vscode-sketchbook
```

2. Set up Python virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

3. Install DrawBot (required):
```bash
# DrawBot must be installed from GitHub (not available via PyPI)
pip install git+https://github.com/typemytype/drawbot
```

> **Note**: DrawBot installation may take a few minutes as it compiles native extensions that integrate with macOS graphics frameworks.

### Initialize Your First Project

```bash
# Initialize project in current directory
python sketchbook.py init

# Or initialize in a specific directory
python sketchbook.py init my-art-project
cd my-art-project
```

### Create and Run Your First Sketch

```bash
# Create a new sketch from template
python sketchbook.py new my_first_sketch --template minimal_sketch

# Validate the sketch
python sketchbook.py validate my_first_sketch

# Run the sketch
python sketchbook.py run my_first_sketch

# List all sketches
python sketchbook.py list
```

## 📚 Documentation

- **[CLI Usage Guide](CLI_USAGE.md)** - Complete command-line interface reference
- **[Product Requirements](docs/prd_sketchbook.md)** - Vision and feature specifications
- **[TDD Implementation Plan](docs/tdd_implementation_plan.md)** - Test-driven development approach

## 🏗️ Architecture

The project follows a modular, test-driven architecture:

```
drawbot-vscode-sketchbook/
├── src/
│   ├── core/                 # Core system components
│   │   ├── project_structure.py    # Directory management
│   │   ├── sketch_manager.py       # File operations
│   │   ├── drawbot_wrapper.py      # DrawBot API wrapper
│   │   └── sketch_runner.py        # Safe execution engine
│   └── cli/                  # Command-line interface
│       └── main.py           # CLI implementation
├── templates/                # Sketch templates
├── sketches/                 # User sketch files
├── tests/                    # Comprehensive test suite
├── docs/                     # Documentation
└── sketchbook.py            # Main CLI entry point
```

### Core Components

- **ProjectStructure** - Validates and creates project directory structure
- **SketchManager** - Handles sketch file operations, templates, and metadata
- **DrawBotWrapper** - Provides consistent DrawBot API with mock support
- **SketchRunner** - Executes sketches safely with timeout and error handling
- **CLI Interface** - User-friendly command-line tools for all operations

## 🧪 Testing

The project uses comprehensive Test-Driven Development with 35+ passing tests:

```bash
# Run all tests
source venv/bin/activate
python -m pytest -v

# Run specific component tests
python -m pytest tests/test_project_structure.py -v
python -m pytest tests/test_sketch_manager.py -v
python -m pytest tests/test_drawbot_wrapper_simple.py -v
python -m pytest tests/test_sketch_runner_simple.py -v
```

### Test Coverage
- ✅ Project structure validation and creation
- ✅ Sketch management and template system
- ✅ DrawBot API wrapper with mock support
- ✅ Safe sketch execution with timeout protection
- ✅ Error handling and edge cases

## 🎯 Use Cases

### For Creative Coders
- Rapid prototyping of generative art concepts
- Organized project structure for complex creative works
- Template-based starting points for common patterns
- Safe experimentation with timeout protection

### For Educators
- Teaching programming concepts through visual art
- Pre-built examples and templates for learning
- Clear project organization for student portfolios
- Safe execution environment for classroom use

### For Students
- Learn creative coding through hands-on examples
- Experiment with different artistic techniques
- Build portfolio of creative programming projects
- Understand programming concepts through visual feedback

## 🛠️ Development

### Project Status
- ✅ **Phase 1 Complete**: MVP Foundation with all core components
- ✅ **CLI Interface**: Fully functional command-line tools
- ✅ **Template System**: Professional starting points for creative work
- ✅ **Test Suite**: Comprehensive TDD coverage with 35+ passing tests

### Development Commands

```bash
# Set up development environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt

# Run tests with coverage
python -m pytest --cov=src --cov-report=xml

# Code formatting and linting
black src/ tests/
flake8 src/ tests/
mypy src/
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Implement features following TDD approach
5. Ensure all tests pass
6. Submit a pull request

### Development Principles
- **Test-Driven Development** - Write tests before implementation
- **Clean Architecture** - Modular, separated concerns
- **User Experience** - Intuitive CLI with helpful error messages
- **Safety First** - Isolated execution with comprehensive error handling

## 📄 License

This project is licensed under the terms specified in the LICENSE file.

## 🎨 Examples

### Basic Shapes
```python
import drawbot

drawbot.size(400, 400)
drawbot.fill(1, 0, 0)  # Red
drawbot.rect(50, 50, 100, 100)
drawbot.fill(0, 0, 1)  # Blue  
drawbot.oval(200, 200, 150, 100)
drawbot.saveImage("shapes.png")
```

### Generative Pattern
```python
import drawbot
import random

drawbot.size(600, 600)
drawbot.fill(0.1, 0.1, 0.2)
drawbot.rect(0, 0, 600, 600)

for x in range(0, 600, 30):
    for y in range(0, 600, 30):
        drawbot.fill(random.random(), random.random(), 1)
        drawbot.oval(x, y, 20, 20)

drawbot.saveImage("pattern.png")
```

### Animation
```python
import drawbot
import math

for frame in range(60):
    drawbot.newPage(400, 400)
    angle = frame * 6  # 6 degrees per frame
    
    x = 200 + 100 * math.cos(math.radians(angle))
    y = 200 + 100 * math.sin(math.radians(angle))
    
    drawbot.fill(1, 0.3, 0.3)
    drawbot.oval(x-10, y-10, 20, 20)

drawbot.saveImage("animation.gif")
```

## 📋 Platform Compatibility

### macOS Support
- **Full Support**: All features available including DrawBot graphics rendering
- **Requirements**: macOS 10.12+ with Python 3.8+
- **Installation**: Standard installation via `git+https://github.com/typemytype/drawbot`

### Other Platforms
- **Limited Support**: CLI and project management features work on all platforms
- **Graphics Limitation**: DrawBot sketches cannot execute (DrawBot is macOS-only)
- **Use Cases**: Project organization, sketch management, template browsing
- **Alternative**: Consider using [cairo](https://cairographics.org/) or [skia-python](https://github.com/kyamagu/skia-python) for cross-platform graphics

### Why macOS-Only?
DrawBot leverages macOS's Core Text and Core Graphics frameworks for:
- **High-quality typography** with full font feature support
- **Native PDF/PostScript generation** 
- **Precise color management** via macOS ColorSync
- **Optimized rendering performance** through hardware acceleration

---

**Built with ❤️ for the creative coding community**
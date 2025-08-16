# DrawBot Sketchbook CLI

A command-line interface for the DrawBot VSCode Sketchbook system with comprehensive code quality tooling and real-time web preview capabilities.

## Quick Start

```bash
# Initialize a new project
sketchbook init

# Create a new sketch
sketchbook new my_sketch

# Create a sketch from template
sketchbook new art_piece --template basic_shapes

# 🎨 Start live preview studio (NEW!)
sketchbook live

# Traditional CLI commands:
# Run a sketch
sketchbook run my_sketch

# List all sketches
sketchbook list

# List available templates
sketchbook templates

# Get project info
sketchbook info

# Validate sketch syntax
sketchbook validate my_sketch
```

## Commands

### `init [path]`

Initialize a new DrawBot sketchbook project in the specified directory (default: current directory).

### `new <name> [--template <template>]`

Create a new sketch file with the given name.

Options:

- `--template`, `-t` - Use a specific template (see `templates` command)

### `templates`

List all available sketch templates with descriptions.

### `list`

List all sketches in the current project.

### `live [--port <port>]`

🎨 **NEW!** Start the live preview web studio for interactive sketch development.

Opens a beautiful web interface at `http://localhost:8083` featuring:
- Real-time sketch execution and preview
- Visual gallery of your sketches and examples
- Error debugging with helpful placeholders
- WebSocket live updates
- Multi-format support (PNG, GIF, JPEG, PDF)

Options:

- `--port`, `-p` - Server port (default: 8083)

Example:
```bash
sketchbook live --port 8080
```

### `run <name> [--timeout <seconds>]`

Execute a sketch file safely with timeout protection.

Options:

- `--timeout`, `-T` - Maximum execution time (default: 30 seconds)

### `validate <name>`

Check a sketch file for syntax errors without executing it.

### `info`

Display current project information.

## Examples

```bash
# Set up a new creative coding workspace
mkdir my-art-project
cd my-art-project
sketchbook init

# Create different types of sketches
sketchbook new mandala --template generative_pattern
sketchbook new logo --template basic_shapes

# Work with sketches
sketchbook validate mandala
sketchbook run mandala
sketchbook list

# Check project status
sketchbook info

# 🎨 Start live preview studio for visual development
sketchbook live
```

## Code Quality Integration

The CLI integrates with the project's comprehensive code quality tooling:

```bash
# Pre-commit hooks run automatically on git commits
git add my_sketch.py
git commit -m "Add new sketch"  # Triggers Black formatting + MyPy checks

# Manual code quality commands
black .              # Format all Python files
mypy src/            # Type checking
pytest -v            # Run comprehensive test suite
pre-commit run --all-files  # Run all quality checks
```

# DrawBot Sketchbook CLI

A command-line interface for the DrawBot VSCode Sketchbook system.

## Quick Start

```bash
# Initialize a new project
sketchbook init

# Create a new sketch
sketchbook new my_sketch

# Create a sketch from template
sketchbook new art_piece --template basic_shapes

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
```

# DrawBot Sketchbook CLI

A command-line interface for the DrawBot VSCode Sketchbook system.

## Quick Start

```bash
# Initialize a new project
python sketchbook.py init

# Create a new sketch
python sketchbook.py new my_sketch

# Create a sketch from template
python sketchbook.py new art_piece --template basic_shapes

# Run a sketch
python sketchbook.py run my_sketch

# List all sketches
python sketchbook.py list

# List available templates
python sketchbook.py templates

# Get project info
python sketchbook.py info

# Validate sketch syntax
python sketchbook.py validate my_sketch
```

## Commands

### `init [path]`

Initialize a new DrawBot sketchbook project in the specified directory (default: current directory).

Creates the required directory structure:

- `sketches/` - Your sketch files
- `templates/` - Sketch templates
- `examples/` - Example sketches
- `tools/` - Development tools
- `docs/` - Documentation
- `extensions/` - VSCode extensions
- `src/` - Source code
- `tests/` - Test files

### `new <name> [--template <template>]`

Create a new sketch file with the given name.

Options:

- `--template`, `-t` - Use a specific template (see `templates` command)

The sketch will be created in the `sketches/` directory. If a sketch with the same name exists, a number suffix will be added automatically.

### `templates`

List all available sketch templates with descriptions.

Built-in templates:

- `minimal_sketch` - Clean starting point
- `basic_shapes` - Rectangles, ovals, polygons
- `simple_animation` - Frame-based animation
- `generative_pattern` - Procedural patterns
- `typography_art` - Creative text layouts

### `list`

List all sketches in the current project, organized by category if they're in subdirectories.

### `run <name> [--timeout <seconds>]`

Execute a sketch file safely with timeout protection.

Options:

- `--timeout`, `-T` - Maximum execution time (default: 30 seconds)

The runner will:

1. Validate syntax before execution
2. Execute in isolated environment
3. Capture output and errors
4. Report execution time
5. Handle timeouts gracefully

### `validate <name>`

Check a sketch file for syntax errors without executing it.

### `info`

Display current project information including:

- Project path
- Validation status
- Number of sketches
- Number of templates

## Examples

```bash
# Set up a new creative coding workspace
mkdir my-art-project
cd my-art-project
python /path/to/sketchbook.py init

# Create different types of sketches
python sketchbook.py new mandala --template generative_pattern
python sketchbook.py new logo --template basic_shapes
python sketchbook.py new intro --template simple_animation

# Work with sketches
python sketchbook.py validate mandala
python sketchbook.py run mandala
python sketchbook.py list

# Check project status
python sketchbook.py info
```

## Error Handling

The CLI provides clear error messages for common issues:

- **Missing DrawBot**: Shows helpful error when DrawBot module isn't installed
- **Syntax Errors**: Validates Python syntax before execution
- **Timeouts**: Prevents infinite loops with configurable timeout
- **File Not Found**: Clear messages for missing sketches or templates
- **Invalid Project**: Guides you to initialize project structure

## Tips

1. **Start Simple**: Use `minimal_sketch` template to begin with a clean slate
2. **Use Templates**: Leverage built-in templates to learn DrawBot patterns
3. **Validate First**: Always run `validate` before `run` to catch syntax errors early
4. **Organize Sketches**: Create subdirectories in `sketches/` to organize by project or theme
5. **Custom Templates**: Add your own templates to the `templates/` directory

## Integration

The CLI is designed to work alongside VSCode with the DrawBot extension, providing a complete creative coding environment for generative art and design.

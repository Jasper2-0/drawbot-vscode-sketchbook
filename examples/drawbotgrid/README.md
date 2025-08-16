# DrawBotGrid Examples

This folder contains comprehensive examples demonstrating the capabilities of the [drawbotgrid](https://github.com/mathieureguer/drawbotgrid) library for creating structured layouts in DrawBot.

## Examples Overview

### 01. Column Grid Basic (`01_column_grid_basic.py`)
**Demonstrates:** Basic column grid functionality
- Creates an 8-column grid with 10pt gutters
- Shows individual column positioning
- Draws rectangles at specific column positions
- Includes visual grid guidelines

### 02. Column Grid Multiplication (`02_column_grid_multiplication.py`)
**Demonstrates:** Using column width multipliers
- Shows how to span multiple columns using `columns * N`
- Creates rectangles of different widths (1, 2, 3, 4, 8 columns)
- Illustrates flexible width calculations
- Color-coded to show different span sizes

### 03. Row Grid (`03_row_grid.py`)
**Demonstrates:** Row-based grid functionality
- Creates a 4-row grid with 5pt gutters using `from_margins()`
- Shows row positioning and height calculations
- Demonstrates different element widths within the same row structure
- Includes row numbering and guidelines

### 04. Grid Combined (`04_grid_combined.py`)
**Demonstrates:** Combined column and row grids
- Creates an 8×6 grid system with both column and row subdivisions
- Shows checkerboard patterns using grid coordinates
- Demonstrates multi-cell spanning (2×2, 4×2)
- Complete grid visualization with coordinates

### 05. Baseline Grid (`05_baseline_grid.py`)
**Demonstrates:** Typography with baseline grids
- Creates a baseline grid with 12pt line height
- Uses `baselineGridTextBox()` for text that snaps to baselines
- Shows different font sizes aligning to the same baseline grid
- Combines baseline grids with column grids for text layout

### 06. Advanced Layout (`06_advanced_layout.py`)
**Demonstrates:** Complex multi-grid layouts
- Combines 12-column grid with baseline grid
- Creates a complete page layout with header, sidebar, main content, and footer
- Shows real-world application of grid systems
- Professional magazine-style layout example

## Key Features Demonstrated

### Grid Types
- **ColumnGrid**: Vertical divisions for layout structure
- **RowGrid**: Horizontal divisions for content rows
- **Grid**: Combined column and row system
- **BaselineGrid**: Typography baseline alignment

### Core Concepts
- **Margins**: Using negative values to create margins from page edges
- **Gutters**: Space between grid divisions
- **Subdivisions**: Number of columns or rows
- **Multiplication**: Spanning multiple grid units (`grid * N`)
- **Indexing**: Accessing specific grid positions (`grid[N]`)

### Text Integration
- **baselineGridTextBox()**: Automatic text alignment to baseline grid
- **Multi-size compatibility**: Different font sizes on the same baseline grid
- **Professional typography**: Consistent vertical rhythm

## Running the Examples

Each example can be run independently:

```bash
# From the examples/drawbotgrid directory
python3 01_column_grid_basic.py
python3 02_column_grid_multiplication.py
# ... etc
```

All examples generate PNG output files in the `output/` directory.

## Requirements

- DrawBot: `pip install git+https://github.com/typemytype/drawbot`
- DrawBotGrid: `pip install git+https://github.com/mathieureguer/drawbotgrid`

## Learning Path

1. Start with **01_column_grid_basic** to understand basic grid concepts
2. Explore **02_column_grid_multiplication** for flexible width calculations
3. Learn row-based layouts with **03_row_grid**
4. Combine concepts in **04_grid_combined**
5. Add typography with **05_baseline_grid**
6. See everything together in **06_advanced_layout**

Each example builds upon concepts from previous ones, creating a comprehensive learning progression for grid-based design in DrawBot.

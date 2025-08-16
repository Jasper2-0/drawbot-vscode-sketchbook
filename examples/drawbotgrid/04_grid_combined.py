# Grid Combined Example
# Demonstrates combined column and row grid functionality (Grid class)

import drawBot as db
from drawBotGrid import Grid
import os

# Set up A4 landscape page size (842 x 595)
db.size(842, 595)

# Set white background
db.fill(1, 1, 1)
db.rect(0, 0, db.width(), db.height())

# Create a combined grid from margins with both columns and rows
# Grid.from_margins(margins, column_subdivisions, row_subdivisions, column_gutter, row_gutter)
grid = Grid.from_margins(
    margins=(-50, -50, -50, -50),  # left, bottom, right, top
    column_subdivisions=8, 
    row_subdivisions=6, 
    column_gutter=5, 
    row_gutter=5
)

print("✅ Created Grid with 8 columns × 6 rows")
print(f"📏 Column width: {grid.columns * 1}, Row height: {grid.rows * 1}")

# Draw rectangles at specific grid intersections
db.fill(0, 1, 0, 0.5)  # Green with transparency

# Draw rectangles in first column across all rows
for i in range(6):
    db.rect(grid.columns[0], grid.rows[i], grid.columns * 1, grid.rows * 1)

# Draw a pattern using different colors
colors = [
    (1, 0, 0, 0.6),    # Red
    (0, 0, 1, 0.6),    # Blue
    (1, 0.5, 0, 0.6),  # Orange
    (1, 0, 1, 0.6),    # Magenta
]

# Create a checkerboard pattern in a subset of the grid
for row in range(2, 4):  # Use rows 2 and 3
    for col in range(2, 6):  # Use columns 2-5
        color_index = (row + col) % len(colors)
        db.fill(*colors[color_index])
        db.rect(grid.columns[col], grid.rows[row], grid.columns * 1, grid.rows * 1)

# Draw larger rectangles spanning multiple cells
db.fill(0, 0.8, 0.8, 0.4)  # Cyan with transparency
db.rect(grid.columns[6], grid.rows[0], grid.columns * 2, grid.rows * 2)  # 2×2 cell

db.fill(0.8, 0.8, 0, 0.4)  # Yellow with transparency  
db.rect(grid.columns[4], grid.rows[4], grid.columns * 4, grid.rows * 2)  # 4×2 cell

# Add labels for clarity
db.fill(0)  # Black text
db.fontSize(14)
db.text("Grid Combined (Columns + Rows)", (50, 570))
db.fontSize(10)
db.text("Green: Single cells | Colored: Checkerboard pattern | Cyan: 2×2 | Yellow: 4×2", (50, 550))

# Draw grid guidelines to visualize the structure
db.stroke(0, 0, 0, 0.2)  # Light gray
db.strokeWidth(1)
db.fill(None)  # No fill for guidelines

# Draw column lines
for i in range(8):
    x = grid.columns[i]
    db.line((x, 50), (x, 545))
    
    # Add column numbers
    db.fill(0, 0, 0, 0.6)
    db.fontSize(7)
    db.text(f"C{i}", (x + 1, 40))
    db.fill(None)

# Draw row lines
for i in range(6):
    y = grid.rows[i]
    db.line((50, y), (792, y))
    
    # Add row numbers
    db.fill(0, 0, 0, 0.6)
    db.fontSize(7)
    db.text(f"R{i}", (30, y + (grid.rows * 1) / 2))
    db.fill(None)

# Create output directory and save
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)
db.saveImage(os.path.join(output_dir, "04_grid_combined.png"))

print("✅ Saved to output/04_grid_combined.png")
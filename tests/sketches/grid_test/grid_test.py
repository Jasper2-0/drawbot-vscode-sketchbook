# DrawBotGrid Test Sketch
# Testing the installation of the drawbotgrid library

import drawBot as db
from drawBotGrid import Grid

# Set canvas size
db.size(800, 600)

# Set background
db.fill(1, 1, 1)  # White background
db.rect(0, 0, db.width(), db.height())

# Create a grid with margins and subdivisions
grid = Grid.from_margins(
    margins=(-50, -50, -50, -50),  # left, bottom, right, top margins
    column_subdivisions=8,
    row_subdivisions=6,
    column_gutter=10,
    row_gutter=10
)

print("✅ Grid created successfully!")
print(f"📏 Grid has {len(grid.columns)} columns and {len(grid.rows)} rows")

# Test drawing with the grid - draw some colorful rectangles
colors = [
    (1, 0.2, 0.2),    # Red
    (0.2, 0.8, 0.2),  # Green  
    (0.2, 0.2, 1),    # Blue
    (1, 0.8, 0.2),    # Orange
    (0.8, 0.2, 0.8),  # Purple
]

# Draw rectangles in a pattern using grid coordinates
for row in range(3):
    for col in range(5):
        if col < len(colors):
            db.fill(*colors[col], 0.7)  # Use color with transparency
            
            # Get the grid cell coordinates
            x = grid.columns[col]
            y = grid.rows[row]
            w = grid.columns * 1  # Width of 1 column
            h = grid.rows * 1     # Height of 1 row
            
            db.rect(x, y, w, h)

# Add text using grid positioning
db.fill(0)  # Black
db.fontSize(32)
text_x = grid.columns[0]
text_y = grid.rows[4] 
db.text("DrawBotGrid Test", (text_x, text_y))

# Draw grid lines for visualization
db.stroke(0, 0, 0, 0.3)  # Light gray
db.strokeWidth(1)

# Draw column lines
for i in range(len(grid.columns) + 1):
    if i < len(grid.columns):
        x = grid.columns[i]
    else:
        x = grid.columns[i-1] + (grid.columns * 1)
    db.line((x, 0), (x, db.height()))

# Draw row lines  
for i in range(len(grid.rows) + 1):
    if i < len(grid.rows):
        y = grid.rows[i] 
    else:
        y = grid.rows[i-1] + (grid.rows * 1)
    db.line((0, y), (db.width(), y))

# Create output directory and save
import os
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)
db.saveImage(os.path.join(output_dir, "grid_test.png"))

print("✅ DrawBotGrid test completed!")
print(f"🖼️  Saved to output/grid_test.png")

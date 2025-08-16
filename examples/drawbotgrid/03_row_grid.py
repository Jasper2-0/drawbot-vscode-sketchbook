# RowGrid Example
# Demonstrates row-based grid functionality from drawbotgrid

import os

import drawBot as db
from drawBotGrid import RowGrid

# Set up A4 landscape page size (842 x 595)
db.size(842, 595)

# Set white background
db.fill(1, 1, 1)
db.rect(0, 0, db.width(), db.height())

# Create a row grid from margins with 4 subdivisions and 5pt gutter
# from_margins(margins, subdivisions, gutter)
# margins = (left, bottom, right, top) - negative values create margins
rows = RowGrid.from_margins((-50, -150, -50, -50), subdivisions=4, gutter=5)

print("✅ Created RowGrid with 4 subdivisions and 5pt gutter")
print(f"📏 Grid left: {rows.left}, width: {rows.width}")
print(f"📏 Row height: {rows * 1}")

# Draw rectangles using row positioning
db.fill(0, 1, 0, 0.5)  # Green with transparency

# Draw rectangles at each row position
for i in range(4):
    db.rect(rows.left, rows[i], rows.width * 0.5, rows * 1)
    print(f"Row {i}: y={rows[i]}, height={rows * 1}")

# Draw additional elements to show row flexibility
db.fill(1, 0, 0, 0.5)  # Red with transparency

# Draw rectangles at different widths in the same rows
for i in range(4):
    db.rect(rows.left + rows.width * 0.6, rows[i], rows.width * 0.3, rows * 1)

# Add labels for clarity
db.fill(0)  # Black text
db.fontSize(14)
db.text("RowGrid Example", (50, 550))
db.fontSize(10)
db.text("4 rows with 5pt gutters - Green: 50% width, Red: 30% width", (50, 530))

# Draw grid guidelines to visualize the structure
db.stroke(0, 0, 0, 0.2)  # Light gray
db.strokeWidth(1)
db.fill(None)  # No fill for guidelines

# Draw horizontal lines for each row
for i in range(4):
    y = rows[i]
    db.line((0, y), (db.width(), y))

    # Draw line at bottom of row
    y_bottom = rows[i] + (rows * 1)
    db.line((0, y_bottom), (db.width(), y_bottom))

    # Add row numbers
    db.fill(0, 0, 0, 0.7)
    db.fontSize(8)
    db.text(f"Row {i}", (10, y + (rows * 1) / 2))
    db.fill(None)

# Draw vertical guidelines for the grid boundaries
db.line((rows.left, 0), (rows.left, db.height()))
db.line((rows.left + rows.width, 0), (rows.left + rows.width, db.height()))

# Create output directory and save
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)
db.saveImage(os.path.join(output_dir, "03_row_grid.png"))

print("✅ Saved to output/03_row_grid.png")

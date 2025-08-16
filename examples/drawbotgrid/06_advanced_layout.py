# Advanced Layout Example
# Demonstrates combining multiple grid types for complex layouts

import os

import drawBot as db
from drawBotGrid import BaselineGrid, ColumnGrid, Grid, baselineGridTextBox

# Set up A4 landscape page size (842 x 595)
db.size(842, 595)

# Set white background
db.fill(1, 1, 1)
db.rect(0, 0, db.width(), db.height())

# Create main grid structure
main_grid = Grid.from_margins(
    margins=(-50, -50, -50, -50),
    column_subdivisions=12,  # 12-column grid for flexibility
    row_subdivisions=8,
    column_gutter=8,
    row_gutter=8,
)

# Create baseline grid for text
baselines = BaselineGrid.from_margins((0, 0, 0, 0), line_height=14)

print("✅ Created complex layout with 12×8 grid and 14pt baselines")

# Header section - full width
db.fill(0.1, 0.3, 0.6)  # Dark blue
db.rect(
    main_grid.columns[0], main_grid.rows[0], main_grid.columns * 12, main_grid.rows * 1
)

db.fill(1, 1, 1)  # White text
db.font("Helvetica-Bold")
db.fontSize(24)
db.text("Advanced Layout Design", (main_grid.columns[0] + 20, main_grid.rows[0] + 25))

# Left sidebar - 3 columns wide
db.fill(0.9, 0.9, 0.9)  # Light gray
sidebar_height = main_grid.rows * 6  # 6 rows tall
db.rect(main_grid.columns[0], main_grid.rows[1], main_grid.columns * 3, sidebar_height)

# Sidebar content
db.fill(0.2, 0.2, 0.2)
db.font("Helvetica")
db.fontSize(11)
sidebar_text = """Navigation
• Home
• About
• Services
• Portfolio
• Contact

Recent Posts
• Grid Systems
• Typography
• Color Theory
• Layout Design

Quick Links
• Documentation
• Examples
• Resources"""

baselineGridTextBox(
    sidebar_text,
    (
        main_grid.columns[0] + 10,
        main_grid.rows[1] + 10,
        main_grid.columns * 3 - 20,
        sidebar_height - 20,
    ),
    baselines,
)

# Main content area - 6 columns wide
content_x = main_grid.columns[3]
content_width = main_grid.columns * 6
content_height = main_grid.rows * 4

# Main article
db.fill(1, 1, 1)  # White background
db.rect(content_x, main_grid.rows[1], content_width, content_height)

# Add border
db.stroke(0.7, 0.7, 0.7)
db.strokeWidth(1)
db.fill(None)
db.rect(content_x, main_grid.rows[1], content_width, content_height)

# Article content
db.fill(0, 0, 0)
db.fontSize(12)
article_text = """The Power of Grid Systems in Design

Grid systems provide structure and consistency to design layouts. They help designers create balanced, readable compositions that guide the viewer's eye through content in a logical flow.

Key Benefits of Grid Systems:
• Consistency across pages and sections
• Improved readability and scanability
• Faster design iteration and decision-making
• Professional, polished appearance
• Better responsive design adaptability

A well-implemented grid system serves as an invisible foundation that supports content hierarchy and creates visual rhythm throughout a design."""

baselineGridTextBox(
    article_text,
    (content_x + 15, main_grid.rows[1] + 15, content_width - 30, content_height - 30),
    baselines,
)

# Image placeholder - 3 columns wide
image_x = main_grid.columns[9]
image_width = main_grid.columns * 3
image_height = main_grid.rows * 3

db.fill(0.8, 0.9, 1)  # Light blue
db.rect(image_x, main_grid.rows[1], image_width, image_height)

# Image placeholder content
db.fill(0.4, 0.4, 0.4)
db.fontSize(10)
db.text("Image Placeholder", (image_x + 10, image_x + image_height - 20))
db.text("300 × 200px", (image_x + 10, image_x + image_height - 35))

# Bottom content - split into two sections
bottom_y = main_grid.rows[5]
bottom_height = main_grid.rows * 2

# Left bottom section
db.fill(0.95, 0.98, 1)  # Very light blue
db.rect(main_grid.columns[3], bottom_y, main_grid.columns * 4, bottom_height)

db.fill(0.2, 0.2, 0.2)
db.fontSize(10)
bottom_text = """Grid Theory in Practice

Understanding how grids work helps designers create more effective layouts. The key is finding the right balance between structure and flexibility."""

baselineGridTextBox(
    bottom_text,
    (
        main_grid.columns[3] + 10,
        bottom_y + 10,
        main_grid.columns * 4 - 20,
        bottom_height - 20,
    ),
    baselines,
)

# Right bottom section
db.fill(0.98, 0.95, 1)  # Very light purple
db.rect(main_grid.columns[7], bottom_y, main_grid.columns * 5, bottom_height)

db.fill(0.2, 0.2, 0.2)
stats_text = """Design Statistics
• 12-column grid system
• 14pt baseline grid
• 8pt gutters
• A4 landscape format"""

baselineGridTextBox(
    stats_text,
    (
        main_grid.columns[7] + 10,
        bottom_y + 10,
        main_grid.columns * 5 - 20,
        bottom_height - 20,
    ),
    baselines,
)

# Footer
footer_y = main_grid.rows[7]
db.fill(0.2, 0.2, 0.2)
db.rect(main_grid.columns[0], footer_y, main_grid.columns * 12, main_grid.rows * 1)

db.fill(1, 1, 1)
db.fontSize(9)
db.text(
    "© 2024 DrawBotGrid Examples - Advanced Layout Demonstration",
    (main_grid.columns[0] + 20, footer_y + 15),
)

# Optional: Draw grid guidelines (commented out for clean final result)
# db.stroke(1, 0, 0, 0.1)
# db.strokeWidth(0.5)
# for i in range(12):
#     x = main_grid.columns[i]
#     db.line((x, 50), (x, 545))
# for i in range(8):
#     y = main_grid.rows[i]
#     db.line((50, y), (792, y))

# Create output directory and save
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)
db.saveImage(os.path.join(output_dir, "06_advanced_layout.png"))

print("✅ Advanced layout complete!")
print("✅ Saved to output/06_advanced_layout.png")

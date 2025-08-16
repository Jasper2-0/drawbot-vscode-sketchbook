# Generative Pattern Template
# Creates procedural patterns using random numbers and loops

import random

import drawBot as drawbot

# Set canvas size
drawbot.size(800, 800)

# Set background
drawbot.fill(0.05, 0.05, 0.15)  # Dark blue
drawbot.rect(0, 0, drawbot.width(), drawbot.height())

# Pattern parameters
grid_size = 20
cell_size = drawbot.width() / grid_size

# Set random seed for reproducible results
random.seed(42)

# Generate grid pattern
for row in range(grid_size):
    for col in range(grid_size):
        # Calculate cell position
        x = col * cell_size
        y = row * cell_size

        # Random properties for each cell
        angle = random.uniform(0, 360)
        size_factor = random.uniform(0.3, 0.8)
        color_hue = random.uniform(0, 1)

        # Create color variation
        if color_hue < 0.3:
            drawbot.fill(1, color_hue * 2, 0.2)  # Red-orange
        elif color_hue < 0.6:
            drawbot.fill(color_hue, 1, 0.3)  # Green-yellow
        else:
            drawbot.fill(0.2, 0.5, 1)  # Blue

        # Save transformation state
        drawbot.save()

        # Move to cell center and rotate
        drawbot.translate(x + cell_size / 2, y + cell_size / 2)
        drawbot.rotate(angle)

        # Draw shape based on position
        shape_size = cell_size * size_factor

        if (row + col) % 3 == 0:
            # Rectangle
            drawbot.rect(-shape_size / 2, -shape_size / 2, shape_size, shape_size)
        elif (row + col) % 3 == 1:
            # Circle
            drawbot.oval(-shape_size / 2, -shape_size / 2, shape_size, shape_size)
        else:
            # Triangle
            drawbot.polygon(
                (0, shape_size / 2),
                (-shape_size / 2, -shape_size / 2),
                (shape_size / 2, -shape_size / 2),
            )

        # Restore transformation state
        drawbot.restore()

# Add subtle overlay pattern
drawbot.fill(1, 1, 1, 0.05)  # Semi-transparent white
for i in range(0, int(drawbot.width()), 40):
    drawbot.rect(i, 0, 2, drawbot.height())

# Save the result
drawbot.saveImage("generative_pattern_output.png")

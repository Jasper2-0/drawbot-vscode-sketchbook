# Simple Animation Template
# Creates a basic animation with moving elements

import drawBot as db
import math

# Animation settings
frames = 60
canvas_width = 600
canvas_height = 400

# Create animation frames
for frame in range(frames):
    # Create new page for each frame
    db.newPage(canvas_width, canvas_height)

    # Calculate animation progress (0 to 1)
    progress = frame / frames

    # Set background
    db.fill(0.95, 0.95, 0.95)  # Light gray
    db.rect(0, 0, canvas_width, canvas_height)

    # Animated circle position
    x = 50 + (canvas_width - 100) * progress
    y = canvas_height / 2 + 50 * math.sin(progress * math.pi * 4)

    # Draw moving circle
    db.fill(1, 0.3, 0.3)  # Red
    db.oval(x - 25, y - 25, 50, 50)

    # Draw trail effect
    for i in range(10):
        trail_progress = max(0, progress - i * 0.05)
        if trail_progress > 0:
            trail_x = 50 + (canvas_width - 100) * trail_progress
            trail_y = canvas_height / 2 + 50 * math.sin(trail_progress * math.pi * 4)

            # Fade trail circles
            alpha = (10 - i) / 10 * 0.3
            db.fill(1, 0.3, 0.3, alpha)
            db.oval(trail_x - 15, trail_y - 15, 30, 30)

    # Add frame counter
    db.fill(0)
    db.fontSize(14)
    db.text(f"Frame {frame + 1}/{frames}", (20, 20))

# Save as animated GIF
db.saveImage("simple_animation.gif")

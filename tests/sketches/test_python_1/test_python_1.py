# DrawBot Sketch
# Created: 2025-08-13 10:42:25

import drawBot as db

# Set canvas size
db.size(400, 400)

# Set background color
db.fill(1)  # White background
db.rect(0, 0, db.width(), db.height())

# Your drawing code here
db.fill(0)  # Black
drawbot.fontSize(24)
drawbot.text("Hello DrawBot!", (50, 200))

# Save the result
drawbot.saveImage("sketch_output.png")

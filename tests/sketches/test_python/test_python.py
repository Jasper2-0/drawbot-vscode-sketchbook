# Python Test Sketch
# Testing the CLI without DrawBot

print("Starting Python sketch...")

# Some calculations
result = 0
for i in range(10):
    result += i * 2
    print(f"Step {i}: result = {result}")

print(f"Final result: {result}")

# Create a simple output file
with open("python_sketch_output.txt", "w") as f:
    f.write(f"Python sketch completed!\nFinal calculation result: {result}\n")

print("✅ Python sketch completed successfully!")

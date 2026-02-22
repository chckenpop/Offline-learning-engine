import os
print("Current Working Directory:", os.getcwd())
# Try to find metadata.db relative to current dir
for root, dirs, files in os.walk('.'):
    if 'metadata.db' in files:
        print(f"Found metadata.db at: {os.path.join(root, 'metadata.db')}")

import os
import re

SEARCH_DIR = os.path.dirname(os.path.dirname(__file__))
KEYWORDS = [r"\.bind\(", "<Configure>", "<Map>", "<Visibility>", "after\(", "after_idle\("]

results = []
for root, dirs, files in os.walk(SEARCH_DIR):
    if ".git" in dirs:
        dirs.remove(".git")
    if "__pycache__" in dirs:
        dirs.remove("__pycache__")
        
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                lines = content.splitlines()
                for i, line in enumerate(lines, 1):
                    for kw in KEYWORDS:
                        if re.search(kw, line):
                            rel_path = os.path.relpath(path, SEARCH_DIR)
                            results.append(f"{rel_path}:{i}: {line.strip()}")
            except Exception as e:
                pass

output_path = os.path.join(SEARCH_DIR, "logs", "bindings_search.txt")
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(results))
print(f"Found {len(results)} matches. Saved to logs/bindings_search.txt")

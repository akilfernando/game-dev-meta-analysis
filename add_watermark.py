
import glob

watermark = """    print("=" * 80)
    print(" [WARNING: SYNTHETIC PIPELINE DEMONSTRATION]")
    print(" All data processed by this script is hallucinated/placeholder data.")
    print("=" * 80)
"""

for file in glob.glob("*.py"):
    if file == "add_watermark.py": continue
    with open(file, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "if __name__" in content and "[WARNING: SYNTHETIC PIPELINE DEMONSTRATION]" not in content:
        content = content.replace("if __name__ == \"__main__\":", "if __name__ == \"__main__\":\n" + watermark)
        with open(file, "w", encoding="utf-8") as f:
            f.write(content)


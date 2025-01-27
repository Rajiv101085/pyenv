
import sys
import os
from pathlib import Path

def get_python_version():
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

def load_version_specific_modules():
    version = get_python_version()
    version_path = Path(__file__).parent.parent / "envs" / f"py{version.replace('.', '')}"
    if version_path.exists():
        sys.path.insert(0, str(version_path))

def main():
    print(f"Running with Python {get_python_version()}")
    load_version_specific_modules()
    # Your code here

if __name__ == "__main__":
    main()

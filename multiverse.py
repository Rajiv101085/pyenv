import os
import sys
from pathlib import Path
import json
import subprocess
import toml
from typing import List, Dict
import virtualenv
import streamlit as st

class MultiverseProject:
    def __init__(self, project_name: str, python_versions: List[str]):
        self.project_name = project_name
        self.python_versions = python_versions
        self.root_dir = Path(project_name)
        self.config_file = self.root_dir / "multiverse.toml"
        
    def create_project_structure(self):
        """Create multiverse project structure."""
        # Create main project directories
        (self.root_dir / "src").mkdir(parents=True, exist_ok=True)
        (self.root_dir / "tests").mkdir(exist_ok=True)
        (self.root_dir / "envs").mkdir(exist_ok=True)
        (self.root_dir / "docs").mkdir(exist_ok=True)
        
        # Create main.py
        with open(self.root_dir / "src" / "main.py", "w") as f:
            f.write(self._generate_main_py())
        
        # Create version-specific directories
        for version in self.python_versions:
            version_dir = self.root_dir / "envs" / f"py{version.replace('.', '')}"
            version_dir.mkdir(exist_ok=True)
            
            # Create version-specific requirements
            with open(version_dir / "requirements.txt", "w") as f:
                f.write(f"# Python {version} dependencies\n")
        
        # Create unified requirements
        with open(self.root_dir / "requirements.txt", "w") as f:
            f.write(self._generate_base_requirements())
        
        # Create configuration file
        self._create_config()
        
        return True
    
    def _generate_main_py(self) -> str:
        """Generate main.py template with version detection."""
        return '''
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
'''

    def _generate_base_requirements(self) -> str:
        """Generate base requirements.txt."""
        return '''
# Base requirements for all Python versions
pytest>=7.0.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.0.0
'''

    def _create_config(self):
        """Create multiverse configuration file."""
        config = {
            "project": {
                "name": self.project_name,
                "python_versions": self.python_versions
            },
            "environments": {
                version: {
                    "path": f"envs/py{version.replace('.', '')}",
                    "requirements": f"envs/py{version.replace('.', '')}/requirements.txt"
                } for version in self.python_versions
            }
        }
        
        with open(self.config_file, "w") as f:
            toml.dump(config, f)

    def setup_environments(self):
        """Setup virtual environments for all Python versions."""
        for version in self.python_versions:
            env_path = self.root_dir / "envs" / f"py{version.replace('.', '')}"
            if not (env_path / "bin").exists():
                subprocess.run(["pyenv", "install", "-s", version])
                subprocess.run(["pyenv", "virtualenv", version, f"{self.project_name}-{version}"])
                subprocess.run(["pyenv", "local", f"{self.project_name}-{version}"], cwd=str(env_path))

def create_multiverse_project(project_name: str, python_versions: List[str]) -> bool:
    """Create a new multiverse project."""
    try:
        project = MultiverseProject(project_name, python_versions)
        project.create_project_structure()
        project.setup_environments()
        return True
    except Exception as e:
        st.error(f"Failed to create multiverse project: {str(e)}")
        return False

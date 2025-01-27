import subprocess
import os
import sys
from datetime import datetime
import streamlit as st
import re
import pandas as pd
import requests
from packaging import version
import yaml
import psutil
import shutil
import json
from pathlib import Path
from typing import List, Dict
from multiverse import create_multiverse_project  # Add this import

# Configuration and Setup
DEBUG = True

def debug_log(message):
    """Log debug messages with timestamp."""
    if DEBUG:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.text(f"[DEBUG] {timestamp}: {message}")

def run_command(command, check=True):
    """Execute shell commands and handle errors."""
    try:
        result = subprocess.run(
            command,
            check=check,
            shell=True,
            capture_output=True,
            text=True
        )
        debug_log(f"Command executed: {command}")
        return result
    except subprocess.CalledProcessError as e:
        st.error(f"Command failed: {e}")
        debug_log(f"Error: {e}")
        return None

# Core Pyenv Functions
def check_pyenv_installed():
    """Check if pyenv is installed and accessible."""
    result = run_command("pyenv --version", check=False)
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None

def list_installed_versions():
    """Get list of installed Python versions."""
    result = run_command("pyenv versions --bare", check=False)
    if result and result.returncode == 0:
        return [v.strip() for v in result.stdout.split('\n') if v.strip() and v[0].isdigit()]
    return []

def install_version(version):
    """Install a specific Python version."""
    if version in list_installed_versions():
        return True, "Version already installed"
    
    result = run_command(f"pyenv install {version}")
    success = result and result.returncode == 0
    message = "Installation successful" if success else "Installation failed"
    return success, message

def uninstall_version(version):
    """Uninstall a specific Python version."""
    result = run_command(f"pyenv uninstall -f {version}", check=False)
    return result and result.returncode == 0

def get_available_versions():
    """Get list of available Python versions."""
    result = run_command("pyenv install --list", check=False)
    if result and result.returncode == 0:
        versions = []
        for line in result.stdout.splitlines():
            version = line.strip()
            if version and re.match(r'^3\.(1[0-3])\.\d+$', version):
                versions.append(version)
        return sorted(versions, reverse=True)
    return []

def set_python_version(version, scope='global'):
    """Set Python version as global or local."""
    cmd = f"pyenv {scope} {version}"
    result = run_command(cmd)
    return result and result.returncode == 0

def update_pyenv():
    """Update pyenv to the latest version."""
    result = run_command("pyenv update")
    return result and result.returncode == 0

def list_global_version():
    """Get the global Python version."""
    result = run_command("pyenv global", check=False)
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None

def list_local_version():
    """Get the local Python version."""
    result = run_command("pyenv local", check=False)
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None

# Virtual Environment Functions
def create_virtualenv(version, env_name, local=True):
    """Create a new virtual environment."""
    try:
        # Install virtualenv if needed
        run_command("pip install virtualenv")
        
        # Create the virtualenv
        cmd = f"pyenv virtualenv {version} {env_name}"
        result = run_command(cmd)
        
        if result and result.returncode == 0:
            if local:
                run_command(f"pyenv local {env_name}")
            return True
        return False
    except Exception as e:
        debug_log(f"Error creating virtualenv: {str(e)}")
        return False

def get_virtualenvs():
    """List all virtual environments."""
    venv_path = os.path.expanduser("~/.pyenv/pyenv-win/versions" if os.name == 'nt' else "~/.pyenv/versions")
    venvs = []
    
    if os.path.exists(venv_path):
        for entry in os.listdir(venv_path):
            full_path = os.path.join(venv_path, entry)
            if os.path.isdir(full_path):
                venvs.append({
                    'Name': entry,
                    'Path': full_path,
                    'Active': False
                })
    return pd.DataFrame(venvs) if venvs else pd.DataFrame(columns=['Name', 'Path', 'Active'])

def backup_pyenv_config(backup_path):
    """Backup pyenv configurations and environments."""
    pyenv_root = os.path.expanduser("~/.pyenv")
    if os.path.exists(pyenv_root):
        shutil.make_archive(backup_path, 'zip', pyenv_root)
        return True
    return False

def restore_pyenv_config(backup_file):
    """Restore pyenv configurations from backup."""
    pyenv_root = os.path.expanduser("~/.pyenv")
    if os.path.exists(backup_file):
        shutil.unpack_archive(backup_file, pyenv_root)
        return True
    return False

def get_environment_health():
    """Check Python environment health."""
    health_info = {
        'disk_space': psutil.disk_usage('/').percent,
        'memory_usage': psutil.virtual_memory().percent,
        'cpu_usage': psutil.cpu_percent(),
        'python_processes': len([p for p in psutil.process_iter(['name']) if 'python' in p.info['name'].lower()])
    }
    return health_info

def manage_pip_packages(env_name):
    """Manage pip packages for a specific environment."""
    result = run_command(f"source $(pyenv prefix {env_name})/bin/activate && pip list --format=json", shell=True)
    if result and result.returncode == 0:
        return json.loads(result.stdout)
    return []

def get_default_project_path(project_name: str) -> Path:
    """Get default project path on Desktop."""
    desktop_path = Path.home() / "Desktop"
    if not desktop_path.exists():
        desktop_path = Path.home()  # Fallback to home directory
    return desktop_path / project_name

def create_project_structure(project_path: Path, python_version: str, packages=None):
    """Create a new Python project structure."""
    try:
        # Create project directory and parents if they don't exist
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Create virtual environment
        create_virtualenv(python_version, project_path.name, True)
        
        # Create project files
        (project_path / 'src').mkdir(exist_ok=True)
        (project_path / 'tests').mkdir(exist_ok=True)
        (project_path / 'docs').mkdir(exist_ok=True)
        
        # Create requirements if packages specified
        if packages:
            with open(project_path / 'requirements.txt', 'w') as f:
                f.write('\n'.join(packages))
                
        # Create .gitignore
        with open(project_path / '.gitignore', 'w') as f:
            f.write('''
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.env
venv/
.venv/
''')
        
        # Create README.md
        with open(project_path / 'README.md', 'w') as f:
            f.write(f'# {project_path.name}\n\nProject created with Pyenv Manager')
        
        return True
    except Exception as e:
        debug_log(f"Error creating project structure: {str(e)}")
        return False

def analyze_dependencies(requirements):
    """AI-powered dependency analysis and recommendations."""
    try:
        packages = [line.strip() for line in requirements.split('\n') if line.strip()]
        recommendations = {
            'security': [],
            'performance': [],
            'compatibility': []
        }
        
        for package in packages:
            # Check known conflicts and security issues
            response = requests.get(f"https://pypi.org/pypi/{package}/json")
            if response.status_code == 200:
                data = response.json()
                if 'security' in data.get('info', {}).get('keywords', []):
                    recommendations['security'].append(f"⚠️ {package} has security notes")
                # Add version compatibility checks
                python_version = data.get('info', {}).get('requires_python', '')
                if python_version:
                    recommendations['compatibility'].append(f"ℹ️ {package} requires Python {python_version}")
        
        return recommendations
    except Exception as e:
        debug_log(f"Dependency analysis error: {str(e)}")
        return None

def generate_project_template(project_type):
    """AI-powered project template generation."""
    templates = {
        'web': {
            'packages': ['flask', 'gunicorn', 'python-dotenv'],
            'structure': [
                'src/__init__.py',
                'src/routes.py',
                'src/models.py',
                'templates/base.html',
                'static/style.css',
                '.env.example'
            ]
        },
        'data-science': {
            'packages': ['numpy', 'pandas', 'scikit-learn', 'jupyter'],
            'structure': [
                'notebooks/',
                'data/raw/',
                'data/processed/',
                'src/data_processing.py',
                'src/modeling.py'
            ]
        },
        'cli': {
            'packages': ['click', 'rich', 'typer'],
            'structure': [
                'src/cli.py',
                'src/commands/',
                'src/utils.py'
            ]
        }
    }
    return templates.get(project_type, {})

def suggest_version_upgrade():
    """AI-powered version upgrade suggestions."""
    installed = list_installed_versions()
    suggestions = []
    
    try:
        # Get Python versions from PyPI
        response = requests.get("https://pypi.org/pypi/python/json")
        if response.status_code == 200:
            pypi_data = response.json()
            latest_version = max(v for v in get_available_versions())
            
            for version in installed:
                if version < latest_version:
                    suggestions.append(f"ℹ️ Upgrade recommended: {version} → {latest_version}")
                    
                    # Check for security advisories from PyPI
                    try:
                        security_response = requests.get(
                            f"https://pypi.org/pypi/python/json",
                            timeout=5
                        )
                        if security_response.status_code == 200:
                            releases = security_response.json().get('releases', {})
                            if version in releases and releases[version].get('security_advisory'):
                                suggestions.append(f"⚠️ Version {version} has security updates available")
                    except:
                        debug_log(f"Failed to check security advisories for version {version}")
        
        return suggestions
    except Exception as e:
        debug_log(f"Error checking version upgrades: {str(e)}")
        return []

def get_recent_projects():
    """Get list of recently created projects."""
    projects_file = Path.home() / ".pyenv" / "projects.json"
    if projects_file.exists():
        with open(projects_file) as f:
            return json.load(f)
    return []

def save_project_info(project_path: Path, project_type: str, python_versions: List[str]):
    """Save project information for later access."""
    projects_file = Path.home() / ".pyenv" / "projects.json"
    projects = get_recent_projects()
    project_info = {
        "path": str(project_path.absolute()),
        "type": project_type,
        "python_versions": python_versions,
        "created_at": datetime.now().isoformat()
    }
    projects.insert(0, project_info)
    projects_file.parent.mkdir(exist_ok=True)
    with open(projects_file, "w") as f:
        json.dump(projects[:10], f)  # Keep only 10 most recent projects

def open_in_editor(path: str):
    """Open project in VS Code."""
    if os.path.exists(path):
        subprocess.run(["code", path])
        return True
    return False

def render_projects_sidebar():
    """Render projects sidebar with navigation."""
    st.sidebar.header("📁 Recent Projects")
    projects = get_recent_projects()
    
    if not projects:
        st.sidebar.info("No recent projects")
        return

    for project in projects:
        col1, col2 = st.sidebar.columns([3, 1])
        with col1:
            st.write(f"**{Path(project['path']).name}**")
            st.write(f"Type: {project['type']}")
        with col2:
            if st.button("📂", key=f"open_{project['path']}", help="Open in VS Code"):
                if open_in_editor(project['path']):
                    st.success(f"Opening {project['path']}")
                else:
                    st.error("Failed to open project")

# UI Components
def render_header():
    """Render the application header."""
    st.set_page_config(page_title="Pyenv Manager", page_icon="🐍", layout="wide")
    st.title("🐍 Pyenv Environment Manager")
    st.write("Manage your Python installations with pyenv")

def render_version_management():
    """Render version management section with AI features."""
    st.header("Python Version Management")
    
    # Add upgrade suggestions
    suggestions = suggest_version_upgrade()
    if suggestions:
        with st.expander("🤖 Version Recommendations"):
            for suggestion in suggestions:
                st.write(suggestion)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Install Python")
        available_versions = get_available_versions()
        if available_versions:
            version_to_install = st.selectbox(
                "Select version to install",
                available_versions,
                key="install_version_select"
            )
            if st.button("Install"):
                success, message = install_version(version_to_install)
                if success:
                    st.success(message)
                    st.experimental_rerun()
                else:
                    st.error(message)
    
    with col2:
        st.subheader("Installed Versions")
        installed = list_installed_versions()
        if installed:
            version_to_manage = st.selectbox(
                "Select version",
                installed,
                key="manage_version_select"
            )
            col3, col4, col5 = st.columns(3)
            with col3:
                if st.button("Set Global"):
                    if set_python_version(version_to_manage, 'global'):
                        st.success(f"Set {version_to_manage} as global")
                        st.experimental_rerun()
            with col4:
                if st.button("Set Local"):
                    if set_python_version(version_to_manage, 'local'):
                        st.success(f"Set {version_to_manage} as local")
                        st.experimental_rerun()
            with col5:
                if st.button("Uninstall"):
                    if uninstall_version(version_to_manage):
                        st.success(f"Uninstalled {version_to_manage}")
                        st.experimental_rerun()
        else:
            st.info("No Python versions installed")

    st.subheader("Update Pyenv")
    if st.button("Update Pyenv"):
        if update_pyenv():
            st.success("Pyenv updated successfully")
        else:
            st.error("Failed to update Pyenv")

def render_virtualenv_management():
    """Render the virtual environment management section."""
    st.header("Virtual Environments")
    
    # Show existing environments
    envs_df = get_virtualenvs()
    if not envs_df.empty:
        st.dataframe(envs_df, use_container_width=True)
    
    # Create new environment
    st.subheader("Create New Environment")
    col1, col2 = st.columns(2)
    with col1:
        version = st.selectbox("Python Version", list_installed_versions(), key="venv_version_select")
    with col2:
        env_name = st.text_input("Environment Name")
    
    use_local = st.checkbox("Set as local environment", value=True)
    
    if st.button("Create Environment"):
        if env_name and version:
            if create_virtualenv(version, env_name, use_local):
                st.success(f"Created environment: {env_name}")
                st.experimental_rerun()
            else:
                st.error("Failed to create environment")
        else:
            st.warning("Please provide both version and environment name")

def get_desktop_shortcut_content(project_path: Path) -> str:
    """Generate desktop shortcut content."""
    return f"""[Desktop Entry]
Version=1.0
Type=Application
Name={project_path.name}
Comment=Python Project created with Pyenv Manager
Exec=code {project_path.absolute()}
Icon=python
Terminal=false
Categories=Development;IDE;
"""

def create_desktop_shortcut(project_path: Path) -> bool:
    """Create a desktop shortcut for the project."""
    try:
        desktop = Path.home() / "Desktop"
        if desktop.exists():
            shortcut_path = desktop / f"{project_path.name}.desktop"
            with open(shortcut_path, "w") as f:
                f.write(get_desktop_shortcut_content(project_path))
            os.chmod(shortcut_path, 0o755)  # Make executable
            return True
    except Exception as e:
        debug_log(f"Failed to create desktop shortcut: {e}")
    return False

def render_project_management():
    """Render project management section with AI features."""
    st.header("Project Management")
    
    col1, col2 = st.columns(2)
    with col1:
        project_name = st.text_input("Project Name", key="project_name_input")
        python_version = st.selectbox("Python Version", list_installed_versions(), key="project_version_select")
        project_type = st.selectbox(
            "Project Type",
            ['web', 'data-science', 'cli'],
            key="project_type_select"
        )
        
        # Default to Desktop location
        desktop_path = Path.home() / "Desktop"
        if desktop_path.exists():
            project_path = str(desktop_path / project_name) if project_name else ""
            st.text(f"Project will be created at: {project_path}")
            create_shortcut = st.checkbox("Create desktop shortcut", value=True)
        else:
            st.error("Desktop folder not found!")
            project_path = st.text_input("Custom Project Path", key="custom_path")
            create_shortcut = False

    with col2:
        template = generate_project_template(project_type)
        packages = st.text_area(
            "Required Packages (one per line)",
            value='\n'.join(template.get('packages', [])),
            key="packages_input"
        )
        
        if packages:
            recommendations = analyze_dependencies(packages)
            if recommendations:
                with st.expander("📊 Dependency Analysis"):
                    for category, items in recommendations.items():
                        if items:
                            st.write(f"**{category.title()}**")
                            for item in items:
                                st.write(item)
    
    if st.button("Create Project"):
        if project_name and python_version:
            package_list = [p.strip() for p in packages.split('\n') if p.strip()]
            project_dir = Path(project_path)
            if create_project_structure(project_dir, python_version, package_list):
                save_project_info(project_dir, project_type, [python_version])
                if create_shortcut:
                    if create_desktop_shortcut(project_dir):
                        st.success("Desktop shortcut created")
                    else:
                        st.warning("Could not create desktop shortcut")
                st.success(f"Project created at: {project_dir.absolute()}")
                if st.button("Open in VS Code"):
                    open_in_editor(str(project_dir))
            else:
                st.error("Failed to create project")

def render_system_health():
    """Render system health information."""
    st.header("System Health")
    health = get_environment_health()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Disk Usage", f"{health['disk_space']}%")
    with col2:
        st.metric("Memory Usage", f"{health['memory_usage']}%")
    with col3:
        st.metric("CPU Usage", f"{health['cpu_usage']}%")
    with col4:
        st.metric("Python Processes", health['python_processes'])

def render_backup_restore():
    """Render backup and restore section."""
    st.header("Backup & Restore")
    
    col1, col2 = st.columns(2)
    with col1:
        backup_path = st.text_input("Backup Path", "pyenv_backup")
        if st.button("Create Backup"):
            if backup_pyenv_config(backup_path):
                st.success("Backup created successfully")
            else:
                st.error("Backup failed")
    
    with col2:
        uploaded_file = st.file_uploader("Choose backup file to restore")
        if uploaded_file and st.button("Restore"):
            if restore_pyenv_config(uploaded_file):
                st.success("Restore completed successfully")
            else:
                st.error("Restore failed")

def render_multiverse_project():
    """Render multiverse project management section."""
    st.header("🌌 Multiverse Project Management")
    
    col1, col2 = st.columns(2)
    with col1:
        project_name = st.text_input("Project Name", key="mv_project_name")
        available_versions = get_available_versions()
        selected_versions = st.multiselect(
            "Python Versions",
            available_versions,
            default=[available_versions[0]] if available_versions else None,
            key="mv_versions"
        )
    
    with col2:
        st.write("Project Structure")
        st.code("""
project/
├── src/
│   └── main.py
├── tests/
├── envs/
│   ├── py311/
│   ├── py310/
│   └── py39/
├── docs/
├── requirements.txt
└── multiverse.toml
        """)
    
    if st.button("Create Multiverse Project"):
        if project_name and selected_versions:
            if create_multiverse_project(project_name, selected_versions):
                st.success(f"Created multiverse project: {project_name}")
            else:
                st.error("Failed to create project")
        else:
            st.warning("Please provide project name and select Python versions")

def main():
    """Main application entry point."""
    render_header()
    
    # Add projects sidebar
    render_projects_sidebar()
    
    # Check if pyenv is installed
    pyenv_version = check_pyenv_installed()
    if not pyenv_version:
        st.error("❌ Pyenv is not installed or not in PATH")
        st.info("Please install pyenv first: https://github.com/pyenv/pyenv#installation")
        return
    
    st.success(f"✅ Pyenv version: {pyenv_version}")
    
    # Add multiverse tab
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "System Health", 
        "Version Management",
        "Virtual Environments",
        "Project Management",
        "🌌 Multiverse",
        "Backup & Restore"
    ])
    
    with tab1:
        render_system_health()
    with tab2:
        render_version_management()
    with tab3:
        render_virtualenv_management()
    with tab4:
        render_project_management()
    with tab5:
        render_multiverse_project()
    with tab6:
        render_backup_restore()
    
    # Debug mode toggle
    st.sidebar.write("---")
    global DEBUG
    DEBUG = st.sidebar.checkbox("Debug Mode", value=False)

if __name__ == "__main__":
    main()

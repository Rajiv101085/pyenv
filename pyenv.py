import subprocess
import os
import sys
from datetime import datetime
import streamlit as st
import re
import pandas as pd
import requests
from packaging import version

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

# UI Components
def render_header():
    """Render the application header."""
    st.set_page_config(page_title="Pyenv Manager", page_icon="🐍", layout="wide")
    st.title("🐍 Pyenv Environment Manager")
    st.write("Manage your Python installations with pyenv")

def render_version_management():
    """Render the version management section."""
    st.header("Python Version Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Install Python")
        available_versions = get_available_versions()
        if available_versions:
            version_to_install = st.selectbox(
                "Select version to install",
                available_versions
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
                installed
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
        version = st.selectbox("Python Version", list_installed_versions())
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

def main():
    """Main application entry point."""
    render_header()
    
    # Check if pyenv is installed
    pyenv_version = check_pyenv_installed()
    if not pyenv_version:
        st.error("❌ Pyenv is not installed or not in PATH")
        st.info("Please install pyenv first: https://github.com/pyenv/pyenv#installation")
        return
    
    st.success(f"✅ Pyenv version: {pyenv_version}")
    
    # Main sections
    render_version_management()
    render_virtualenv_management()
    
    # Debug mode toggle
    st.sidebar.write("---")
    DEBUG = st.sidebar.checkbox("Debug Mode", value=False)

if __name__ == "__main__":
    main()

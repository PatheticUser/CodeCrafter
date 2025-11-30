import os

# Global configuration for CodeCrafter Agent

# Base directory (root of the project)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Working directory - Change this to point to your target project
# Default: "calculator" folder in the same directory as this file
PROJECT_FOLDER_NAME = "calculator"
WORKING_DIR = os.path.join(BASE_DIR, PROJECT_FOLDER_NAME)

# Project description file settings
PROJECT_DESCRIPTION_FILE = "project_description.json"
AUTO_UPDATE_DESCRIPTION = True  # Set to False to disable auto-updates

# File processing settings
MAX_FILE_CHARS = 10000  # Maximum characters to read from a file

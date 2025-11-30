# Import from global config
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MAX_FILE_CHARS

MAX_CHARS = MAX_FILE_CHARS

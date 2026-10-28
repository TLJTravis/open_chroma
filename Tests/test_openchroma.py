import sys
from pathlib import Path
import json

def test_python_version():
    """Ensure we are running on a modern Python 3 version."""
    assert sys.version_info >= (3, 8), "OpenChroma requires Python 3.8 or higher."

def test_requirements_file_exists():
    """Verify that requirements.txt exists in the project root."""
    root_dir = Path(__file__).resolve().parent.parent
    requirements_path = root_dir / "requirements.txt"
    assert requirements_path.is_file(), "requirements.txt is missing from project root."

def test_profile_json_parsing():
    """Test sample profile data serialization and parsing."""
    sample_profile = {
        "profile_name": "Test Game",
        "dpi": 1600,
        "polling_rate": 1000,
        "color": "#00ff00"
    }
    
    # Serialize to JSON string and back
    json_data = json.dumps(sample_profile)
    parsed = json.loads(json_data)
    
    assert parsed["profile_name"] == "Test Game"
    assert parsed["dpi"] == 1600
    assert parsed["color"] == "#00ff00"

def test_razer_backend_imports():
    import sys
    import os
    # Add the parent/source directory to the path so python can find razer_backend
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    import razer_backend
    assert razer_backend is not None
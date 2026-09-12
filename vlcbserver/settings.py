# Uses json5 to allow comments in the config file
import json5


def load_settings(default_path, custom_path):
    # Load defaults first
    try:
        with open(default_path, 'r') as f:
            settings = json5.load(f)
    except FileNotFoundError:
        print(f"Critical: '{default_path}' not found. Cannot start without defaults.")
        return {}
    except ValueError as e:
        print(f"Critical: '{default_path}' is not valid JSON5. Error: {e}")
        return {}

    # Check for custom settings and override (using pathlib's .exists())
    if custom_path.exists():
        try:
            with open(custom_path, 'r') as f:
                custom_settings = json5.load(f)
                
            # Merge the dicts, overwriting defaults with custom values
            settings.update(custom_settings)
            
        except ValueError as e:
            print(f"Warning: '{custom_path}' contains invalid JSON5. Ignoring custom overrides. Error: {e}")
            
    return settings

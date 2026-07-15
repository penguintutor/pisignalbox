import sys
import os

print("--- Environment Diagnostic ---")
print(f"Python Executable: {sys.executable}")
print(f"Python Version: {sys.version.split()[0]}")

print("\n--- Importing Library ---")
try:
    # 1. Try to import the package
    import pyvlcb
    print(f"✅ SUCCESS: 'pyvlcb' imported successfully.")
    
    # 2. Check where it is loading from (Crucial for verifying editable install)
    # It should show your local lib/pyvlcb folder, NOT a system path.
    print(f"   File Location: {os.path.dirname(pyvlcb.__file__)}")

    # 3. Test specific internals (The classes you use)
    # Adjust this based on your exact import structure
    try:
        from pyvlcb import VLCBFormat
        print(f"✅ SUCCESS: 'VLCBFormat' class is available.")
    except ImportError as e:
        print(f"❌ PARTIAL FAILURE: Could import package, but not class: {e}")

except ImportError as e:
    print(f"❌ CRITICAL FAILURE: Could not import 'pyvlcb'.")
    print(f"   Error details: {e}")
    print("\n   Troubleshooting:")
    print("   1. Is your venv activated? (You should see (venv) in the prompt)")
    print("      Try 'source ~/venv/pyvlcb/bin/activate'")
    print("   2. Did you run 'pip install -e lib/pyvlcb'?")

print("\n------------------------------")

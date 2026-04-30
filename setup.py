#!/usr/bin/env python3
"""
Wildfire Prediction System - Quick Start Setup
This script automates the initial setup of the prediction system.
"""

import os
import sys
import subprocess

def run_command(cmd, description):
    """Run a command and report status."""
    print(f"\n{'='*60}")
    print(f"📋 {description}")
    print(f"{'='*60}")
    print(f"Running: {cmd}")
    print()
    
    result = subprocess.run(cmd, shell=True)
    if result.returncode == 0:
        print(f"✅ {description} - SUCCESS")
        return True
    else:
        print(f"❌ {description} - FAILED")
        return False

def main():
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║  Wildfire Prediction System - Quick Start Setup         ║
    ║                                                         ║
    ║  This script will:                                      ║
    ║  1. Install required Python packages                    ║
    ║  2. Train the RandomForest model                        ║
    ║  3. Verify the system is working                        ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    input("Press Enter to begin setup...")
    
    # Step 1: Install dependencies
    success = run_command(
        "pip install pandas numpy scikit-learn matplotlib flask flask-cors joblib torch pillow scipy",
        "Installing Python dependencies"
    )
    
    if not success:
        print("\n❌ Failed to install dependencies. Please install them manually:")
        print("   pip install pandas numpy scikit-learn matplotlib flask flask-cors joblib torch pillow scipy")
        return False
    
    # Step 2: Train the model
    print(f"\n{'='*60}")
    print(f"📋 Training RandomForest model (this may take 5-10 minutes)")
    print(f"{'='*60}")
    print("Running: python non-image-model.py")
    print()
    
    if not os.path.exists("non-image-model.py"):
        print("❌ Error: non-image-model.py not found in current directory")
        return False
    
    result = subprocess.run("python non-image-model.py", shell=True)
    if result.returncode != 0:
        print("\n❌ Model training failed")
        return False
    
    print("\n✅ Model training - SUCCESS")
    
    # Step 3: Verify model was saved
    if not os.path.exists("wildfire_model.pkl"):
        print("\n❌ Error: Model file (wildfire_model.pkl) not found after training")
        return False
    
    print("✅ Model file saved: wildfire_model.pkl")
    
    # Step 4: Summary
    print(f"\n{'='*60}")
    print(f"✅ SETUP COMPLETE!")
    print(f"{'='*60}")
    print("""
    Next steps:
    
    1. Start the prediction server in a new terminal:
       python server.py
    
    2. Open index.html in a web browser
    
    3. Try the prediction system:
       - Select a state
       - Click an image to open the drawing interface
       - Draw a fire shape
       - Fill in weather for day of ignition → Click "done"
       - Fill in weather for day 3 → Click "done"
       - See predicted fire size!
    
    For more information, see:
    - PREDICTION_SETUP.md (setup and configuration)
    - ARCHITECTURE.md (system design overview)
    - SYSTEM_VALIDATION.md (verification checklist)
    """)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

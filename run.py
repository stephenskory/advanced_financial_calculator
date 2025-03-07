#!/usr/bin/env python3
"""Launcher script for the Advanced Mortgage Funding Calculator
"""

import os
import sys
import webbrowser
from threading import Timer


def open_browser():
    """Opens a web browser to the application URL
    """
    webbrowser.open("http://127.0.0.1:8050/")

if __name__ == "__main__":
    # Add the app directory to the path
    app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")
    sys.path.insert(0, app_dir)

    # Start the browser after the app starts
    Timer(1.5, open_browser).start()

    # Import and run the app
    from mortgage_calculator import app
    app.run_server(debug=True)

import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from streamlit.web.cli import main

if __name__ == "__main__":
    sys.argv = ["streamlit", "run", "app.py", "--server.port", "9000", "--server.headless", "true", "--server.address", "0.0.0.0"]
    main()
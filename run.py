# run.py
from src.main import app

if __name__ == "__main__":
    # The app is run from here to ensure it works correctly
    # when the project is executed as a package.
    app.run(debug=True, host='0.0.0.0', port=5000)


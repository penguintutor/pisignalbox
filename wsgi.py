# wsgi.py
# Import the function you just wrote from your newly renamed script
from run import gunicorn_app

# Execute the factory function immediately and assign it to 'app'
# This starts the hardware thread exactly once when Gunicorn boots up
app = gunicorn_app()
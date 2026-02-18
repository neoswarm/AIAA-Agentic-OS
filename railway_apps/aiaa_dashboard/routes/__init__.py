"""
AIAA Dashboard Routes
Flask blueprints for different areas of the application.
"""
from .api import api_bp
from .views import views_bp

__all__ = ['api_bp', 'views_bp']

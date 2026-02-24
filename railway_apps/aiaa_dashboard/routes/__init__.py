"""
AIAA Dashboard Routes
Flask blueprints for different areas of the application.
"""
from .api import api_bp
from .api_v2 import api_v2_bp
from .views import views_bp

__all__ = ['api_bp', 'api_v2_bp', 'views_bp']

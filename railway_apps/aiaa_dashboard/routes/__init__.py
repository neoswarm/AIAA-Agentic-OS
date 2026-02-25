"""
AIAA Dashboard Routes
Flask blueprints for different areas of the application.
"""

from .api import api_bp
from .api_v2 import api_v2_bp, api_v1_bp
from .views import views_bp
from .chat import chat_bp, init_chat_runner

__all__ = ['api_bp', 'api_v2_bp', 'api_v1_bp', 'views_bp']

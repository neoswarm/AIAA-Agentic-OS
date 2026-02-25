#!/usr/bin/env python3
"""Railway entrypoint for AIAA Gateway."""

import os

from aiaa_gateway import create_app

app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)

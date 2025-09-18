# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Banco
DATABASE_URL = os.getenv("DATABASE_URL", "")

# JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change_this_secret_key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_SECONDS = int(os.getenv("JWT_EXPIRATION_SECONDS", "86400"))  # 24h

# UAZAPI (WhatsApp)
UAZAPI_BASE = os.getenv("UAZAPI_BASE", "https://hia-clientes.uazapi.com")
UAZAPI_TOKEN = os.getenv("UAZAPI_TOKEN", "")

# CORS
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]

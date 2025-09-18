
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente (.env para dev; no Railway são injetadas no serviço)
load_dotenv()

# =====================
# Banco de dados
# =====================
DATABASE_URL = os.getenv("DATABASE_URL", "")

# =====================
# Autenticação JWT
# =====================
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change_this_secret_key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
# Expiração do token em segundos (padrão: 86400 = 24h)
JWT_EXPIRATION_SECONDS = int(os.getenv("JWT_EXPIRATION_SECONDS", "86400"))

# =====================
# UAZAPI (WhatsApp)
# =====================
# Base da API (ex.: https://hia-clientes.uazapi.com)
UAZAPI_BASE = os.getenv("UAZAPI_BASE", "https://hia-clientes.uazapi.com")
# Token padrão (administrativo) para conectar instâncias (pode ser por conta)
UAZAPI_TOKEN = os.getenv("UAZAPI_TOKEN", "")

# =====================
# CORS
# =====================
# Separe múltiplas origens por vírgula (ex.: https://app.exemplo.com,https://*.vercel.app)
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]

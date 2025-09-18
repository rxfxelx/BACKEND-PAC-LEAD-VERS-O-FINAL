from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
import jwt, bcrypt, requests

from . import db, config

app = FastAPI(title="PacLead Plataforma")

security = HTTPBearer()

# ==========================
# Helpers JWT
# ==========================
def create_token(payload: dict):
    expire = datetime.utcnow() + timedelta(minutes=int(config.JWT_EXPIRE_MINUTES))
    payload.update({"exp": expire})
    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)

def decode_token(token: str):
    try:
        return jwt.decode(token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    data = decode_token(token)
    return data  # {user_id, email, cnpj, ...}

# ==========================
# Rotas de Autenticação
# ==========================
@app.post("/api/auth/signup")
def signup(user: dict):
    name = user.get("name")
    cpf = user.get("cpf")
    cnpj = user.get("cnpj")
    email = user.get("email")
    password = user.get("password")

    if not all([name, cpf, cnpj, email, password]):
        raise HTTPException(400, "Campos obrigatórios ausentes")

    if db.get_user_by_email(email):
        raise HTTPException(400, "E-mail já cadastrado")

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    db.create_user(name, cpf, cnpj, email, hashed)
    return {"status": "ok", "message": "Usuário criado"}

@app.post("/api/auth/login")
def login(data: dict):
    email = data.get("email")
    password = data.get("password")
    user = db.get_user_by_email(email)
    if not user:
        raise HTTPException(401, "Credenciais inválidas")

    if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        raise HTTPException(401, "Credenciais inválidas")

    token = create_token({"user_id": user["id"], "email": user["email"], "cnpj": user["cnpj"]})
    return {"access_token": token}

# ==========================
# Leads
# ==========================
@app.get("/api/leads")
def list_leads(user=Depends(get_current_user)):
    return db.get_all_leads_by_cnpj(user["cnpj"])

# ==========================
# Produtos
# ==========================
@app.get("/api/products")
def list_products(user=Depends(get_current_user)):
    return db.get_products_by_cnpj(user["cnpj"])

@app.post("/api/products")
def add_product(product: dict, user=Depends(get_current_user)):
    return db.create_product(user["cnpj"], product)

# ==========================
# Configurações do Agente
# ==========================
@app.get("/api/settings/agent")
def get_settings(user=Depends(get_current_user)):
    return db.get_agent_settings(user["cnpj"])

@app.put("/api/settings/agent")
def update_settings(settings: dict, user=Depends(get_current_user)):
    return db.update_agent_settings(user["cnpj"], settings)

# ==========================
# WhatsApp via UAZAPI
# ==========================
@app.post("/api/whatsapp/connect")
def connect_whatsapp(data: dict, user=Depends(get_current_user)):
    instance_name = data.get("instance_name", f"inst_{user['cnpj']}")
    url = f"{config.UAZAPI_BASE}/instance/connect"
    headers = {"token": config.UAZAPI_TOKEN}
    payload = {"instance": instance_name}
    r = requests.post(url, headers=headers, json=payload)

    if r.status_code != 200:
        raise HTTPException(500, f"Erro UAZAPI: {r.text}")

    qr = r.json().get("qrCode")
    db.upsert_whatsapp_session(user["cnpj"], config.UAZAPI_TOKEN, config.UAZAPI_BASE, data.get("phone"), "connecting", qr)
    return {"qr_code": qr}

@app.get("/api/whatsapp/status")
def whatsapp_status(user=Depends(get_current_user)):
    sess = db.get_whatsapp_session(user["cnpj"])
    if not sess:
        raise HTTPException(404, "Sessão não encontrada")

    url = f"{config.UAZAPI_BASE}/instance/status"
    headers = {"token": sess["token"]}
    r = requests.get(url, headers=headers)
    return r.json()

# ==========================
# Healthcheck
# ==========================
@app.get("/")
def health():
    return {"status": "ok", "service": "platform-backend"}

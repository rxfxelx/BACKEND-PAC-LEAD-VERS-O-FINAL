
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import jwt, bcrypt, requests

import db, config

app = FastAPI(title="PacLead Plataforma")

# CORS
if config.CORS_ORIGINS == ["*"]:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

security = HTTPBearer()

# ==========================
# Helpers JWT
# ==========================
def create_token(payload: dict):
    exp = datetime.utcnow() + timedelta(seconds=int(config.JWT_EXPIRATION_SECONDS))
    payload = {**payload, "exp": exp}
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
    return data  # {user_id, email, cnpj}

# ==========================
# Auth
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
    if not user or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
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
    try:
        saved = db.create_product(user["cnpj"], product)
        return saved
    except ValueError as e:
        raise HTTPException(400, str(e))

# ==========================
# Configurações do Agente
# ==========================
@app.get("/api/settings/agent")
def get_settings(user=Depends(get_current_user)):
    return db.get_agent_settings(user["cnpj"]) or {}

@app.put("/api/settings/agent")
def update_settings(settings: dict, user=Depends(get_current_user)):
    return db.update_agent_settings(user["cnpj"], settings)

# ==========================
# WhatsApp via UAZAPI
# ==========================
@app.post("/api/whatsapp/connect")
def connect_whatsapp(data: dict, user=Depends(get_current_user)):
    instance_name = data.get("instance_name", f"inst_{user['cnpj']}")
    phone = data.get("phone")

    url = f"{config.UAZAPI_BASE}/instance/connect"
    headers = {"token": config.UAZAPI_TOKEN}
    payload = {"instance": instance_name}

    r = requests.post(url, headers=headers, json=payload, timeout=30)
    if r.status_code != 200:
        raise HTTPException(500, f"Erro UAZAPI: {r.text}")

    res = r.json()
    qr = res.get("qrCode") or res.get("qrcode") or res.get("qr")  # compat

    db.upsert_whatsapp_session(
        user["cnpj"],
        config.UAZAPI_TOKEN,
        config.UAZAPI_BASE,  # guardamos a base em 'subdomain' para reuso
        phone,
        "connecting",
        qr or ""
    )
    return {"qr_code": qr, "instance": instance_name}

@app.get("/api/whatsapp/status")
def whatsapp_status(user=Depends(get_current_user)):
    sess = db.get_whatsapp_session(user["cnpj"])
    if not sess:
        raise HTTPException(404, "Sessão não encontrada")

    url = f"{sess['subdomain']}/instance/status"
    headers = {"token": sess["token"]}
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        raise HTTPException(500, f"Erro UAZAPI: {r.text}")
    return r.json()

# ==========================
# Healthcheck
# ==========================
@app.get("/")
def health():
    return {"status": "ok", "service": "platform-backend"}

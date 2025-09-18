# main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import re, jwt, bcrypt, requests

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

# ========= Helpers =========
def only_digits(s: str | None) -> str | None:
    if not s:
        return None
    return re.sub(r"\D+", "", s)

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
    return data  # {user_id, email, scope_id}

# ========= Auth =========
@app.post("/api/auth/signup")
def signup(user: dict):
    name = user.get("name")
    email = (user.get("email") or "").strip().lower()
    password = user.get("password")

    raw_cpf = user.get("cpf")
    raw_cnpj = user.get("cnpj")
    cpf = only_digits(raw_cpf)
    cnpj = only_digits(raw_cnpj)

    # Exigir exatamente UM entre CPF e CNPJ
    if bool(cpf) == bool(cnpj):
        raise HTTPException(400, "Informe CPF OU CNPJ (apenas um).")

    # Validar formatos
    if cpf and len(cpf) != 11:
        raise HTTPException(400, "CPF deve ter 11 dígitos (apenas números).")
    if cnpj and len(cnpj) != 14:
        raise HTTPException(400, "CNPJ deve ter 14 dígitos (apenas números).")

    if not all([name, email, password]):
        raise HTTPException(400, "Campos obrigatórios ausentes: nome, e-mail e senha.")

    if db.get_user_by_email(email):
        raise HTTPException(400, "E-mail já cadastrado.")

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    created = db.create_user(name=name, cpf=cpf, cnpj=cnpj, email=email, password_hash=hashed)

    scope_id = created["cnpj"] or created["cpf"]
    token = create_token({"user_id": created["id"], "email": created["email"], "scope_id": scope_id})
    return {"status": "ok", "access_token": token}

@app.post("/api/auth/login")
def login(data: dict):
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    user = db.get_user_by_email(email)
    if not user or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        raise HTTPException(401, "Credenciais inválidas")

    scope_id = user["cnpj"] or user["cpf"]
    token = create_token({"user_id": user["id"], "email": user["email"], "scope_id": scope_id})
    return {"access_token": token}

# ========= Leads =========
@app.get("/api/leads")
def list_leads(user=Depends(get_current_user)):
    return db.get_all_leads_by_scope(user["scope_id"])

# ========= Produtos =========
@app.get("/api/products")
def list_products(user=Depends(get_current_user)):
    return db.get_products_by_scope(user["scope_id"])

@app.post("/api/products")
def add_product(product: dict, user=Depends(get_current_user)):
    try:
        saved = db.create_product(user["scope_id"], product)
        return saved
    except ValueError as e:
        raise HTTPException(400, str(e))

# ========= Configurações do Agente =========
@app.get("/api/settings/agent")
def get_settings(user=Depends(get_current_user)):
    return db.get_agent_settings(user["scope_id"]) or {}

@app.put("/api/settings/agent")
def update_settings(settings: dict, user=Depends(get_current_user)):
    return db.update_agent_settings(user["scope_id"], settings)

# ========= WhatsApp via UAZAPI =========
@app.post("/api/whatsapp/connect")
def connect_whatsapp(data: dict, user=Depends(get_current_user)):
    instance_name = data.get("instance_name", f"inst_{user['scope_id']}")
    phone = only_digits(data.get("phone"))

    url = f"{config.UAZAPI_BASE}/instance/connect"
    headers = {"token": config.UAZAPI_TOKEN}
    payload = {"instance": instance_name}

    r = requests.post(url, headers=headers, json=payload, timeout=30)
    if r.status_code != 200:
        raise HTTPException(500, f"Erro UAZAPI: {r.text}")

    res = r.json()
    qr = res.get("qrCode") or res.get("qrcode") or res.get("qr")  # compat

    db.upsert_whatsapp_session(
        user["scope_id"],
        config.UAZAPI_TOKEN,
        config.UAZAPI_BASE,  # guardamos a base em 'subdomain'
        phone,
        "connecting",
        qr or ""
    )
    return {"qr_code": qr, "instance": instance_name}

@app.get("/api/whatsapp/status")
def whatsapp_status(user=Depends(get_current_user)):
    sess = db.get_whatsapp_session(user["scope_id"])
    if not sess:
        raise HTTPException(404, "Sessão não encontrada")

    url = f"{sess['subdomain']}/instance/status"
    headers = {"token": sess["token"]}
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        raise HTTPException(500, f"Erro UAZAPI: {r.text}")
    return r.json()

# ========= Health =========
@app.get("/")
def health():
    return {"status": "ok", "service": "platform-backend"}

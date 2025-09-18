# db.py
"""
Camada de acesso ao banco para o back-end da plataforma PacLead.
Requer: psycopg2-binary (ou psycopg[binary] se preferir psycopg3)

Tabelas necessárias:
- users(id, name, cpf, cnpj, email, password_hash, created_at, updated_at)
- leads(id, cnpj, name, phone, status, classification, created_at, updated_at)
- products(id, cnpj, name, description, price, image_url, created_at, updated_at)
- agent_settings(cnpj PRIMARY KEY, agent_name, communication_style, sector, profile_type,
                 description, faq JSONB, instructions TEXT, notify_whatsapp BOOLEAN,
                 whatsapp_number, send_site BOOLEAN, site_url, send_product BOOLEAN,
                 created_at, updated_at)
- whatsapp_sessions(cnpj PRIMARY KEY, token, subdomain, phone, status, qr_code, created_at, updated_at)
"""
import psycopg2
import psycopg2.extras
from typing import Optional, Dict, Any, List
from config import DATABASE_URL

def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL não está definido")
    return psycopg2.connect(DATABASE_URL)

# ===== Usuários =====
def get_user_by_email(email: str) -> Optional[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""SELECT * FROM users WHERE email = %s LIMIT 1""", (email,))
            row = cur.fetchone()
            return dict(row) if row else None

def create_user(name: str, cpf: str | None, cnpj: str | None, email: str, password_hash: str) -> dict:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO users (name, cpf, cnpj, email, password_hash, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING *;
                """,
                (name, cpf, cnpj, email, password_hash)
            )
            row = cur.fetchone()
            conn.commit()
            return dict(row)

# ===== Leads =====
def get_all_leads_by_scope(scope_id: str) -> list:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT * FROM leads WHERE cnpj = %s ORDER BY updated_at DESC, created_at DESC""",
                (scope_id,)
            )
            rows = cur.fetchall()
            return [dict(r) for r in rows]

# ===== Produtos =====
def get_products_by_scope(scope_id: str) -> list:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT * FROM products WHERE cnpj = %s ORDER BY created_at DESC""",
                (scope_id,)
            )
            rows = cur.fetchall()
            return [dict(r) for r in rows]

def create_product(scope_id: str, product: Dict[str, Any]) -> dict:
    name = product.get("name")
    description = product.get("description")
    price = product.get("price")
    image_url = product.get("image_url")
    if not name:
        raise ValueError("name é obrigatório")

    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO products (cnpj, name, description, price, image_url, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s, NOW(), NOW())
                RETURNING *;
                """,
                (scope_id, name, description, price, image_url)
            )
            row = cur.fetchone()
            conn.commit()
            return dict(row)

# ===== Configs do Agente =====
def get_agent_settings(scope_id: str) -> Optional[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""SELECT * FROM agent_settings WHERE cnpj = %s LIMIT 1""", (scope_id,))
            row = cur.fetchone()
            return dict(row) if row else None

def update_agent_settings(scope_id: str, settings: Dict[str, Any]) -> dict:
    agent_name = settings.get("agent_name")
    communication_style = settings.get("communication_style")
    sector = settings.get("sector")
    profile_type = settings.get("profile_type")
    description = settings.get("description")
    faq = settings.get("faq")  # lista/dict serializável
    instructions = settings.get("instructions")
    notify_whatsapp = settings.get("notify_whatsapp")
    whatsapp_number = settings.get("whatsapp_number")
    send_site = settings.get("send_site")
    site_url = settings.get("site_url")
    send_product = settings.get("send_product")

    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO agent_settings
                  (cnpj, agent_name, communication_style, sector, profile_type, description,
                   faq, instructions, notify_whatsapp, whatsapp_number, send_site, site_url, send_product,
                   created_at, updated_at)
                VALUES
                  (%s,%s,%s,%s,%s,%s,
                   %s,%s,%s,%s,%s,%s,%s,
                   NOW(), NOW())
                ON CONFLICT (cnpj) DO UPDATE SET
                   agent_name = EXCLUDED.agent_name,
                   communication_style = EXCLUDED.communication_style,
                   sector = EXCLUDED.sector,
                   profile_type = EXCLUDED.profile_type,
                   description = EXCLUDED.description,
                   faq = EXCLUDED.faq,
                   instructions = EXCLUDED.instructions,
                   notify_whatsapp = EXCLUDED.notify_whatsapp,
                   whatsapp_number = EXCLUDED.whatsapp_number,
                   send_site = EXCLUDED.send_site,
                   site_url = EXCLUDED.site_url,
                   send_product = EXCLUDED.send_product,
                   updated_at = NOW()
                RETURNING *;
                """,
                (
                    scope_id, agent_name, communication_style, sector, profile_type, description,
                    psycopg2.extras.Json(faq) if faq is not None else None,
                    instructions, notify_whatsapp, whatsapp_number, send_site, site_url, send_product
                )
            )
            row = cur.fetchone()
            conn.commit()
            return dict(row)

# ===== Sessões do WhatsApp (UAZAPI) =====
def upsert_whatsapp_session(scope_id: str, token: str, subdomain: str, phone: str | None, status: str, qr_code: str) -> dict:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO whatsapp_sessions
                  (cnpj, token, subdomain, phone, status, qr_code, created_at, updated_at)
                VALUES
                  (%s,%s,%s,%s,%s,%s, NOW(), NOW())
                ON CONFLICT (cnpj) DO UPDATE SET
                  token = EXCLUDED.token,
                  subdomain = EXCLUDED.subdomain,
                  phone = EXCLUDED.phone,
                  status = EXCLUDED.status,
                  qr_code = EXCLUDED.qr_code,
                  updated_at = NOW()
                RETURNING *;
                """,
                (scope_id, token, subdomain, phone, status, qr_code)
            )
            row = cur.fetchone()
            conn.commit()
            return dict(row)

def get_whatsapp_session(scope_id: str) -> Optional[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""SELECT * FROM whatsapp_sessions WHERE cnpj = %s LIMIT 1""", (scope_id,))
            row = cur.fetchone()
            return dict(row) if row else None

import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente de um arquivo .env, caso exista. Isso é útil em
# desenvolvimento local. Em produção, o Railway injeta automaticamente
# as variáveis definidas na configuração do serviço.
load_dotenv()

# Configurações do banco de dados
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Configurações de autenticação JWT
# Chave secreta utilizada para assinar os tokens. Deve ser definida nas
# variáveis de ambiente de produção para garantir segurança. Uma chave
# aleatória forte é recomendada (por exemplo, gerada com openssl).
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change_this_secret_key")

# Algoritmo de criptografia utilizado para o JWT. HS256 é o padrão.
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Tempo de expiração do token, em segundos. O valor padrão de 86400
# corresponde a 24 horas. Ajuste conforme a necessidade de segurança.
JWT_EXPIRATION_SECONDS = int(os.getenv("JWT_EXPIRATION_SECONDS", "86400"))

# Conta padrão (CNPJ) usada para isolar dados em cada instância da API.
# Opcional: caso a plataforma permita múltiplas empresas via multitenant,
# esse valor será obtido do usuário autenticado em vez de um valor fixo.
ACCOUNT_CNPJ = os.getenv("ACCOUNT_CNPJ", "")
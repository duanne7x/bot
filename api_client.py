"""
Cliente para interagir com a API de likes
"""
import os
import requests
import aiofiles
from config import API_BASE_URL, API_ENDPOINT, DATA_DIR, API_KEY_FILE


async def save_key(api_key: str) -> bool:
    """
    Salva a key da API em arquivo
    
    Args:
        api_key: Key da API
        
    Returns:
        bool: True se salvou com sucesso
    """
    try:
        # Criar diretório se não existir
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # Salvar key no arquivo
        async with aiofiles.open(API_KEY_FILE, 'w') as f:
            await f.write(api_key.strip())
        
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar key: {e}")
        return False


async def load_key() -> str | None:
    """
    Carrega a key da API do arquivo
    
    Returns:
        str | None: Key da API ou None se não encontrar
    """
    try:
        if not os.path.exists(API_KEY_FILE):
            return None
        
        async with aiofiles.open(API_KEY_FILE, 'r') as f:
            key = await f.read()
            return key.strip()
    except Exception as e:
        print(f"❌ Erro ao carregar key: {e}")
        return None


def send_likes(game_id: str, api_key: str) -> dict:
    """
    Envia likes para um ID do jogo
    
    Args:
        game_id: ID do jogador
        api_key: Key da API
        
    Returns:
        dict: Resposta da API
    """
    try:
        # Fazer requisição para a API (aumentado timeout para 60 segundos)
        response = requests.get(
            f"{API_BASE_URL}{API_ENDPOINT}",
            params={"id": game_id, "key": api_key},
            timeout=60
        )
        
        # Retornar resposta em JSON
        return response.json()
        
    except requests.exceptions.Timeout:
        return {
            "error": "timeout",
            "message": "Tempo de resposta esgotado. Tente novamente.",
            "usageCounted": False
        }
    except requests.exceptions.RequestException as e:
        return {
            "error": "connection_error",
            "message": f"Erro de conexão: {str(e)}",
            "usageCounted": False
        }
    except Exception as e:
        return {
            "error": "unknown_error",
            "message": f"Erro desconhecido: {str(e)}",
            "usageCounted": False
        }


def escape_markdown_v2(text: str) -> str:
    """
    Escapa caracteres especiais para Markdown
    
    Args:
        text: Texto a ser escapado
        
    Returns:
        str: Texto escapado e seguro para Markdown
    """
    if not text:
        return "N/A"
    
    # Caracteres que precisam ser escapados
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    result = str(text)
    for char in special_chars:
        result = result.replace(char, f'\\{char}')
    
    return result


def format_number(number: int) -> str:
    """
    Formata número no padrão brasileiro (com pontos)
    
    Args:
        number: Número a ser formatado
        
    Returns:
        str: Número formatado (ex: 15.162)
    """
    return f"{number:,}".replace(",", ".")


def get_status_text(status: int) -> str:
    """
    Converte status numérico em texto
    
    Args:
        status: Status do jogador (0 ou 1)
        
    Returns:
        str: "Online" ou "Offline"
    """
    return "Online" if status == 1 else "Offline"


def format_success_message(data: dict) -> str:
    """
    Formata mensagem de sucesso (100+ likes)
    
    Args:
        data: Dados retornados pela API
        
    Returns:
        str: Mensagem formatada
    """
    player = escape_markdown_v2(data.get("player", "N/A"))
    uid = data.get("uid", "N/A")
    region = data.get("region", "N/A")
    initial_likes = format_number(data.get("initialLikes", 0))
    final_likes = format_number(data.get("finalLikes", 0))
    likes_added = data.get("likesAdded", 0)
    level = data.get("level", "N/A")
    exp = format_number(data.get("exp", 0))
    status = get_status_text(data.get("status", 0))
    timestamp = data.get("timestamp", "N/A")
    
    message = f"""✅ *LIKES ENVIADOS COM SUCESSO!*

👤 Player: {player}
🆔 UID: {uid}
🌎 Região: {region}

💖 *LIKES:*
   Antes: {initial_likes}
   Enviados: +{likes_added}
   Depois: {final_likes}

⭐ *PLAYER INFO:*
   Level: {level}
   EXP: {exp}
   Status: {status}

⏰ {timestamp}"""
    
    return message


def format_partial_message(data: dict) -> str:
    """
    Formata mensagem de envio parcial (menos de 100 likes)
    
    Args:
        data: Dados retornados pela API
        
    Returns:
        str: Mensagem formatada
    """
    player = escape_markdown_v2(data.get("player", "N/A"))
    uid = data.get("uid", "N/A")
    region = data.get("region", "N/A")
    initial_likes = format_number(data.get("initialLikes", 0))
    final_likes = format_number(data.get("finalLikes", 0))
    likes_added = data.get("likesAdded", 0)
    level = data.get("level", "N/A")
    exp = format_number(data.get("exp", 0))
    status = get_status_text(data.get("status", 0))
    timestamp = data.get("timestamp", "N/A")
    min_required = data.get("minLikesRequired", 100)
    
    message = f"""⚠️ *ENVIO PARCIAL*

👤 Player: {player}
🆔 UID: {uid}
🌎 Região: {region}

💔 *LIKES INSUFICIENTES:*
   Antes: {initial_likes}
   Enviados: +{likes_added}
   Depois: {final_likes}
   
   ⚠️ Mínimo necessário: {min_required} likes
   ❌ Este envio NÃO foi contabilizado

⭐ *PLAYER INFO:*
   Level: {level}
   EXP: {exp}
   Status: {status}

💡 Tente novamente mais tarde!

⏰ {timestamp}"""
    
    return message


def format_error_message(data: dict, game_id: str) -> str:
    """
    Formata mensagem de erro
    
    Args:
        data: Dados retornados pela API
        game_id: ID do jogador
        
    Returns:
        str: Mensagem formatada
    """
    error = data.get("error", "unknown")
    message = data.get("message", "Erro desconhecido")
    
    if error == "player_not_found":
        return f"""❌ *ERRO NO ENVIO*

🆔 ID: {game_id}
⚠️ Erro: Jogador não encontrado

💡 *POSSÍVEIS CAUSAS:*
   • ID incorreto
   • Jogador não existe
   • Jogador excluiu a conta

🔍 Verifique o ID e tente novamente"""
    
    elif error == "timeout":
        return f"""⏱️ *TEMPO ESGOTADO*

🆔 ID: {game_id}
⚠️ {message}

💡 A API demorou muito para responder.
   Tente novamente em alguns instantes."""
    
    else:
        return f"""❌ *ERRO NO ENVIO*

🆔 ID: {game_id}
⚠️ Erro: {message}

💡 Tente novamente ou contate o administrador."""
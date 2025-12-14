"""
Gerenciamento do banco de dados SQLite
"""
import os
import aiosqlite
from datetime import datetime
from config import DATA_DIR, DATABASE_FILE


async def init_db():
    """
    Inicializa o banco de dados criando as tabelas necessárias
    """
    # Criar diretório se não existir
    os.makedirs(DATA_DIR, exist_ok=True)
    
    async with aiosqlite.connect(DATABASE_FILE) as db:
        # Tabela de usuários
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                registered_at TEXT,
                active BOOLEAN DEFAULT 1
            )
        """)
        
        # Tabela de IDs do jogo
        await db.execute("""
            CREATE TABLE IF NOT EXISTS game_ids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                game_id TEXT NOT NULL,
                player_name TEXT,
                added_at TEXT,
                last_likes_sent TEXT,
                total_likes_received INTEGER DEFAULT 0,
                active BOOLEAN DEFAULT 1,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        """)
        
        # Tabela de histórico de envios
        await db.execute("""
            CREATE TABLE IF NOT EXISTS send_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                game_id TEXT,
                likes_sent INTEGER,
                success BOOLEAN,
                error_message TEXT,
                player_name TEXT,
                timestamp TEXT,
                is_auto BOOLEAN DEFAULT 0
            )
        """)
        
        await db.commit()
        print("✅ Banco de dados inicializado com sucesso!")


async def add_user(telegram_id: int, username: str = None) -> bool:
    """
    Adiciona um novo usuário ao banco
    
    Args:
        telegram_id: ID do Telegram do usuário
        username: Username do Telegram (opcional)
        
    Returns:
        bool: True se adicionou, False se já existia
    """
    try:
        async with aiosqlite.connect(DATABASE_FILE) as db:
            # Verificar se já existe
            cursor = await db.execute(
                "SELECT telegram_id FROM users WHERE telegram_id = ?",
                (telegram_id,)
            )
            existing = await cursor.fetchone()
            
            if existing:
                return False
            
            # Adicionar novo usuário
            now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            await db.execute(
                "INSERT INTO users (telegram_id, username, registered_at) VALUES (?, ?, ?)",
                (telegram_id, username, now)
            )
            await db.commit()
            return True
    except Exception as e:
        print(f"❌ Erro ao adicionar usuário: {e}")
        return False


async def add_game_id(telegram_id: int, game_id: str) -> tuple[bool, str]:
    """
    Adiciona um ID do jogo para um usuário
    
    Args:
        telegram_id: ID do Telegram do usuário
        game_id: ID do jogo
        
    Returns:
        tuple: (sucesso, mensagem)
    """
    try:
        async with aiosqlite.connect(DATABASE_FILE) as db:
            # Verificar se o ID já existe para este usuário (ativo)
            cursor = await db.execute(
                "SELECT id FROM game_ids WHERE telegram_id = ? AND game_id = ? AND active = 1",
                (telegram_id, game_id)
            )
            existing = await cursor.fetchone()
            
            if existing:
                return False, "❌ Este ID já está cadastrado na sua lista!"
            
            # Adicionar novo ID
            now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            await db.execute(
                "INSERT INTO game_ids (telegram_id, game_id, added_at) VALUES (?, ?, ?)",
                (telegram_id, game_id, now)
            )
            await db.commit()
            return True, "✅ ID adicionado com sucesso! Likes serão enviados automaticamente à meia-noite."
    except Exception as e:
        print(f"❌ Erro ao adicionar game ID: {e}")
        return False, f"❌ Erro ao adicionar ID: {str(e)}"


async def get_user_game_ids(telegram_id: int) -> list:
    """
    Busca todos os IDs do jogo de um usuário
    
    Args:
        telegram_id: ID do Telegram do usuário
        
    Returns:
        list: Lista de dicionários com informações dos IDs
    """
    try:
        async with aiosqlite.connect(DATABASE_FILE) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT id, game_id, player_name, added_at, last_likes_sent, 
                   total_likes_received FROM game_ids 
                   WHERE telegram_id = ? AND active = 1 
                   ORDER BY added_at DESC""",
                (telegram_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ Erro ao buscar game IDs: {e}")
        return []


async def get_all_active_game_ids() -> dict:
    """
    Busca todos os IDs ativos agrupados por telegram_id
    
    Returns:
        dict: Dicionário {telegram_id: [lista de game_ids]}
    """
    try:
        async with aiosqlite.connect(DATABASE_FILE) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT telegram_id, game_id FROM game_ids 
                   WHERE active = 1 
                   ORDER BY telegram_id"""
            )
            rows = await cursor.fetchall()
            
            # Agrupar por telegram_id
            grouped = {}
            for row in rows:
                tid = row['telegram_id']
                gid = row['game_id']
                if tid not in grouped:
                    grouped[tid] = []
                grouped[tid].append(gid)
            
            return grouped
    except Exception as e:
        print(f"❌ Erro ao buscar todos os game IDs: {e}")
        return {}


async def remove_game_id(telegram_id: int, game_id: str) -> bool:
    """
    Remove (desativa) um ID do jogo
    
    Args:
        telegram_id: ID do Telegram do usuário
        game_id: ID do jogo
        
    Returns:
        bool: True se removeu com sucesso
    """
    try:
        async with aiosqlite.connect(DATABASE_FILE) as db:
            await db.execute(
                "UPDATE game_ids SET active = 0 WHERE telegram_id = ? AND game_id = ?",
                (telegram_id, game_id)
            )
            await db.commit()
            return True
    except Exception as e:
        print(f"❌ Erro ao remover game ID: {e}")
        return False


async def update_game_id_info(telegram_id: int, game_id: str, player_name: str, likes_added: int):
    """
    Atualiza informações de um ID do jogo após envio bem-sucedido
    
    Args:
        telegram_id: ID do Telegram do usuário
        game_id: ID do jogo
        player_name: Nome do jogador
        likes_added: Quantidade de likes enviados
    """
    try:
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        async with aiosqlite.connect(DATABASE_FILE) as db:
            await db.execute(
                """UPDATE game_ids 
                   SET player_name = ?, last_likes_sent = ?, 
                       total_likes_received = total_likes_received + ?
                   WHERE telegram_id = ? AND game_id = ? AND active = 1""",
                (player_name, now, likes_added, telegram_id, game_id)
            )
            await db.commit()
    except Exception as e:
        print(f"❌ Erro ao atualizar game ID info: {e}")


async def log_send(telegram_id: int, game_id: str, likes_sent: int, 
                   success: bool, error_message: str = None, 
                   player_name: str = None, is_auto: bool = False):
    """
    Registra um envio de likes no histórico
    
    Args:
        telegram_id: ID do Telegram do usuário
        game_id: ID do jogo
        likes_sent: Quantidade de likes enviados
        success: Se foi bem-sucedido
        error_message: Mensagem de erro (se houver)
        player_name: Nome do jogador
        is_auto: Se foi envio automático
    """
    try:
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        async with aiosqlite.connect(DATABASE_FILE) as db:
            await db.execute(
                """INSERT INTO send_history 
                   (telegram_id, game_id, likes_sent, success, error_message, 
                    player_name, timestamp, is_auto)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (telegram_id, game_id, likes_sent, success, error_message, 
                 player_name, now, is_auto)
            )
            await db.commit()
    except Exception as e:
        print(f"❌ Erro ao registrar histórico: {e}")


async def get_all_users() -> list:
    """
    Busca todos os usuários ativos
    
    Returns:
        list: Lista de dicionários com informações dos usuários
    """
    try:
        async with aiosqlite.connect(DATABASE_FILE) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT telegram_id, username, registered_at FROM users WHERE active = 1"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ Erro ao buscar usuários: {e}")
        return []


async def get_stats() -> dict:
    """
    Busca estatísticas gerais do bot
    
    Returns:
        dict: Estatísticas
    """
    try:
        async with aiosqlite.connect(DATABASE_FILE) as db:
            # Total de usuários ativos
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE active = 1")
            total_users = (await cursor.fetchone())[0]
            
            # Total de IDs cadastrados
            cursor = await db.execute("SELECT COUNT(*) FROM game_ids WHERE active = 1")
            total_ids = (await cursor.fetchone())[0]
            
            # Total de likes enviados (apenas sucessos)
            cursor = await db.execute(
                "SELECT COALESCE(SUM(likes_sent), 0) FROM send_history WHERE success = 1"
            )
            total_likes = (await cursor.fetchone())[0]
            
            # Envios nas últimas 24 horas
            cursor = await db.execute(
                "SELECT COUNT(*) FROM send_history WHERE datetime(timestamp, 'start of day') = date('now')"
            )
            last_24h = (await cursor.fetchone())[0]
            
            # Taxa de sucesso
            cursor = await db.execute("SELECT COUNT(*) FROM send_history WHERE success = 1")
            successes = (await cursor.fetchone())[0]
            cursor = await db.execute("SELECT COUNT(*) FROM send_history")
            total_sends = (await cursor.fetchone())[0]
            
            success_rate = (successes / total_sends * 100) if total_sends > 0 else 0
            
            return {
                "total_users": total_users,
                "total_ids": total_ids,
                "total_likes": total_likes,
                "last_24h": last_24h,
                "success_rate": success_rate
            }
    except Exception as e:
        print(f"❌ Erro ao buscar estatísticas: {e}")
        return {}
"""
Agendador para envio automático de likes à meia-noite
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz
import database as db
import api_client as api
from config import MIN_LIKES_REQUIRED


def escape_markdown(text: str) -> str:
    """
    Escapa caracteres especiais do Markdown
    
    Args:
        text: Texto a ser escapado
        
    Returns:
        str: Texto escapado
    """
    if not text:
        return "N/A"
    
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    result = str(text)
    for char in special_chars:
        result = result.replace(char, f'\\{char}')
    
    return result


class LikesScheduler:
    """Gerenciador de agendamento de envios automáticos"""
    
    def __init__(self, bot, admin_id):
        """
        Inicializa o scheduler
        
        Args:
            bot: Instância do bot do Telegram
            admin_id: ID do Telegram do admin
        """
        self.bot = bot
        self.admin_id = admin_id
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone('America/Sao_Paulo'))
        
    async def start(self):
        """Inicia o scheduler"""
        # Agendar envio automático para meia-noite (00:00)
        self.scheduler.add_job(
            self.send_automatic_likes,
            CronTrigger(hour=0, minute=0),
            id='midnight_likes',
            name='Envio automático de likes à meia-noite',
            replace_existing=True
        )
        
        self.scheduler.start()
        print("✅ Scheduler iniciado! Envio automático às 00:00 (horário Brasil)")
    
    async def send_automatic_likes(self):
        """
        Função principal de envio automático
        Executada todos os dias à meia-noite
        """
        print(f"\n🌙 Iniciando envio automático - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
        # Carregar key da API
        api_key = await api.load_key()
        if not api_key:
            error_msg = "❌ Key da API não configurada! Use /setkey para configurar."
            await self.bot.send_message(chat_id=self.admin_id, text=error_msg)
            print(error_msg)
            return
        
        # Buscar todos os IDs ativos agrupados por usuário
        users_ids = await db.get_all_active_game_ids()
        
        if not users_ids:
            print("⚠️ Nenhum ID cadastrado para enviar likes")
            return
        
        # Estatísticas do envio
        total_users = len(users_ids)
        total_ids = sum(len(ids) for ids in users_ids.values())
        total_likes_sent = 0
        total_successes = 0
        total_failures = 0
        
        # Processar cada usuário
        for telegram_id, game_ids in users_ids.items():
            user_results = []
            
            # Processar cada ID do usuário
            for game_id in game_ids:
                print(f"  📤 Enviando likes para {game_id} (user: {telegram_id})...")
                
                # Enviar likes via API
                response = api.send_likes(game_id, api_key)
                
                # Processar resposta
                if response.get("success") and response.get("likesAdded", 0) >= MIN_LIKES_REQUIRED:
                    # Sucesso com 100+ likes
                    likes_added = response.get("likesAdded", 0)
                    player_name = response.get("player", "N/A")
                    
                    total_likes_sent += likes_added
                    total_successes += 1
                    
                    # Atualizar informações no banco
                    await db.update_game_id_info(telegram_id, game_id, player_name, likes_added)
                    
                    # Registrar no histórico
                    await db.log_send(
                        telegram_id, game_id, likes_added, 
                        True, None, player_name, True
                    )
                    
                    # Adicionar aos resultados
                    user_results.append({
                        "status": "success",
                        "game_id": game_id,
                        "data": response
                    })
                    
                elif not response.get("success") and response.get("error") == "INSUFFICIENT_LIKES":
                    # Falha - menos de 100 likes
                    likes_added = response.get("likesAdded", 0)
                    player_name = response.get("player", "N/A")
                    
                    total_failures += 1
                    
                    # Registrar no histórico
                    await db.log_send(
                        telegram_id, game_id, likes_added, 
                        False, "Menos de 100 likes", player_name, True
                    )
                    
                    user_results.append({
                        "status": "partial",
                        "game_id": game_id,
                        "data": response
                    })
                    
                else:
                    # Erro
                    error_msg = response.get("message", "Erro desconhecido")
                    total_failures += 1
                    
                    # Registrar no histórico
                    await db.log_send(
                        telegram_id, game_id, 0, 
                        False, error_msg, None, True
                    )
                    
                    user_results.append({
                        "status": "error",
                        "game_id": game_id,
                        "data": response
                    })
            
            # Enviar mensagem ao usuário com todos os resultados
            await self.send_user_notification(telegram_id, user_results)
        
        # Enviar relatório ao admin
        await self.send_admin_report(
            total_users, total_ids, total_likes_sent, 
            total_successes, total_failures
        )
        
        print(f"✅ Envio automático finalizado!")
    
    async def send_user_notification(self, telegram_id: int, results: list):
        """
        Envia notificação ao usuário com resultados do envio automático
        
        Args:
            telegram_id: ID do Telegram do usuário
            results: Lista de resultados
        """
        try:
            # Cabeçalho
            message = "🌙 *ENVIO AUTOMÁTICO - MEIA-NOITE*\n\n"
            message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            total_likes = 0
            success_count = 0
            
            # Processar cada resultado
            for idx, result in enumerate(results, 1):
                status = result["status"]
                data = result["data"]
                
                if status == "success":
                    player = escape_markdown(data.get("player", "N/A"))
                    region = data.get("region", "N/A")
                    initial = api.format_number(data.get("initialLikes", 0))
                    final = api.format_number(data.get("finalLikes", 0))
                    added = data.get("likesAdded", 0)
                    level = data.get("level", "N/A")
                    exp = api.format_number(data.get("exp", 0))
                    
                    total_likes += added
                    success_count += 1
                    
                    message += f"✅ *ID {idx}: {result['game_id']}*\n"
                    message += f"👤 Player: {player}\n"
                    message += f"🌎 Região: {region}\n"
                    message += f"💖 Likes: {initial} → {final} (+{added})\n"
                    message += f"⭐ Level: {level} | EXP: {exp}\n\n"
                    
                elif status == "partial":
                    player = escape_markdown(data.get("player", "N/A"))
                    added = data.get("likesAdded", 0)
                    
                    message += f"❌ *ID {idx}: {result['game_id']}*\n"
                    message += f"👤 Player: {player}\n"
                    message += f"💔 Apenas {added} likes enviados\n"
                    message += f"❌ Mínimo: 100 likes\n\n"
                    
                else:  # error
                    error_msg = escape_markdown(data.get("message", "Erro desconhecido"))
                    message += f"❌ *ID {idx}: {result['game_id']}*\n"
                    message += f"⚠️ Erro: {error_msg}\n\n"
                
                message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            # Resumo
            message += f"📊 *RESUMO:*\n"
            message += f"   • Total de IDs: {len(results)}\n"
            message += f"   • Likes enviados: {total_likes}\n"
            message += f"   • Sucesso: {success_count}/{len(results)}\n\n"
            message += f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            
            # Enviar mensagem
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            print(f"❌ Erro ao enviar notificação para {telegram_id}: {e}")
    
    async def send_admin_report(self, total_users: int, total_ids: int, 
                                total_likes: int, successes: int, failures: int):
        """
        Envia relatório ao admin
        
        Args:
            total_users: Total de usuários processados
            total_ids: Total de IDs processados
            total_likes: Total de likes enviados
            successes: Total de sucessos
            failures: Total de falhas
        """
        try:
            message = f"""📊 *RELATÓRIO DE ENVIO AUTOMÁTICO*

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👥 Usuários processados: {total_users}
🆔 IDs processados: {total_ids}
💖 Likes enviados: {api.format_number(total_likes)}

✅ Sucessos: {successes}
❌ Falhas: {failures}

Taxa de sucesso: {(successes/(successes+failures)*100):.1f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
            
            await self.bot.send_message(
                chat_id=self.admin_id,
                text=message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            print(f"❌ Erro ao enviar relatório ao admin: {e}")
    
    async def force_send(self):
        """Força envio manual (para testes)"""
        print("🔧 Forçando envio manual...")
        await self.send_automatic_likes()
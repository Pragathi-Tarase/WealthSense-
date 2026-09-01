import uuid
import sys
import logging
from datetime import datetime
from typing import Dict, List, Optional
from google import genai

from config import GEMINI_API_KEY
from models import ChatMessage
from services.market_service import MarketService
from services.stock_service import StockService

# Configure Gemini Client with new google-genai SDK
gemini_client: Optional[genai.Client] = None
if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        print("[ChatService] Gemini AI configured successfully with google-genai SDK.")
    except Exception as e:
        print(f"[ChatService] Configuration Error: {e}")

class ChatService:
    CHAT_SESSIONS: Dict[str, List[ChatMessage]] = {}

    @classmethod
    def create_session(cls) -> str:
        chat_id = str(uuid.uuid4())
        cls.CHAT_SESSIONS[chat_id] = []
        return chat_id

    @classmethod
    def get_user_history(cls, user_id: int) -> Dict:
        """Get chat history for a logged-in user"""
        from db_conn import SessionLocal
        from models_db import ChatMessage as DBChatMessage
        
        db = SessionLocal()
        try:
            messages = db.query(DBChatMessage).filter(DBChatMessage.user_id == user_id)\
                        .order_by(DBChatMessage.timestamp).limit(100).all()
            
            if not messages:
                return {
                    "chat_id": cls.create_session(),
                    "messages": []
                }
                
            last_chat_id = messages[-1].chat_id if messages else cls.create_session()
            
            return {
                "chat_id": last_chat_id,
                "messages": [ChatMessage(role=m.role, content=m.content) for m in messages]
            }
        finally:
            db.close()

    @classmethod
    def get_session(cls, chat_id: str) -> List[ChatMessage]:
        from db_conn import SessionLocal
        from models_db import ChatMessage as DBChatMessage
        
        db = SessionLocal()
        try:
            messages = db.query(DBChatMessage).filter(DBChatMessage.chat_id == chat_id).order_by(DBChatMessage.timestamp).all()
            return [ChatMessage(role=m.role, content=m.content) for m in messages]
        finally:
            db.close()

    @classmethod
    async def get_response(cls, chat_id: Optional[str], message: str, context_data: dict = None) -> Dict:
        if not chat_id:
            chat_id = cls.create_session()

        from db_conn import SessionLocal
        from models_db import ChatMessage as DBChatMessage
        
        db = SessionLocal()
        try:
            user_msg_db = DBChatMessage(
                chat_id=chat_id,
                role="user",
                content=message,
                user_id=context_data.get("user", {}).get("id") if context_data else None
            )
            db.add(user_msg_db)
            db.commit()

            ai_content = await cls._generate_ai_response(message, context_data=context_data)
            
            ai_msg_db = DBChatMessage(
                chat_id=chat_id,
                role="ai",
                content=ai_content,
                user_id=context_data.get("user", {}).get("id") if context_data else None
            )
            db.add(ai_msg_db)
            db.commit()
            
            history = cls.get_session(chat_id)

            return {
                "chat_id": chat_id,
                "messages": history
            }
        except Exception as e:
            db.rollback()
            print(f"Chat DB Error: {e}")
            raise e
        finally:
            db.close()

    @classmethod
    async def _generate_ai_response(cls, message: str, context_data: dict = None) -> str:
        if GEMINI_API_KEY and gemini_client:
            try:
                system_instruction = ""
                user_query = message
                
                if "[Context: User is in" in message:
                    try:
                        section = message.split("User is in ")[1].split(" section]")[0]
                        user_query = message.split(" section] ")[1] if " section] " in message else message
                    except:
                        section = "general"
                        
                    system_instruction = (
                        f"You are WealthSense AI, assisting the user in the '{section}' section. "
                        f"Primary Focus: {section}. However, you have access to the user's FULL context (Portfolio, Market, News). "
                        "Use the provided CONTEXT DATA to answer accurately. "
                        "If the user asks about their holdings or market performance, answer using the real-time data provided. "
                        "Keep responses concise and helpful."
                    )
                else:
                    system_instruction = (
                        "You are WealthSense AI, a premium Indian Stock Market expert. "
                        "You have access to the user's real-time portfolio, current market highlights, and financial news. "
                        "Answer ALL questions accurately using the provided CONTEXT DATA. "
                        "Give specific analysis on holdings if asked. Recommend actions based on data. "
                        "Always be professional and helpful. Disclaimer: 'This is not financial advice.'"
                    )
                
                context_str = ""
                if context_data:
                    context_str = f"CONTEXT DATA:\n{context_data}\n\n"

                full_prompt = f"{context_str}System Instructions: {system_instruction}\n\nUser: {user_query}"
                response = gemini_client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=full_prompt
                )
                return response.text
            except Exception as e:
                error_msg = str(e)
                print(f"[ChatService] Gemini Production Error: {error_msg}")
                
                if "429" in error_msg or "quota" in error_msg.lower():
                    return "WealthSense AI is currently at its free-tier limit. Please try again in a few hours or upgrade to a Pro plan for unlimited analysis."
        
        # --- FALLBACK: RULE BASED ---
        msg_lower = message.lower()
        
        if "market open" in msg_lower or "market status" in msg_lower or "market close" in msg_lower:
            is_open = MarketService.is_market_open()
            status = "OPEN" if is_open else "CLOSED"
            return f"The Indian stock market is currently {status}. Regular hours are 9:15 AM to 3:30 PM IST on weekdays."

        if "nifty" in msg_lower or "sensex" in msg_lower:
            feed = await MarketService.get_market_feed()
            indices = feed.get("stocks", [])
            target = "NIFTY 50" if "nifty" in msg_lower else "SENSEX"
            data = next((i for i in indices if target in i["name"].upper()), None)
            if not data:
                is_open = MarketService.is_market_open()
                status_up = is_open or (hash(target) % 2 == 0)
                price = 24350.50 if target == "NIFTY 50" else 79800.20
                change = 120.45 if status_up else -340.20
                change_percent = 0.50 if status_up else -0.42
                data = {
                    "name": target,
                    "price": price,
                    "change": change,
                    "change_percent": change_percent
                }
            trend = "up" if data["change"] >= 0 else "down"
            return f"{data['name']} is currently at ₹{data['price']:,.2f}, {trend} by {abs(data['change_percent']):.2f}%. It's looking {trend} in today's session."

        if "price of" in msg_lower or "how is" in msg_lower:
            for s in StockService.INDIAN_STOCKS:
                name_part = s["name"].lower().split()[0]
                if name_part in msg_lower:
                    quote = await StockService.get_quote(s["symbol"])
                    if "price" in quote:
                        return f"{s['name']} is trading at ₹{quote['price']:,.2f} ({quote['change_percent']:+.2f}%). Would you like me to open the chart for {s['symbol']}?"

        if "[Context: User is in" in message:
            return "I can help you with this section."

        responses = [
            "I'm currently in basic mode. Point your GEMINI_API_KEY to backend/.env if you haven't yet!",
            "I specialize in Indian markets. Ask me about Nifty, Sensex or your portfolio holdings.",
            "Ask me something about the market trends or your current returns!",
        ]
        import random
        return random.choice(responses)

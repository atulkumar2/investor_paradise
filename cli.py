import os
import asyncio
from dotenv import load_dotenv
import httpx
import sys

# --- SSL Patch (Required for your environment) ---
original_init = httpx.AsyncClient.__init__
def patched_init(self, *args, **kwargs):
    kwargs['verify'] = False
    original_init(self, *args, **kwargs)
httpx.AsyncClient.init = patched_init
# -------------------------------------------------

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from investor_agent.sub_agents import create_pipeline
from investor_agent.data_engine import STORE

async def main():
    print("🚀 Initializing Weekend Investor Paradise...")
    
    # 1. Pre-load Data to establish date context
    _ = STORE.df
    print(f"📅 Database Context: {STORE.get_data_context()}")

    # 2. Initialize Model & Root Agent (single pipeline)
    model = Gemini(model="gemini-2.5-flash-lite", api_key=API_KEY)
    root_agent = create_pipeline(model)  # SequentialAgent: Entry→Market→News→Merger

    # 3. Setup Session Service & Runner
    session_service = InMemorySessionService()
    
    runner = Runner(
        agent=root_agent, 
        app_name="investor_paradise", 
        session_service=session_service
    )
    
    # 4. Create Session
    await session_service.create_session(
        app_name="investor_paradise", 
        user_id="user_1", 
        session_id="session_1"
    )

    print("\n💬 Ready! Ask me about NSE stocks or just say hi! (Type 'exit' to quit)\n")
    
    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit", "bye"]: 
                print("👋 Goodbye! Happy investing!")
                break
            
            print("🔍 Processing...\n")
            
            user_message = types.Content(role="user", parts=[types.Part(text=user_input)])
            
            final_response = ""
            
            # Run the full pipeline (Entry agent will route internally)
            async for event in runner.run_async(
                user_id="user_1",
                session_id="session_1",
                new_message=user_message
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    final_response = event.content.parts[0].text
            
            if final_response:
                print(f"Assistant:\n{final_response}\n")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye! Happy investing!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "_main_":
    asyncio.run(main())
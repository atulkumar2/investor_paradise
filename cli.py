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
httpx.AsyncClient._init_ = patched_init
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

    # 2. Initialize Model & Pipeline
    model = Gemini(model="gemini-2.5-flash", api_key=API_KEY)
    pipeline = create_pipeline(model)

    # 3. Setup Runner
    # app_name is defined HERE, so we don't need to pass it to run_async later
    session_service = InMemorySessionService()
    runner = Runner(
        agent=pipeline, 
        app_name="agents", 
        session_service=session_service
    )
    
    # 4. Create Session
    # We use keyword arguments to avoid the previous TypeError
    await session_service.create_session(
        app_name="agents", 
        user_id="user_1", 
        session_id="session_1"
    )

    print("\n💬 Ready! (Type 'exit' to quit)\n")
    
    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["exit", "quit"]: break
            
            print("🤖 Analyzing...")
            
            user_message = types.Content(role="user", parts=[types.Part(text=user_input)])
            
            final_response = ""
            
            # 5. Run the Agent
            # FIX: Removed 'app_name' here. ADK uses the one from Runner() init.
            async for event in runner.run_async(
                user_id="user_1",
                session_id="session_1",
                new_message=user_message
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    final_response = event.content.parts[0].text
            
            print(f"\nInvestor Copilot:\n{final_response}\n")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            # import traceback; traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
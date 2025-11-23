import os
import asyncio
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from test_search_query import semantic_search, load_persisted_collection

# Set API key
os.environ["GOOGLE_API_KEY"] = "AIzaSyBSLcUsK6WJWxNmkx-fprOGkNVt5mS_0XY"

# Configuration
retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

# Constants
USER_ID = "default_user"
SESSION_NAME = "main_conversation"

# Load ChromaDB collection into memory
print("Loading ChromaDB PDF document collection...")
load_persisted_collection()
print("✅ PDF document collection loaded.\n")

# Initialize agent
root_agent = Agent(
    name="helpful_assistant",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    description="A helpful assistant that can answer questions by searching through ingested PDF documents.",
    instruction=(
        "You are a helpful assistant with access to a semantic_search tool:\n"
        "1. **semantic_search**: Use this to search through ingested PDF documents. "
        "This tool searches through documents that have been processed and stored in a vector database. "
        "Use this when the user asks about information that might be in the PDF documents.\n\n"
        "When answering questions:\n"
        "- Use semantic_search for information related to the ingested PDF documents\n"
        "- If you cannot find relevant information, politely explain that your knowledge is limited to the ingested documents"
        "- Provide in response the citation of the document name used "
    ),
    tools=[semantic_search],
)

# Initialize runner and session service
runner = InMemoryRunner(agent=root_agent)
# Initialize session service - it should be connected to the runner
session_service = InMemorySessionService()
# Set the session service on the runner if it has that capability
if hasattr(runner, 'session_service'):
    runner.session_service = session_service
MODEL_NAME = root_agent.name

print("✅ Agent initialized and ready.\n")


async def create_or_get_session(session_name: str = SESSION_NAME):
    """
    Create or retrieve a session for maintaining conversation context.
    
    Args:
        session_name: Name identifier for the session
        
    Returns:
        Session object
        
    Raises:
        RuntimeError: If session creation/retrieval fails
    """
    # Get app name from the Runner (fallback to agent name if not available)
    try:
        app_name = runner.app_name
    except AttributeError:
        app_name = root_agent.name

    # Always try to create a new session first (it will handle if it already exists)
    # If creation fails because it exists, then get it
    session = None
    try:
        # Try to create a new session
        session = await session_service.create_session(
            app_name=app_name, user_id=USER_ID, session_id=session_name
        )
        if session is None:
            raise ValueError("Session creation returned None")
        print(f"✅ Created new session: {session_name}")
    except Exception as create_error:
        # If creation fails (e.g., session already exists), try to get it
        try:
            session = await session_service.get_session(
                app_name=app_name, user_id=USER_ID, session_id=session_name
            )
            if session is None:
                raise ValueError("Session retrieval returned None")
            print(f"✅ Retrieved existing session: {session_name}")
        except Exception as get_error:
            # If both fail, raise an error
            raise RuntimeError(
                f"Failed to create or retrieve session '{session_name}': "
                f"Create error: {create_error}, Get error: {get_error}"
            ) from get_error
    
    # Validate session has required attributes
    if session is None:
        raise RuntimeError("Session is None after creation/retrieval")
    
    # Check for 'id' attribute (could be 'id' or 'session_id' depending on implementation)
    session_id = None
    if hasattr(session, 'id'):
        session_id = session.id
    elif hasattr(session, 'session_id'):
        session_id = session.session_id
    elif hasattr(session, 'sessionId'):
        session_id = session.sessionId
    
    if session_id is None:
        # If no ID found, try to use the session_name as the ID
        print(f"⚠️  Warning: Session object has no 'id' attribute, using session_name as ID")
        session_id = session_name
        # Try to set it if possible
        if hasattr(session, 'id'):
            session.id = session_id
    
    return session


async def run_query(runner_instance: InMemoryRunner, query: str, session_name: str):
    """
    Run a single query in the given session.
    
    Args:
        runner_instance: The InMemoryRunner instance
        query: Query string
        session_name: Session name/ID for maintaining context
    """
    print(f"\nUser > {query}")

    # Convert the query string to the ADK Content format
    query_content = types.Content(role="user", parts=[types.Part(text=query)])

    # Stream the agent's response asynchronously
    # Use session_name directly as the session_id
    async for event in runner_instance.run_async(
        user_id=USER_ID, session_id=session_name, new_message=query_content
    ):
        # Only print text parts; do not emit warnings for non-text parts.
        if event.content and event.content.parts:
            # Extract all text parts, ignore other kinds
            texts = [
                part.text for part in event.content.parts
                if hasattr(part, "text") and part.text
            ]
            for text in texts:
                if text != "None":
                    print(f"{MODEL_NAME} > {text}")


async def main():
    """Main function to run the interactive agent."""
    print("Ask questions about the PDF documents. Type 'exit' or 'quit' to quit.\n")
    
    # Create or get session once at the start to ensure it exists
    try:
        session = await create_or_get_session(SESSION_NAME)
        if session is None:
            raise RuntimeError("Failed to create or retrieve session")
        print(f"✅ Session '{SESSION_NAME}' initialized.\n")
    except Exception as e:
        print(f"⚠️  Warning: Session initialization issue: {e}")
        print("Continuing anyway - session will be created on first use.\n")

    while True:
        query = input("Your question: ").strip()
        
        if query.lower() in ("exit", "quit"):
            print("Goodbye!")
            break
        
        if not query:
            continue
        
        try:
            # Pass session_name directly instead of session object
            await run_query(runner, query, SESSION_NAME)
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

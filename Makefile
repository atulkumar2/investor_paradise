
install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/0.8.13/install.sh | sh; source $HOME/.local/bin/env; }
	uv sync

playground:
	@echo "==============================================================================="
	@echo "| 🚀 Starting your agent playground...                                        |"
	@echo "|                                                                             |"
	@echo "| 💡 Try asking: What's the weather in San Francisco?                         |"
	@echo "|                                                                             |"
	@echo "| 🔍 IMPORTANT: Select the 'investor_agent' folder to interact with your agent.          |"
	@echo "==============================================================================="
	uv run adk web . --port 8501 --reload_agents

deploy:
	(uv export --no-hashes --no-header --no-dev --no-emit-project --no-annotate > investor_agent/app_utils/.requirements.txt 2>/dev/null || \
	uv export --no-hashes --no-header --no-dev --no-emit-project > investor_agent/app_utils/.requirements.txt) && \
	uv run -m investor_agent.app_utils.deploy \
		--source-packages=./investor_agent \
		--entrypoint-module=investor_agent.agent_engine_app \
		--entrypoint-object=agent_engine \
		--requirements-file=investor_agent/app_utils/.requirements.txt

backend: deploy


setup-dev-env:
	PROJECT_ID=$$(gcloud config get-value project) && \
	(cd deployment/terraform/dev && terraform init && terraform apply --var-file vars/env.tfvars --var dev_project_id=$$PROJECT_ID --auto-approve)



test:
	uv sync --dev
	uv run pytest tests/unit && uv run pytest tests/integration


lint:
	uv sync --dev --extra lint
	uv run codespell
	uv run ruff check . --diff
	uv run ruff format . --check --diff
	uv run mypy .

register-gemini-enterprise:
	@uvx agent-starter-pack@0.23.0 register-gemini-enterprise
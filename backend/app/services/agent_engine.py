import io
import os
import sys
import logging
from typing import Dict, Any, List, Optional
from smolagents import CodeAgent, Tool, HfApiModel, OpenAIServerModel
from backend.app.config import settings
from backend.app.services.sandbox import execute_restricted

logger = logging.getLogger(__name__)

# --- Definition of Custom Agent Tools ---

class WebSearchTool(Tool):
    name = "web_search"
    description = "Searches the web using DuckDuckGo and returns snippets of top results."
    inputs = {
        "query": {
            "type": "string",
            "description": "The search query to look up on the web."
        }
    }
    output_type = "string"

    def forward(self, query: str) -> str:
        from duckduckgo_search import DDGS
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                if not results:
                    return "No search results found."
                
                formatted = []
                for i, r in enumerate(results, 1):
                    formatted.append(f"[{i}] Title: {r.get('title', 'N/A')}\nSnippet: {r.get('body', 'N/A')}")
                return "\n\n".join(formatted)
        except Exception as e:
            logger.error(f"Search tool error: {str(e)}")
            return f"Failed to perform search. Error: {str(e)}"


class FileReaderTool(Tool):
    name = "file_reader"
    description = "Reads the text contents of a file securely from the local filesystem."
    inputs = {
        "filepath": {
            "type": "string",
            "description": "The path to the text file to read."
        }
    }
    output_type = "string"

    def forward(self, filepath: str) -> str:
        # Secure the path: only allow reading inside user workspace or app dir
        try:
            resolved_path = os.path.abspath(filepath)
            # Basic sanity check to avoid reading critical system files
            if any(p in resolved_path for p in ["/etc/", "/var/", "/System/", ".ssh"]):
                return "Error: Security violation. Access to this directory is forbidden."
            
            if not os.path.exists(resolved_path):
                return f"Error: File not found at '{filepath}'."
                
            with open(resolved_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(20000) # Cap reading at 20k characters
                if len(content) >= 20000:
                    content += "\n...[truncated due to length]..."
                return content
        except Exception as e:
            return f"Failed to read file: {str(e)}"


class FileWriterTool(Tool):
    name = "file_writer"
    description = "Writes text data into a file on the local workspace."
    inputs = {
        "filepath": {
            "type": "string",
            "description": "The destination path where the file should be saved."
        },
        "content": {
            "type": "string",
            "description": "The text content to write into the file."
        }
    }
    output_type = "string"

    def forward(self, filepath: str, content: str) -> str:
        try:
            resolved_path = os.path.abspath(filepath)
            if any(p in resolved_path for p in ["/etc/", "/var/", "/System/", ".ssh"]):
                return "Error: Security violation. Writing to this directory is forbidden."
            
            os.makedirs(os.path.dirname(resolved_path), exist_ok=True)
            with open(resolved_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote {len(content)} characters to '{filepath}'."
        except Exception as e:
            return f"Failed to write file: {str(e)}"


class PythonSandboxTool(Tool):
    name = "python_sandbox"
    description = "Executes custom Python code inside a restricted AST sandbox and returns the stdout and outputs."
    inputs = {
        "code": {
            "type": "string",
            "description": "The raw Python code to execute."
        }
    }
    output_type = "string"

    def forward(self, code: str) -> str:
        res = execute_restricted(code)
        if not res["success"]:
            return f"Sandbox execution failed.\nError: {res['error']}\nStdout: {res['stdout']}"
        return f"Execution succeeded!\nStdout: {res['stdout']}\nOutputs: {res['outputs']}"


# --- Agent Provisioning Engine ---

class AgentOrchestrator:
    """
    Orchestrates models and constructs agent instances with specific execution environments.
    """
    def __init__(self, execution_mode: str = "SERVERLESS"):
        self.execution_mode = execution_mode.upper()
        self.tools = [WebSearchTool(), FileReaderTool(), FileWriterTool(), PythonSandboxTool()]

    def _get_model(self, model_id: str):
        """Initializes the smolagents model driver based on configuration and mode."""
        
        # 1. Local Mode Execution (using llama-cpp-python local model endpoint)
        if self.execution_mode == "LOCAL":
            try:
                # We attempt to connect to a local llama.cpp server
                # Standard local server port is 8000 or similar
                logger.info("Initializing Local open-source model using local OpenAIServerModel.")
                return OpenAIServerModel(
                    api_key="local-token",
                    api_base="http://localhost:8001/v1",  # Local runner binds on port 8001 to avoid FastAPI clash
                    model_id=model_id
                )
            except Exception as e:
                logger.warning(f"Failed to load local model driver: {str(e)}. Falling back to HF Serverless Inference.")

        # 2. Serverless / API Mode Execution
        # If OpenAI keys are configured, use OpenAIServerModel
        if settings.OPENAI_API_KEY:
            logger.info(f"Initializing OpenAIServerModel for {model_id} via {settings.OPENAI_API_BASE}")
            return OpenAIServerModel(
                api_key=settings.OPENAI_API_KEY,
                api_base=settings.OPENAI_API_BASE,
                model_id=settings.LLM_MODEL  # Fallback to general LLM model if requested is unavailable
            )
        
        # Free-tier serverless HF inference endpoint
        logger.info(f"Initializing HfApiModel serverless endpoint for model '{model_id}'")
        return HfApiModel(
            model_id=model_id,
            token=settings.HF_TOKEN
        )

    def run_agent_task(self, model_id: str, prompt: str, context_vars: Dict[str, Any]) -> Dict[str, Any]:
        """
        Instantiates an agent, feeds in variables, intercepts stdout to capture logs, 
        and executes the prompt.
        """
        model = self._get_model(model_id)

        # Build code execution sandbox mapping for smolagents CodeAgent
        # We redirect stdout/stderr to capture execution traces live!
        log_stream = io.StringIO()
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        agent = CodeAgent(
            model=model,
            tools=self.tools,
            additional_authorized_imports=list(SAFE_MODULES)
        )

        # Intercept output
        sys.stdout = log_stream
        sys.stderr = log_stream

        success = False
        error_msg = None
        output_result = None

        try:
            # Build full system environment query
            formatted_prompt = f"Global context/inputs:\n{context_vars}\n\nTask details:\n{prompt}"
            logger.info(f"Executing agent task: {prompt[:100]}...")
            
            output_result = agent.run(formatted_prompt)
            success = True
        except Exception as e:
            error_msg = f"Agent failed execution: {str(e)}"
            logger.error(error_msg)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        captured_logs = log_stream.getvalue()

        # Clean logs by stripping any excessively repetitive color codes if present
        clean_logs = captured_logs.replace("\x1b[", "").replace("[0m", "")

        return {
            "success": success,
            "logs": clean_logs,
            "output": str(output_result) if output_result is not None else None,
            "error": error_msg
        }

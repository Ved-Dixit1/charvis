from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import datetime

# --- DAG Definition Schemas ---

class DAGNode(BaseModel):
    id: str = Field(..., description="Unique identifier for the node (e.g., 'extract_data', 'translate_text')")
    task_type: str = Field(..., description="The type of agent task (e.g., 'text_generation', 'summarization', 'translation', 'web_search', 'python_execution')")
    prompt: str = Field(..., description="Detailed instructions, system prompts, or parameters for the agent to execute this specific node.")
    model_id: str = Field(..., description="Suggested Hugging Face model stub (e.g., 'meta-llama/Meta-Llama-3-8B-Instruct', 'google/gemma-2-2b-it')")
    input_variables: List[str] = Field(default=[], description="List of variable keys this node reads from the global execution context.")
    output_variable: str = Field(..., description="Single unique variable key under which this node writes its final string or object output.")
    dependencies: List[str] = Field(default=[], description="List of parent node IDs that must finish execution before this node can run.")

class DAGEdge(BaseModel):
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")

class DAGPipeline(BaseModel):
    title: str = Field(..., description="A short, catchy name for the execution pipeline.")
    description: str = Field(..., description="A concise explanation of what this workflow accomplishes and the steps it takes.")
    nodes: List[DAGNode] = Field(..., description="The collection of executable nodes making up the pipeline.")
    edges: List[DAGEdge] = Field(default=[], description="Connections showing data flow between nodes, derived from node dependencies.")


# --- API Request & Response Schemas ---

class PipelineCreateRequest(BaseModel):
    prompt: str = Field(..., description="Natural language description of the pipeline you want to build.")

class PipelineExecutionRequest(BaseModel):
    inputs: Dict[str, Any] = Field(default={}, description="Key-value pair variables to seed the execution context (e.g., file paths, URLs, initial text).")
    execution_mode: str = Field("SERVERLESS", description="Compute runtime selection: 'LOCAL' (using GGUF) or 'SERVERLESS' (using HF APIs)")

class NodeExecutionResponse(BaseModel):
    id: int
    node_id: str
    status: str
    inputs: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None
    logs: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

class PipelineExecutionResponse(BaseModel):
    id: str
    pipeline_id: str
    status: str
    inputs: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None
    execution_mode: str
    error_message: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    node_executions: List[NodeExecutionResponse] = []

    class Config:
        from_attributes = True

class PipelineResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    user_prompt: str
    dag_json: Dict[str, Any]
    created_at: datetime.datetime
    executions: List[PipelineExecutionResponse] = []

    class Config:
        from_attributes = True

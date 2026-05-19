import logging
import traceback
from typing import Dict, Any, List, Set
from sqlalchemy.orm import Session
from backend.app.models import Pipeline, PipelineExecution, NodeExecution
from backend.app.schemas import DAGPipeline, DAGNode
from backend.app.services.agent_engine import AgentOrchestrator

logger = logging.getLogger(__name__)

def topological_sort(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Performs Kahn's algorithm for topological sorting on DAG nodes.
    Raises ValueError if a cycle is detected.
    """
    # Build maps of adjacency and in-degree counts
    adj_list: Dict[str, Set[str]] = {n["id"]: set() for n in nodes}
    in_degree: Dict[str, int] = {n["id"]: 0 for n in nodes}
    node_map: Dict[str, Dict[str, Any]] = {n["id"]: n for n in nodes}

    for n in nodes:
        deps = n.get("dependencies", [])
        for dep in deps:
            # dep -> n["id"]
            if dep in adj_list:
                adj_list[dep].add(n["id"])
                in_degree[n["id"]] += 1
            else:
                # Dependency refers to a node not in list
                logger.warning(f"Node '{n['id']}' references missing dependency '{dep}'")

    # Queue of nodes with 0 in-degree (no unresolved parent steps)
    queue = [nid for nid, count in in_degree.items() if count == 0]
    sorted_order = []

    while queue:
        # Sort queue to ensure deterministic execution order
        queue.sort()
        curr = queue.pop(0)
        sorted_order.append(node_map[curr])

        for neighbor in adj_list[curr]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(sorted_order) != len(nodes):
        cycle_nodes = [nid for nid, count in in_degree.items() if count > 0]
        raise ValueError(f"Cyclic dependency detected in pipeline! Loops found at nodes: {cycle_nodes}")

    return sorted_order


class PipelineExecutor:
    """
    Manages end-to-end topological execution of an agent pipeline.
    Ensures safe state passing and logs intermediate agent traces to the database.
    """
    def __init__(self, db: Session, execution_id: str):
        self.db = db
        self.execution_id = execution_id
        
        # Load execution and pipeline config
        self.execution = db.query(PipelineExecution).filter(PipelineExecution.id == execution_id).first()
        if not self.execution:
            raise ValueError(f"Execution record with ID '{execution_id}' does not exist.")
            
        self.pipeline = db.query(Pipeline).filter(Pipeline.id == self.execution.pipeline_id).first()
        if not self.pipeline:
            raise ValueError(f"Pipeline record with ID '{self.execution.pipeline_id}' does not exist.")

        self.dag = self.pipeline.dag_json
        self.orchestrator = AgentOrchestrator(execution_mode=self.execution.execution_mode)

    def execute(self) -> Dict[str, Any]:
        """Runs the topological pipeline. Returns the final context dictionary."""
        logger.info(f"Starting execution '{self.execution_id}' of pipeline '{self.pipeline.title}'...")
        
        # Update pipeline execution state to RUNNING
        self.execution.status = "RUNNING"
        self.db.commit()

        # Seed global context dictionary from user inputs
        context: Dict[str, Any] = {k: v for k, v in (self.execution.inputs or {}).items()}
        
        nodes_list = self.dag.get("nodes", [])
        
        try:
            # 1. Sort nodes topologically
            sorted_nodes = topological_sort(nodes_list)
        except ValueError as sort_err:
            self.execution.status = "FAILED"
            self.execution.error_message = str(sort_err)
            self.db.commit()
            raise sort_err

        # Initialize NodeExecution DB logs as PENDING
        node_db_records: Dict[str, NodeExecution] = {}
        for n in sorted_nodes:
            node_id = n["id"]
            node_exec = NodeExecution(
                execution_id=self.execution_id,
                node_id=node_id,
                status="PENDING",
                inputs={},
                outputs={},
                logs=""
            )
            self.db.add(node_exec)
            self.db.commit()
            node_db_records[node_id] = node_exec

        # 2. Iterate through sorted nodes
        failed_node_id = None
        for node_data in sorted_nodes:
            node_id = node_data["id"]
            node_exec = node_db_records[node_id]

            # If a prior node failed, downstream nodes are marked as FAILED directly
            if failed_node_id:
                node_exec.status = "FAILED"
                node_exec.error_message = f"Skipped due to upstream failure at node '{failed_node_id}'."
                self.db.commit()
                continue

            node_exec.status = "RUNNING"
            self.db.commit()

            # Gather input variables for this node from context
            node_inputs = {}
            for var in node_data.get("input_variables", []):
                # If variable exists in context, pull it. If not, inject empty string or check
                node_inputs[var] = context.get(var, "")

            # If input_variables is empty and this is a starting node, pass general user inputs
            if not node_inputs and not node_data.get("dependencies", []):
                node_inputs = context.copy()

            node_exec.inputs = node_inputs
            self.db.commit()

            # Execute Agent
            try:
                res = self.orchestrator.run_agent_task(
                    model_id=node_data["model_id"],
                    prompt=node_data["prompt"],
                    context_vars=node_inputs
                )

                # Log thoughts and traces to DB
                node_exec.logs = res.get("logs", "")
                
                if res["success"]:
                    # Save results
                    output_val = res.get("output", "")
                    output_key = node_data["output_variable"]
                    
                    # Store output in global execution context
                    context[output_key] = output_val

                    node_exec.status = "SUCCESS"
                    node_exec.outputs = {output_key: output_val}
                    self.db.commit()
                else:
                    # Mark node failed
                    node_exec.status = "FAILED"
                    node_exec.error_message = res.get("error", "Unknown agent execution error.")
                    self.db.commit()
                    failed_node_id = node_id

            except Exception as task_err:
                logger.error(f"Execution error on node '{node_id}': {str(task_err)}")
                node_exec.status = "FAILED"
                node_exec.error_message = f"{type(task_err).__name__}: {str(task_err)}\n{traceback.format_exc()}"
                node_exec.logs = (node_exec.logs or "") + f"\n[CRITICAL ERROR]: {str(task_err)}"
                self.db.commit()
                failed_node_id = node_id

        # 3. Finalize execution status
        if failed_node_id:
            self.execution.status = "FAILED"
            self.execution.error_message = f"Pipeline execution interrupted due to failure at node '{failed_node_id}'."
            self.db.commit()
            logger.error(f"Pipeline execution '{self.execution_id}' completed with failures.")
        else:
            self.execution.status = "SUCCESS"
            # Filter output variables corresponding to terminal nodes (nodes with no outbound edges)
            final_outputs = {}
            # Outbound count checks
            outbound_count = {n["id"]: 0 for n in sorted_nodes}
            for n in sorted_nodes:
                for dep in n.get("dependencies", []):
                    if dep in outbound_count:
                        outbound_count[dep] += 1
            
            for n in sorted_nodes:
                if outbound_count[n["id"]] == 0:
                    out_var = n["output_variable"]
                    final_outputs[out_var] = context.get(out_var, "")

            self.execution.outputs = final_outputs
            self.db.commit()
            logger.info(f"Pipeline execution '{self.execution_id}' completed successfully!")

        return context

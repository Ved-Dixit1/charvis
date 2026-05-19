#!/usr/bin/env python3
"""
Charvis Local Runner CLI
Allows offline execution of generated agent DAG pipelines directly from your terminal.

Usage:
  python runner.py --pipeline path/to/pipeline.json --input raw_data="hello" --mode LOCAL
"""

import os
import sys
import json
import argparse
from typing import Dict, Any

# Ensure backend package can be imported from parent directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.app.services.executor import topological_sort
from backend.app.services.agent_engine import AgentOrchestrator

def parse_input_pairs(input_list: list) -> Dict[str, Any]:
    """Parses list of 'key=value' strings into a dictionary."""
    inputs = {}
    if not input_list:
        return inputs
    for item in input_list:
        if "=" not in item:
            print(f"Warning: Skipping invalid input argument format '{item}'. Expected 'key=value'.")
            continue
        k, v = item.split("=", 1)
        # Attempt to parse json structure (like list or dict), fallback to string
        try:
            inputs[k.strip()] = json.loads(v.strip())
        except Exception:
            inputs[k.strip()] = v.strip()
    return inputs

def execute_offline_pipeline(pipeline_path: str, inputs: Dict[str, Any], mode: str):
    """Executes a pipeline DAG JSON file node-by-node offline."""
    print("=" * 60)
    print("      CHARVIS OFFLINE PIPELINE EXECUTION ENGINE      ")
    print("=" * 60)
    
    if not os.path.exists(pipeline_path):
        print(f"Error: Pipeline file not found at '{pipeline_path}'")
        sys.exit(1)

    try:
        with open(pipeline_path, "r", encoding="utf-8") as f:
            pipeline_data = json.load(f)
    except Exception as e:
        print(f"Error: Failed to read pipeline JSON: {str(e)}")
        sys.exit(1)

    # Resolve if the file is a database dump or raw DAG
    dag = pipeline_data.get("dag_json", pipeline_data)
    title = pipeline_data.get("title", dag.get("title", "Untitled Pipeline"))
    nodes = dag.get("nodes", [])

    print(f"Pipeline: {title}")
    print(f"Execution Mode: {mode}")
    print(f"Initial Inputs: {inputs}")
    print(f"Resolving DAG structure ({len(nodes)} nodes)...")

    try:
        sorted_nodes = topological_sort(nodes)
    except ValueError as err:
        print(f"\n[CRITICAL ERROR]: {str(err)}")
        sys.exit(1)

    print("Topological Order:", " -> ".join([n["id"] for n in sorted_nodes]))
    print("-" * 60)

    # Initialize execution context with inputs
    context = inputs.copy()
    orchestrator = AgentOrchestrator(execution_mode=mode)
    
    failed_node = None
    for idx, node in enumerate(sorted_nodes, 1):
        node_id = node["id"]
        model_id = node["model_id"]
        output_var = node["output_variable"]
        
        print(f"\n[{idx}/{len(sorted_nodes)}] Running Node: '{node_id}'")
        print(f"  └─ Task Type: {node['task_type']}")
        print(f"  └─ Model ID:  {model_id}")
        
        if failed_node:
            print(f"  └─ [SKIPPED] due to parent failure at node '{failed_node}'")
            continue

        # Extract input context variables
        node_inputs = {}
        for var in node.get("input_variables", []):
            node_inputs[var] = context.get(var, "")

        if not node_inputs and not node.get("dependencies", []):
            node_inputs = context.copy()

        print(f"  └─ Node Inputs: {node_inputs}")
        print("  └─ Executing Agent...")
        print("~" * 60)
        
        try:
            res = orchestrator.run_agent_task(
                model_id=model_id,
                prompt=node["prompt"],
                context_vars=node_inputs
            )
            
            # Print thoughts/logs in real-time
            if res.get("logs"):
                print(res["logs"])
                
            print("~" * 60)
            
            if res["success"]:
                output_val = res.get("output", "")
                context[output_var] = output_val
                print(f"  └─ [SUCCESS] Node '{node_id}' output saved to variable '{output_var}'")
                print(f"  └─ Result: {output_val[:300]}")
                if len(output_val) > 300:
                    print("     ...[truncated]...")
            else:
                print(f"  └─ [FAILED] Agent execution error: {res.get('error')}")
                failed_node = node_id
        except Exception as e:
            print(f"  └─ [CRITICAL ERROR] Running task: {str(e)}")
            failed_node = node_id

    print("\n" + "=" * 60)
    if failed_node:
        print(f"  EXECUTION STATUS: FAILED (Interrupted at node '{failed_node}')")
        print("=" * 60)
        sys.exit(1)
    else:
        print("  EXECUTION STATUS: SUCCESS")
        print("=" * 60)
        print("\nFinal Pipeline Outputs:")
        
        # Output terminal values
        outbound_count = {n["id"]: 0 for n in sorted_nodes}
        for n in sorted_nodes:
            for dep in n.get("dependencies", []):
                if dep in outbound_count:
                    outbound_count[dep] += 1
                    
        for n in sorted_nodes:
            if outbound_count[n["id"]] == 0:
                out_var = n["output_variable"]
                print(f" - {out_var}: {context.get(out_var, '')}")
                
        # Write output to local results.json
        output_file = "pipeline_results.json"
        with open(output_file, "w", encoding="utf-8") as out_f:
            json.dump(context, out_f, indent=2)
        print(f"\nFull execution context written to '{output_file}'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Charvis Offline Pipeline Executor CLI")
    parser.add_argument("--pipeline", required=True, help="Path to the generated pipeline JSON file")
    parser.add_argument("--mode", default="SERVERLESS", choices=["LOCAL", "SERVERLESS"], help="Execution compute layer")
    parser.add_argument("--input", action="append", help="Key-value inputs in 'key=value' format. Can be specified multiple times.")
    
    args = parser.parse_args()
    inputs = parse_input_pairs(args.input)
    execute_offline_pipeline(args.pipeline, inputs, args.mode)

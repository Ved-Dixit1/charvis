import json
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
import instructor
from backend.app.config import settings
from backend.app.schemas import DAGPipeline, DAGNode, DAGEdge

logger = logging.getLogger(__name__)

def generate_mock_dag(prompt: str) -> DAGPipeline:
    """
    Generates an intelligent mock DAG based on prompt keywords.
    Ensures zero-config local running is incredibly rich and functional.
    """
    prompt_lower = prompt.lower()
    
    # 1. CSV / Data Analysis Flow
    if any(k in prompt_lower for k in ["csv", "excel", "data", "analyze", "analytics"]):
        nodes = [
            DAGNode(
                id="extract_trends",
                task_type="python_execution",
                prompt="Write a Python script to compute average sales, group-by monthly stats, and output a clean table of trends from the raw_data.",
                model_id="Qwen/Qwen2.5-Coder-7B-Instruct",
                input_variables=["raw_data"],
                output_variable="data_summary",
                dependencies=[]
            ),
            DAGNode(
                id="generate_text_summary",
                task_type="summarization",
                prompt="Take the statistical summaries and generate a high-level executive report highlighting top performers and anomalies.",
                model_id="meta-llama/Meta-Llama-3-8B-Instruct",
                input_variables=["data_summary"],
                output_variable="executive_report",
                dependencies=["extract_trends"]
            ),
            DAGNode(
                id="translate_report",
                task_type="translation",
                prompt="Translate the executive report into Spanish, maintaining its professional, executive tone and tabular layout.",
                model_id="google/gemma-2-2b-it",
                input_variables=["executive_report"],
                output_variable="final_report_es",
                dependencies=["generate_text_summary"]
            )
        ]
        title = "Data Analysis & Translation Pipeline"
        description = "Ingests raw text/CSV data, extracts statistical trends via local Python sandboxing, generates a natural language summary, and translates it into Spanish."
        
    # 2. Web Search & Research Flow
    elif any(k in prompt_lower for k in ["search", "web", "research", "find", "google", "duckduckgo"]):
        nodes = [
            DAGNode(
                id="web_research",
                task_type="web_search",
                prompt=f"Perform web searches on DuckDuckGo to extract the latest news and consensus on the topic: '{prompt}'. Keep only highly relevant facts.",
                model_id="meta-llama/Meta-Llama-3-8B-Instruct",
                input_variables=["user_query"],
                output_variable="research_findings",
                dependencies=[]
            ),
            DAGNode(
                id="write_article",
                task_type="text_generation",
                prompt="Synthesize the research findings into an engaging, structured blog post with an intro, key takeaways, and a conclusion.",
                model_id="meta-llama/Meta-Llama-3-8B-Instruct",
                input_variables=["research_findings"],
                output_variable="blog_post",
                dependencies=["web_research"]
            ),
            DAGNode(
                id="sentiment_analysis",
                task_type="text_generation",
                prompt="Perform a sentiment analysis on the findings. Output a classification (Positive, Neutral, Negative) and 2-sentence rationale.",
                model_id="google/gemma-2-2b-it",
                input_variables=["research_findings"],
                output_variable="sentiment_report",
                dependencies=["web_research"]
            )
        ]
        title = "Autonomous Research & Content Synthesis Pipeline"
        description = "Executes real-time DuckDuckGo searches, parses web findings, writes a synthetic article, and parallelly outputs a sentiment analysis report."

    # 3. Default General Flow (Summarizer & Writer)
    else:
        nodes = [
            DAGNode(
                id="text_summarizer",
                task_type="summarization",
                prompt="Read the input_text. Create a structured summary containing key bullet points and action items.",
                model_id="meta-llama/Meta-Llama-3-8B-Instruct",
                input_variables=["input_text"],
                output_variable="text_summary",
                dependencies=[]
            ),
            DAGNode(
                id="blog_expansion",
                task_type="text_generation",
                prompt="Expand the summarized bullet points into a detailed, creative newsletter format targeted at tech innovators.",
                model_id="meta-llama/Meta-Llama-3-8B-Instruct",
                input_variables=["text_summary"],
                output_variable="newsletter_draft",
                dependencies=["text_summarizer"]
            )
        ]
        title = "Content Distillation & Expansion Pipeline"
        description = "Takes long-form input, reduces it to structural insights, and expands it into an elegant newsletter format."

    # Derive edges from dependencies
    edges = []
    for node in nodes:
        for dep in node.dependencies:
            edges.append(DAGEdge(source=dep, target=node.id))

    return DAGPipeline(title=title, description=description, nodes=nodes, edges=edges)


def generate_pipeline_dag(prompt: str) -> DAGPipeline:
    """
    Accepts natural language prompt. Uses structured LLM calling (via Instructor)
    to output a validated DAGPipeline object. Falls back to mock generation if keys are missing.
    """
    if not settings.OPENAI_API_KEY:
        logger.info("OPENAI_API_KEY is not configured. Falling back to semantic mock DAG generation.")
        return generate_mock_dag(prompt)

    try:
        # Patch client for structured output mapping
        client = instructor.from_openai(
            OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_API_BASE
            )
        )

        system_instruction = (
            "You are a Senior AI Pipeline Architect. Your job is to translate user's natural language requirements "
            "into a Structured AI Agent execution pipeline represented as a Directed Acyclic Graph (DAG).\n\n"
            "Rules:\n"
            "1. Identify distinct execution nodes. Each node represents a single specialized agent step.\n"
            "2. Establish dependencies between nodes. A node can ONLY depend on another node if it reads its output.\n"
            "3. Input variables must correspond to: initial input variables or output_variable names of dependent parent nodes.\n"
            "4. Task types must be selected from: ['text_generation', 'summarization', 'translation', 'web_search', 'python_execution'].\n"
            "5. Assign a suitable open-source model ID from the Hugging Face hub (e.g. 'meta-llama/Meta-Llama-3-8B-Instruct', "
            "'Qwen/Qwen2.5-Coder-7B-Instruct', 'google/gemma-2-2b-it').\n"
            "6. Make sure there are no cycles in the DAG."
        )

        pipeline: DAGPipeline = client.chat.completions.create(
            model=settings.LLM_MODEL,
            response_model=DAGPipeline,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Create a pipeline to: {prompt}"}
            ],
            temperature=0.1
        )

        # Double check and ensure edges are properly populated if the LLM left it sparse
        if not pipeline.edges:
            edges = []
            for node in pipeline.nodes:
                for dep in node.dependencies:
                    edges.append(DAGEdge(source=dep, target=node.id))
            pipeline.edges = edges

        return pipeline

    except Exception as e:
        logger.error(f"Error during structured LLM generation: {str(e)}. Falling back to mock DAG.")
        return generate_mock_dag(prompt)

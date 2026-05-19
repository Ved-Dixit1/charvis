#!/usr/bin/env python3
"""
Charvis Technical PDF Documentation Compiler
Uses fpdf2 to build a publication-grade PDF handbook for the Charvis platform.
"""

import os
import sys
from fpdf import FPDF

class CharvisTechnicalManual(FPDF):
    def header(self):
        if self.page_no() == 1:
            return  # Skip header on the cover page
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(100, 110, 130)
        self.cell(0, 10, 'CHARVIS - AI Agent DAG Pipeline Orchestrator | Technical Specifications', border=0, ln=0, align='L')
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, 'PROJECT DIRECTORY', border=0, ln=1, align='R')
        self.set_draw_color(226, 232, 240)
        self.line(10, 18, 200, 18)
        self.ln(5)

    def footer(self):
        if self.page_no() == 1:
            return  # Skip footer on the cover page
        self.set_y(-15)
        self.set_draw_color(226, 232, 240)
        self.line(10, 282, 200, 282)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, 'Confidential - Open Source MIT License', border=0, ln=0, align='L')
        self.cell(0, 10, f'Page {self.page_no()} of {{nb}}', border=0, ln=1, align='R')

    def chapter_title(self, num, title):
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(79, 70, 229)  # Premium Indigo
        self.cell(0, 10, f'{num}. {title}', border=0, ln=1, align='L')
        self.ln(4)

    def heading_2(self, text):
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(30, 41, 59)
        self.cell(0, 8, text, border=0, ln=1, align='L')
        self.ln(2)

    def paragraph(self, text):
        self.set_font('Helvetica', '', 9.5)
        self.set_text_color(71, 85, 105)
        self.multi_cell(0, 5.5, text)
        self.ln(3)

    def code_block(self, code_lines):
        self.set_font('Courier', '', 8)
        self.set_text_color(16, 185, 129)  # Glowing emerald text
        self.set_fill_color(9, 9, 11)      # Dark charcoal background
        self.set_draw_color(39, 39, 42)
        
        # Calculate height needed
        height = len(code_lines) * 4.5 + 4
        x = self.get_x()
        y = self.get_y()
        
        self.rect(x, y, 190, height, 'DF')
        self.set_xy(x + 3, y + 2)
        
        for line in code_lines:
            self.cell(0, 4.5, line, border=0, ln=1)
        self.set_y(y + height + 3)

def generate_pdf():
    pdf = CharvisTechnicalManual(orientation='P', unit='mm', format='A4')
    pdf.alias_nb_pages()
    
    # ----------------------------------------------------
    # PAGE 1: COVER PAGE
    # ----------------------------------------------------
    pdf.add_page()
    
    # Obsidian solid background
    pdf.set_fill_color(6, 7, 10)
    pdf.rect(0, 0, 210, 297, 'F')
    
    # Glowing neon lines
    pdf.set_draw_color(79, 70, 229) # Indigo
    pdf.line(15, 15, 195, 15)
    pdf.line(15, 282, 195, 282)
    pdf.line(15, 15, 15, 282)
    pdf.line(195, 15, 195, 282)
    
    pdf.ln(25)
    pdf.set_font('Helvetica', 'B', 32)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 15, 'C H A R V I S', border=0, ln=1, align='C')
    
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(129, 140, 248) # Indigo-light
    pdf.cell(0, 8, 'AI Agent DAG Pipeline Generator & Hybrid Compute Orchestrator', border=0, ln=1, align='C')
    
    pdf.ln(12)
    
    # Cover image (Visual Dashboard Mockup)
    img_path = 'assets/dashboard_mockup.png'
    if os.path.exists(img_path):
        # Center image horizontally
        pdf.image(img_path, x=22, y=72, w=166)
    
    pdf.set_y(238)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(241, 245, 249)
    pdf.cell(0, 6, 'TECHNICAL SPECIFICATIONS HANDBOOK', border=0, ln=1, align='C')
    
    pdf.set_font('Helvetica', '', 8.5)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 5, 'Release Version: V1.0.0 (Production Core)', border=0, ln=1, align='C')
    pdf.cell(0, 5, 'License: MIT Open Source Project', border=0, ln=1, align='C')
    pdf.cell(0, 5, f'Compiled Date: 2026-05-19', border=0, ln=1, align='C')
    
    # ----------------------------------------------------
    # PAGE 2: TOC & EXECUTIVE SUMMARY
    # ----------------------------------------------------
    pdf.add_page()
    pdf.ln(5)
    pdf.chapter_title('I', 'Executive Summary')
    pdf.paragraph(
        "Charvis is an advanced, production-ready monorepo framework designed to close the gap between abstract "
        "human pipeline requests and concrete, topologically correct code agent clusters. Rather than relying on rigid, "
        "hardcoded LLM templates, Charvis parses developer instructions into dynamic, cycle-free Directed Acyclic "
        "Graphs (DAG). Each node inside a generated DAG is provisioned as an independent, autonomous agent "
        "running specialized tools under extreme safety."
    )
    pdf.paragraph(
        "A cornerstone feature is the Dual-Compute Strategy. Charvis can run serverless agent instances calling "
        "highly performant remote APIs, or shift downstream tasks into absolute offline local compute modes by "
        "programmatically downloading quantized Hugging Face GGUF models and executing tool logic locally. Safety "
        "boundaries are strictly enforced through a custom, processes-isolated AST Python Sandbox which blocks dangerous "
        "built-in calls and schedules resource termination limits."
    )
    
    pdf.ln(5)
    pdf.chapter_title('II', 'Platform Anatomy & Modules')
    pdf.heading_2('1. High-Performance Backend Architecture')
    pdf.paragraph(
        "The backend is driven by FastAPI, integrated with SQLAlchemy core, Pydantic validations, and Kahn's topological "
        "resolutions. Background threads process long-running model downloads and network checks asynchronously, immediately "
        "transmitting transactional reference IDs to client drawers to prevent HTTP timeout blockages."
    )
    pdf.paragraph(
        "SQLite serves as the zero-config fallback storage layer (written to 'charvis.db'), automatically upgrading to "
        "enterprise-grade PostgreSQL connection instances when database variables are supplied in the '.env' file."
    )

    # ----------------------------------------------------
    # PAGE 3: ARCHITECTURE FLOW & TOPOLOGY
    # ----------------------------------------------------
    pdf.add_page()
    pdf.ln(5)
    pdf.chapter_title('III', 'Topological Execution & Variable Binding')
    pdf.paragraph(
        "Before any execution begins, Charvis evaluates DAG steps using Kahn's topological sorting algorithm. This "
        "guarantees that upstream prerequisite nodes complete successfully before downstream dependent nodes process. "
        "Upstream results are systematically injected into downstream variables via mapping context states."
    )
    
    img_flow = 'assets/architecture_flow.png'
    if os.path.exists(img_flow):
        pdf.image(img_flow, x=22, y=42, w=166)
    
    pdf.set_y(212)
    pdf.heading_2('Topological Error Cascading Rules')
    pdf.paragraph(
        "To ensure execution hygiene, when a parent node runs into critical errors (sandbox violations, model download "
        "disconnects, syntax faults), the execution engine immediately captures the exception, marks the node status as "
        "FAILED in the relational database, and cascades the failure. All children nodes that depend on that parent output "
        "are marked as SKIPPED, preventing deadlocks or corrupt analytical cascades."
    )

    # ----------------------------------------------------
    # PAGE 4: AST SECURITY SANDBOX
    # ----------------------------------------------------
    pdf.add_page()
    pdf.ln(5)
    pdf.chapter_title('IV', 'Restricted AST Security Sandbox')
    pdf.paragraph(
        "To prevent server breaches, data exfiltration, or resource hogging by generated python agent scripts, Charvis "
        "forces tool execution through a custom process boundary. This sandbox parses the generated Python script statically "
        "into an Abstract Syntax Tree (AST), inspecting all import calls, attributes, and variables before running it."
    )
    
    img_sandbox = 'assets/safety_sandbox.png'
    if os.path.exists(img_sandbox):
        pdf.image(img_sandbox, x=22, y=45, w=166)
        
    pdf.set_y(215)
    pdf.heading_2('Blocked Dangers vs. Safe Whitelist')
    pdf.paragraph(
        "Charvis overrides standard python built-ins to block dangerous commands. The whitelist restricts standard imports "
        "to helper libraries: 'math', 'json', 'datetime', 'random', 're', 'collections', and 'urllib.parse'. It strictly "
        "forbids system operations like 'os', 'sys', 'subprocess', or 'shutil', and blocks direct file open calls."
    )

    # ----------------------------------------------------
    # PAGE 5: DUAL COMPUTE & CONFIG MATRIX
    # ----------------------------------------------------
    pdf.add_page()
    pdf.ln(5)
    pdf.chapter_title('V', 'Dual-Compute Configurations')
    pdf.paragraph(
        "The hybrid compute layer allows developers to select their infrastructure of choice. Local Mode scans "
        "Hugging Face local cache folders, downloads GGUF models directly, and runs quantization models on-device. "
        "Serverless Mode integrates custom API targets (Together AI, DeepInfra, OpenAI) for serverless agent DAG synthesis."
    )
    
    img_compute = 'assets/hybrid_compute.png'
    if os.path.exists(img_compute):
        pdf.image(img_compute, x=25, y=45, w=160)
        
    pdf.set_y(210)
    pdf.heading_2('Platform Environmental Parameters')
    
    # Configure variables table
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(255, 255, 255)
    pdf.set_fill_color(79, 70, 229) # Indigo header
    
    pdf.cell(50, 6, 'Parameter Name', border=1, ln=0, align='C', fill=True)
    pdf.cell(55, 6, 'Default Fallback', border=1, ln=0, align='C', fill=True)
    pdf.cell(85, 6, 'Platform Purpose', border=1, ln=1, align='C', fill=True)
    
    pdf.set_font('Courier', 'B', 7.5)
    pdf.set_text_color(30, 41, 59)
    pdf.set_fill_color(248, 250, 252) # Light alternate row
    
    pdf.cell(50, 6, ' DATABASE_URL', border=1, ln=0, align='L', fill=True)
    pdf.set_font('Helvetica', '', 8)
    pdf.cell(55, 6, ' sqlite:///./charvis.db', border=1, ln=0, align='L', fill=True)
    pdf.cell(85, 6, ' Fallback SQLite or Postgres target database', border=1, ln=1, align='L', fill=True)
    
    pdf.set_font('Courier', 'B', 7.5)
    pdf.cell(50, 6, ' OPENAI_API_KEY', border=1, ln=0, align='L')
    pdf.set_font('Helvetica', '', 8)
    pdf.cell(55, 6, ' None (Optional)', border=1, ln=0, align='L')
    pdf.cell(85, 6, ' Key used to synthetically generate pipeline DAGs', border=1, ln=1, align='L')
    
    pdf.set_font('Courier', 'B', 7.5)
    pdf.cell(50, 6, ' LOCAL_CACHE_DIR', border=1, ln=0, align='L', fill=True)
    pdf.set_font('Helvetica', '', 8)
    pdf.cell(55, 6, ' ~/.cache/huggingface', border=1, ln=0, align='L', fill=True)
    pdf.cell(85, 6, ' Local storage folder for GGUF model files', border=1, ln=1, align='L', fill=True)

    # ----------------------------------------------------
    # PAGE 6: DEVELOPMENT QUICKSTART
    # ----------------------------------------------------
    pdf.add_page()
    pdf.ln(5)
    pdf.chapter_title('VI', 'Developer Quickstart & Deployment')
    
    pdf.heading_2('Step 1: Running the FastAPI Backend Server')
    pdf.paragraph(
        "Activate your Python virtual environment, install requirements, and run the API server. "
        "FastAPI will spin up necessary SQLite structures inside 'charvis.db' automatically on its initial boot."
    )
    
    cmd_backend = [
        "cd backend",
        "python3 -m venv venv",
        "source venv/bin/activate",
        "pip install -r requirements.txt",
        "uvicorn app.main:app --reload --port 8000"
    ]
    pdf.code_block(cmd_backend)
    
    pdf.heading_2('Step 2: Booting the visual React Flow Editor')
    pdf.paragraph(
        "Open a separate terminal shell, navigate to the Next.js frontend folder, and boot the developmental server."
    )
    
    cmd_frontend = [
        "cd frontend",
        "npm install",
        "npm run dev"
    ]
    pdf.code_block(cmd_frontend)
    
    pdf.heading_2('Step 3: Standalone CLI Offline Execution')
    pdf.paragraph(
        "To run complex agent pipelines entirely offline from your terminal, invoke the standalone CLI runner utility:"
    )
    
    cmd_cli = [
        "python runner.py --pipeline sample.json --mode LOCAL --input raw_data='hello'"
    ]
    pdf.code_block(cmd_cli)

    # ----------------------------------------------------
    # PAGE 7: SECURITY CODE WALKTHROUGH & LOGS
    # ----------------------------------------------------
    pdf.add_page()
    pdf.ln(5)
    pdf.chapter_title('VII', 'AST Static Security Verification Sample')
    pdf.paragraph(
        "The following script is a representation of how the AST Static Compiler analyzes input code lines. "
        "It parses modules statically and checks node elements before permitting execution:"
    )
    
    code_sample = [
        "import ast",
        "class SecurityValidator(ast.NodeVisitor):",
        "    def visit_Import(self, node):",
        "        for alias in node.names:",
        "            if alias.name not in ALLOWED_MODULES:",
        "                raise ValueError(f'Import {alias.name} is forbidden!')",
        "        self.generic_visit(node)",
        "",
        "    def visit_Attribute(self, node):",
        "        if node.attr.startswith('__'):",
        "            raise ValueError(f'Dunder attribute {node.attr} blocked!')",
        "        self.generic_visit(node)"
    ]
    pdf.code_block(code_sample)
    
    pdf.heading_2('Execution Logging & Verification')
    pdf.paragraph(
        "Every single code execution, stdout output, intermediate thought, and model query is recorded "
        "relationally. Developers can poll logs in real-time or review the terminal trace panel inside the "
        " Next.js visual client drawer. This ensures complete observability, making debugging complex topologies "
        "and agent scripts highly deterministic and robust."
    )
    pdf.paragraph(
        "Charvis democratizes advanced agent orchestration, keeping compute costs minimal and data privacy absolute. "
        "Happy building!"
    )
    
    # Save target PDF
    output_filename = 'charvis_project_documentation.pdf'
    pdf.output(output_filename)
    print(f"Success: Technical PDF manual compiled at '{output_filename}'.")

if __name__ == '__main__':
    generate_pdf()

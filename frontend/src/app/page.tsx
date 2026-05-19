"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  Handle,
  Position,
} from "@xyflow/react";
import {
  Play,
  Sparkles,
  Terminal,
  Search,
  Globe,
  FileText,
  Edit,
  Database,
  Cpu,
  Layers,
  Settings,
  History,
  X,
  CheckCircle,
  AlertCircle,
  Loader2,
  Download,
  Info,
  ExternalLink,
} from "lucide-react";

// API Base URL mapping - matches our FastAPI backend configuration
const API_BASE = "http://localhost:8000";

// --- Custom React Flow Agent Node Component ---

const CustomAgentNode = ({ data }: any) => {
  const getTaskIcon = (task: string) => {
    switch (task?.toLowerCase()) {
      case "python_execution":
        return <Terminal className="w-4 h-4 text-violet-400" />;
      case "web_search":
        return <Search className="w-4 h-4 text-amber-400" />;
      case "translation":
        return <Globe className="w-4 h-4 text-cyan-400" />;
      case "summarization":
        return <FileText className="w-4 h-4 text-emerald-400" />;
      default:
        return <Edit className="w-4 h-4 text-indigo-400" />;
    }
  };

  const getTaskColor = (task: string) => {
    switch (task?.toLowerCase()) {
      case "python_execution":
        return "border-violet-500/30 bg-violet-950/10 text-violet-300 shadow-violet-500/5";
      case "web_search":
        return "border-amber-500/30 bg-amber-950/10 text-amber-300 shadow-amber-500/5";
      case "translation":
        return "border-cyan-500/30 bg-cyan-950/10 text-cyan-300 shadow-cyan-500/5";
      case "summarization":
        return "border-emerald-500/30 bg-emerald-950/10 text-emerald-300 shadow-emerald-500/5";
      default:
        return "border-indigo-500/30 bg-indigo-950/10 text-indigo-300 shadow-indigo-500/5";
    }
  };

  const status = data.status || "PENDING";
  let statusBorder = "border-slate-800/80";
  let statusGlow = "";

  if (status === "RUNNING") {
    statusBorder = "border-amber-500 node-pulse-running";
    statusGlow = "shadow-[0_0_15px_rgba(245,158,11,0.2)]";
  } else if (status === "SUCCESS") {
    statusBorder = "border-emerald-500";
    statusGlow = "shadow-[0_0_15px_rgba(16,185,129,0.2)]";
  } else if (status === "FAILED") {
    statusBorder = "border-rose-500";
    statusGlow = "shadow-[0_0_15px_rgba(244,63,94,0.2)]";
  }

  const isSelected = data.isSelected;

  return (
    <div
      className={`glass-panel p-4 rounded-xl w-60 border-2 transition-all duration-300 ${statusBorder} ${statusGlow} ${
        isSelected ? "ring-2 ring-indigo-500 border-indigo-400" : ""
      }`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-slate-700 !border-slate-800 !w-3 !h-3"
      />
      
      {/* Node Header */}
      <div className="flex items-center justify-between mb-2">
        <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[10px] font-semibold ${getTaskColor(data.task_type)}`}>
          {getTaskIcon(data.task_type)}
          <span>{data.task_type?.replace("_", " ").toUpperCase()}</span>
        </div>
        
        {/* Node Execution Status */}
        <div>
          {status === "PENDING" && <div className="w-2.5 h-2.5 rounded-full bg-slate-600 animate-pulse" title="Pending" />}
          {status === "RUNNING" && <Loader2 className="w-3.5 h-3.5 text-amber-500 animate-spin" />}
          {status === "SUCCESS" && <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />}
          {status === "FAILED" && <AlertCircle className="w-3.5 h-3.5 text-rose-500" />}
        </div>
      </div>

      {/* Node Content */}
      <div className="mb-2">
        <h4 className="text-sm font-semibold text-slate-100 truncate">{data.id}</h4>
        <p className="text-[11px] text-slate-400 mt-1.5 line-clamp-2 italic">
          "{data.prompt}"
        </p>
      </div>

      {/* Model Tag */}
      <div className="flex items-center justify-between border-t border-slate-800/60 pt-2 text-[10px] text-slate-400">
        <span className="truncate max-w-[120px] font-mono text-slate-500" title={data.model_id}>
          {data.model_id?.split("/").pop()}
        </span>
        <span className="bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800 font-mono text-slate-400">
          {data.output_variable}
        </span>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-slate-700 !border-slate-800 !w-3 !h-3"
      />
    </div>
  );
};

// Node mappings
const nodeTypes = {
  customAgentNode: CustomAgentNode,
};

// --- Main Dashboard Page Component ---

export default function CharvisDashboard() {
  const [prompt, setPrompt] = useState("");
  const [generating, setGenerating] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [executionMode, setExecutionMode] = useState<"SERVERLESS" | "LOCAL">("SERVERLESS");
  
  // Pipeline details
  const [activePipeline, setActivePipeline] = useState<any>(null);
  const [activeExecution, setActiveExecution] = useState<any>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  
  // Storage lists
  const [pipelinesHistory, setPipelinesHistory] = useState<any[]>([]);
  const [cachedModels, setCachedModels] = useState<any[]>([]);
  const [newModelId, setNewModelId] = useState("");
  
  // API credentials settings
  const [apiKey, setApiKey] = useState("");
  const [apiBase, setApiBase] = useState("https://api.openai.com/v1");
  const [hfToken, setHfToken] = useState("");
  
  // UI Panels toggles
  const [showSettings, setShowSettings] = useState(false);
  const [pollingActive, setPollingActive] = useState(false);
  
  // React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState<any>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<any>([]);
  
  const pollingRef = useRef<any>(null);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  // --- Load localStorage Preferences ---
  useEffect(() => {
    if (typeof window !== "undefined") {
      setApiKey(localStorage.getItem("charvis_api_key") || "");
      setApiBase(localStorage.getItem("charvis_api_base") || "https://api.openai.com/v1");
      setHfToken(localStorage.getItem("charvis_hf_token") || "");
    }
    fetchHistory();
    fetchCachedModels();
  }, []);

  // Save changes
  const savePreferences = () => {
    localStorage.setItem("charvis_api_key", apiKey);
    localStorage.setItem("charvis_api_base", apiBase);
    localStorage.setItem("charvis_hf_token", hfToken);
    setShowSettings(false);
    alert("Preferences saved successfully!");
  };

  // --- Fetch API Handlers ---

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/pipelines`);
      if (res.ok) {
        const data = await res.json();
        setPipelinesHistory(data);
      }
    } catch (e) {
      console.error("Failed to load pipeline history", e);
    }
  };

  const fetchCachedModels = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/models/cache`);
      if (res.ok) {
        const data = await res.json();
        setCachedModels(data.repos || []);
      }
    } catch (e) {
      console.error("Failed to load cached models", e);
    }
  };

  const triggerModelDownload = async () => {
    if (!newModelId) return;
    try {
      const res = await fetch(`${API_BASE}/api/models/download?model_id=${encodeURIComponent(newModelId)}`, {
        method: "POST"
      });
      if (res.ok) {
        alert("Model download queued in the background!");
        setNewModelId("");
        fetchCachedModels();
      } else {
        alert("Failed to queue model download. Check repo ID.");
      }
    } catch (e) {
      alert("Error triggering download.");
    }
  };

  // --- DAG Generation Handler ---

  const generatePipeline = async () => {
    if (!prompt.trim()) return;
    setGenerating(true);
    setActiveExecution(null);
    setSelectedNodeId(null);
    
    try {
      const res = await fetch(`${API_BASE}/api/pipelines/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });

      if (res.ok) {
        const pipeline = await res.json();
        loadPipelineToCanvas(pipeline);
        fetchHistory();
      } else {
        alert("Pipeline synthesis failed. Check terminal backend logs.");
      }
    } catch (err) {
      console.error(err);
      alert("Backend connection failed. Ensure FastAPI is running on port 8000.");
    } finally {
      setGenerating(false);
    }
  };

  // --- Render DAG JSON to React Flow Canvas ---

  const loadPipelineToCanvas = (pipeline: any) => {
    setActivePipeline(pipeline);
    setActiveExecution(null);
    setSelectedNodeId(null);

    const dag = pipeline.dag_json;
    const rawNodes = dag.nodes || [];
    const rawEdges = dag.edges || [];

    // Auto layout nodes in vertical space
    const mappedNodes = rawNodes.map((node: any, idx: number) => {
      // Calculate simple hierarchical layout coords
      // Find tier based on dependency depth
      let tier = 0;
      let tempDeps = [...(node.dependencies || [])];
      while (tempDeps.length > 0) {
        tier++;
        // find parents of parents
        const parentNodes = rawNodes.filter((rn: any) => tempDeps.includes(rn.id));
        tempDeps = [];
        parentNodes.forEach((pn: any) => {
          if (pn.dependencies) tempDeps.push(...pn.dependencies);
        });
      }

      return {
        id: node.id,
        type: "customAgentNode",
        position: { x: 150 + tier * 280, y: 100 + (idx % 3) * 150 },
        data: {
          ...node,
          status: "PENDING",
          isSelected: false,
        },
      };
    });

    // Structure edges with glowing visual markers
    const mappedEdges = rawEdges.map((edge: any) => ({
      id: `e-${edge.source}-${edge.target}`,
      source: edge.source,
      target: edge.target,
      animated: false,
      style: { stroke: "#334155", strokeWidth: 2 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: "#334155",
      },
    }));

    setNodes(mappedNodes);
    setEdges(mappedEdges);
  };

  // --- Pipeline DAG Execution Handler ---

  const executePipeline = async () => {
    if (!activePipeline) return;
    setExecuting(true);
    
    // Seed initial pipeline parameters depending on structure
    const inputs: any = {};
    const lowerPrompt = activePipeline.user_prompt.toLowerCase();
    
    if (lowerPrompt.includes("csv") || lowerPrompt.includes("data")) {
      inputs["raw_data"] = "Product,Sales,Region,Date\nLaptops,15000,North,2026-05-01\nPhones,22000,South,2026-05-02\nLaptops,18000,East,2026-05-03\nTablets,8000,West,2026-05-04\nPhones,24000,North,2026-05-05";
    } else {
      inputs["user_query"] = activePipeline.user_prompt;
      inputs["input_text"] = "Charvis is an agentic orchestration platform that is set to democratize model running. By running quantized models directly inside an AST sandbox locally, users preserve absolute data privacy while avoiding high infrastructure costs. Downstream compilation is handled offline.";
    }

    try {
      const res = await fetch(`${API_BASE}/api/pipelines/${activePipeline.id}/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          inputs: inputs,
          execution_mode: executionMode,
        }),
      });

      if (res.ok) {
        const execution = await res.json();
        setActiveExecution(execution);
        startPolling(execution.id);
      } else {
        alert("Workflow execution failed to trigger.");
        setExecuting(false);
      }
    } catch (err) {
      console.error(err);
      alert("Failed to execute. Is the backend offline?");
      setExecuting(false);
    }
  };

  // --- Real-time State Polling (1.5s Interval) ---

  const startPolling = (execId: string) => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    setPollingActive(true);

    pollingRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/executions/${execId}`);
        if (!res.ok) return;
        
        const execution = await res.json();
        setActiveExecution(execution);

        // Update nodes statuses inside React Flow state
        setNodes((prevNodes) =>
          prevNodes.map((n) => {
            const nodeExec = execution.node_executions?.find((ne: any) => ne.node_id === n.id);
            return {
              ...n,
              data: {
                ...n.data,
                status: nodeExec ? nodeExec.status : "PENDING",
              },
            };
          })
        );

        // Update edge animations based on active node runs
        setEdges((prevEdges) =>
          prevEdges.map((e) => {
            const sourceExec = execution.node_executions?.find((ne: any) => ne.node_id === e.source);
            
            let color = "#334155";
            let animate = false;

            if (sourceExec) {
              if (sourceExec.status === "RUNNING") {
                color = "#f59e0b"; // pulsing amber
                animate = true;
              } else if (sourceExec.status === "SUCCESS") {
                color = "#10b981"; // glowing green
              } else if (sourceExec.status === "FAILED") {
                color = "#f43f5e"; // solid red
              }
            }

            return {
              ...e,
              animated: animate,
              style: { stroke: color, strokeWidth: animate ? 3 : 2 },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                color: color,
              },
            };
          })
        );

        // Stop polling if pipeline execution finished
        if (execution.status === "SUCCESS" || execution.status === "FAILED") {
          clearInterval(pollingRef.current);
          setPollingActive(false);
          setExecuting(false);
        }
      } catch (err) {
        console.error("Error polling execution status", err);
      }
    }, 1500);
  };

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  // Node clicked callback
  const onNodeClick = useCallback((_: any, node: any) => {
    setSelectedNodeId(node.id);
    
    // Highlight the selected node visually
    setNodes((prevNodes) =>
      prevNodes.map((n) => ({
        ...n,
        data: {
          ...n.data,
          isSelected: n.id === node.id,
        },
      }))
    );
  }, [setNodes]);

  // Terminal Auto Scroll to Bottom when logs append
  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [activeExecution, selectedNodeId]);

  // Get active selected node db execution record
  const getSelectedNodeRecord = () => {
    if (!selectedNodeId || !activeExecution) return null;
    return activeExecution.node_executions?.find((ne: any) => ne.node_id === selectedNodeId);
  };

  const getSelectedNodeData = () => {
    if (!selectedNodeId || !activePipeline) return null;
    return activePipeline.dag_json.nodes?.find((n: any) => n.id === selectedNodeId);
  };

  const selectedNodeRecord = getSelectedNodeRecord();
  const selectedNodeData = getSelectedNodeData();

  return (
    <div className="flex h-screen w-screen overflow-hidden">
      
      {/* 1. LEFT SIDEBAR PANEL: CONFLICTS & CONTROLS */}
      <aside className="w-80 h-full glass-panel border-r border-slate-800/80 flex flex-col z-20">
        
        {/* Sidebar Header */}
        <div className="p-5 border-b border-slate-800/60 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-indigo-600 p-1.5 rounded-lg shadow-lg shadow-indigo-600/30">
              <Layers className="w-5 h-5 text-indigo-100" />
            </div>
            <div>
              <h1 className="text-md font-black tracking-wider text-slate-100 bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
                CHARVIS
              </h1>
              <p className="text-[10px] text-indigo-400/80 font-mono tracking-tighter">AI Agent Pipeline Gen</p>
            </div>
          </div>
          
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-1.5 rounded-lg border border-slate-800/80 hover:bg-slate-800/60 text-slate-400 hover:text-slate-100 transition-colors"
            title="Configure API Keys"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>

        {/* Action Panel Container */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          
          {/* Settings Section (Conditional Slide-Down) */}
          {showSettings && (
            <div className="p-3.5 rounded-xl border border-indigo-500/20 bg-indigo-950/10 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-1.5">
                <span className="text-xs font-semibold text-indigo-300">Preferences Settings</span>
                <button onClick={() => setShowSettings(false)} className="text-slate-500 hover:text-slate-300">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="space-y-2 text-[11px]">
                <div>
                  <label className="block text-slate-400 mb-1">Together AI / OpenAI Key</label>
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="sk-..."
                    className="w-full bg-[#0b0c16] border border-slate-800/80 rounded px-2 py-1 text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">OpenAI Compatible Base URL</label>
                  <input
                    type="text"
                    value={apiBase}
                    onChange={(e) => setApiBase(e.target.value)}
                    className="w-full bg-[#0b0c16] border border-slate-800/80 rounded px-2 py-1 text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Hugging Face Token</label>
                  <input
                    type="password"
                    value={hfToken}
                    onChange={(e) => setHfToken(e.target.value)}
                    placeholder="hf_..."
                    className="w-full bg-[#0b0c16] border border-slate-800/80 rounded px-2 py-1 text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
                <button
                  onClick={savePreferences}
                  className="w-full mt-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded py-1 px-2 font-semibold text-center transition-colors shadow-lg shadow-indigo-600/20"
                >
                  Save Keys Locally
                </button>
              </div>
            </div>
          )}

          {/* Generator Input Section */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <span>Prompt Pipeline Generator</span>
            </h3>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g., Analyze sales data from a CSV, generate trends via Python execution, summarize anomalies, and translate the text report into Spanish."
              className="w-full h-28 bg-[#090a12] border border-slate-800/80 rounded-xl p-3 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500/60 focus:ring-1 focus:ring-indigo-500/30 transition-all resize-none"
            />
            
            {/* Quick Examples */}
            <div className="flex flex-wrap gap-1">
              <button
                onClick={() => setPrompt("Search the web for news about Google Gemini 3, summarize and write a blog draft, and do a sentiment analysis.")}
                className="text-[9px] bg-slate-900 border border-slate-800/60 text-slate-400 px-1.5 py-0.5 rounded hover:border-slate-700 hover:text-slate-300 transition-colors"
              >
                🔍 Gemini News
              </button>
              <button
                onClick={() => setPrompt("Take standard text input, summarize it into bullet points, and write a targeted creative newsletter.")}
                className="text-[9px] bg-slate-900 border border-slate-800/60 text-slate-400 px-1.5 py-0.5 rounded hover:border-slate-700 hover:text-slate-300 transition-colors"
              >
                📰 Newsletter Expansion
              </button>
            </div>

            <button
              onClick={generatePipeline}
              disabled={generating || !prompt.trim()}
              className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-xl py-2.5 px-4 font-semibold text-xs transition-all disabled:opacity-55 shadow-lg shadow-indigo-600/10 active:scale-[0.98]"
            >
              {generating ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Synthesizing AI DAG...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Generate AI Pipeline</span>
                </>
              )}
            </button>
          </div>

          {/* Compute Driver Toggles */}
          {activePipeline && (
            <div className="p-3 rounded-xl border border-slate-800/60 bg-[#090a12] space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-400">Compute Layer Driver</span>
                <span className="text-[9px] bg-indigo-950 border border-indigo-500/20 text-indigo-400 px-1.5 py-0.5 rounded font-mono font-semibold">V1 Hybrid</span>
              </div>
              
              <div className="grid grid-cols-2 gap-1.5 bg-[#06070a] p-1 rounded-lg border border-slate-900">
                <button
                  onClick={() => setExecutionMode("SERVERLESS")}
                  className={`flex flex-col items-center justify-center p-2 rounded-md transition-all ${
                    executionMode === "SERVERLESS"
                      ? "bg-slate-950 text-indigo-300 border border-indigo-500/20 shadow-md"
                      : "text-slate-500 hover:text-slate-300"
                  }`}
                >
                  <Cpu className="w-3.5 h-3.5 mb-1" />
                  <span className="text-[10px] font-semibold">Serverless API</span>
                </button>
                <button
                  onClick={() => setExecutionMode("LOCAL")}
                  className={`flex flex-col items-center justify-center p-2 rounded-md transition-all ${
                    executionMode === "LOCAL"
                      ? "bg-slate-950 text-indigo-300 border border-indigo-500/20 shadow-md"
                      : "text-slate-500 hover:text-slate-300"
                  }`}
                >
                  <Database className="w-3.5 h-3.5 mb-1" />
                  <span className="text-[10px] font-semibold">Local (GGUF)</span>
                </button>
              </div>

              <button
                onClick={executePipeline}
                disabled={executing || generating}
                className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl py-2.5 px-4 font-semibold text-xs transition-all disabled:opacity-55 active:scale-[0.98]"
              >
                {executing ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Running AI Agents...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5" />
                    <span>Execute Workflow</span>
                  </>
                )}
              </button>
            </div>
          )}

          {/* Model Cache Downloader Manager */}
          <div className="p-3 rounded-xl border border-slate-800/60 bg-[#090a12] space-y-2">
            <h4 className="text-[11px] font-semibold text-slate-400 flex items-center gap-1">
              <Database className="w-3 h-3 text-slate-500" />
              <span>Hugging Face Hub Downloader</span>
            </h4>
            <div className="flex gap-1.5">
              <input
                type="text"
                value={newModelId}
                onChange={(e) => setNewModelId(e.target.value)}
                placeholder="meta-llama/Llama-3-8B-Instruct"
                className="flex-1 bg-[#06070a] border border-slate-800/80 rounded px-2 py-1 text-[10px] font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
              />
              <button
                onClick={triggerModelDownload}
                className="bg-slate-900 border border-slate-800 hover:border-slate-700 p-1.5 rounded text-slate-400 hover:text-slate-200 transition-colors"
                title="Download Model"
              >
                <Download className="w-3.5 h-3.5" />
              </button>
            </div>
            
            {cachedModels.length > 0 ? (
              <div className="space-y-1 pt-1">
                <span className="text-[9px] font-mono text-slate-500 block">Cached Models:</span>
                <div className="max-h-24 overflow-y-auto space-y-1">
                  {cachedModels.map((repo, i) => (
                    <div key={i} className="text-[10px] bg-slate-950 p-1 rounded border border-slate-900 flex justify-between items-center font-mono">
                      <span className="text-slate-400 truncate max-w-[130px]" title={repo.repo_id}>
                        {repo.repo_id?.split("/").pop()}
                      </span>
                      <span className="text-indigo-400 text-[8px]">{repo.size_str}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <span className="text-[9px] font-mono text-slate-600 block">No model files cached. Downloads fallback automatically in local modes.</span>
            )}
          </div>

          {/* Pipelines Synthesis History */}
          {pipelinesHistory.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <History className="w-3.5 h-3.5 text-indigo-400" />
                <span>Workflow History</span>
              </h3>
              <div className="space-y-1.5 max-h-40 overflow-y-auto">
                {pipelinesHistory.map((pipeline) => (
                  <div
                    key={pipeline.id}
                    onClick={() => loadPipelineToCanvas(pipeline)}
                    className={`p-2.5 rounded-lg border text-left cursor-pointer transition-all ${
                      activePipeline?.id === pipeline.id
                        ? "bg-indigo-950/20 border-indigo-500/40"
                        : "bg-[#090a12] border-slate-900 hover:border-slate-800 hover:bg-[#0d0f1a]"
                    }`}
                  >
                    <h4 className="text-[11px] font-bold text-slate-200 truncate">{pipeline.title}</h4>
                    <p className="text-[9px] text-slate-400 mt-1 line-clamp-1 italic">"{pipeline.user_prompt}"</p>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>

        {/* Footer info banner */}
        <div className="p-4 border-t border-slate-800/60 bg-[#06070a]/90 text-[10px] text-slate-500 flex items-center gap-2">
          <Info className="w-3 h-3 flex-shrink-0 text-slate-600" />
          <span>Charvis constructs topological DAG steps and routes autonomous tool calling offline.</span>
        </div>

      </aside>

      {/* 2. MAIN CONTAINER: CANVAS VIEW LAYER */}
      <main className="flex-1 h-full relative z-10 flex flex-col">
        
        {/* Top visual navigation path */}
        <div className="h-14 glass-panel border-b border-slate-800/80 flex items-center justify-between px-6 z-20">
          <div>
            {activePipeline ? (
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold bg-indigo-950 border border-indigo-500/30 text-indigo-400 px-2 py-0.5 rounded-full">Active Pipeline</span>
                <h2 className="text-sm font-bold text-slate-200">{activePipeline.title}</h2>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-slate-400 text-xs">
                <span>Start by entering natural language prompt on the left to synthesize a workflow.</span>
              </div>
            )}
          </div>
          
          <div className="flex items-center gap-4">
            {activeExecution && (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-500 font-mono">Status:</span>
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                    activeExecution.status === "SUCCESS"
                      ? "bg-emerald-950 text-emerald-400 border border-emerald-500/20"
                      : activeExecution.status === "RUNNING"
                      ? "bg-amber-950 text-amber-400 border border-amber-500/20 animate-pulse"
                      : activeExecution.status === "FAILED"
                      ? "bg-rose-950 text-rose-400 border border-rose-500/20"
                      : "bg-slate-900 text-slate-400 border border-slate-800"
                  }`}
                >
                  {activeExecution.status}
                </span>
              </div>
            )}
            
            <a
              href="https://huggingface.co/models"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[10px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-mono transition-colors"
            >
              <span>HF HUB</span>
              <ExternalLink className="w-2.5 h-2.5" />
            </a>
          </div>
        </div>

        {/* React Flow Canvas Wrapper */}
        <div className="flex-1 w-full h-full relative bg-[#06070a]">
          {nodes.length > 0 ? (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              nodeTypes={nodeTypes}
              fitView
              className="w-full h-full"
            >
              <Background color="#1e1b4b" gap={16} size={1} />
              <Controls />
              <MiniMap nodeStrokeWidth={3} zoomable pannable />
            </ReactFlow>
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-6 bg-[#06070a]/90 space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-indigo-950/20 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shadow-xl shadow-indigo-500/5 animate-pulse">
                <Layers className="w-8 h-8" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-200">No Pipeline Loaded</h3>
                <p className="text-slate-500 text-xs max-w-sm mt-1">
                  Type in your pipeline requirement inside the left sidebar. Charvis will map models, ports, and connections dynamically.
                </p>
              </div>
            </div>
          )}
        </div>

      </main>

      {/* 3. SLIDE-OUT LOG DRAWER PANEL: DETAILED STEP LOGS */}
      {selectedNodeId && selectedNodeData && (
        <aside className="w-96 h-full glass-panel border-l border-slate-800/80 flex flex-col z-20 relative">
          
          {/* Drawer Header */}
          <div className="p-4 border-b border-slate-800/60 flex items-center justify-between bg-slate-950/40">
            <div>
              <div className="text-[9px] font-bold text-slate-500 tracking-wider">SELECTED AGENT NODE</div>
              <h3 className="text-sm font-bold text-slate-100">{selectedNodeId}</h3>
            </div>
            
            <button
              onClick={() => {
                setSelectedNodeId(null);
                setNodes((prevNodes) =>
                  prevNodes.map((n) => ({ ...n, data: { ...n.data, isSelected: false } }))
                );
              }}
              className="p-1 rounded-md text-slate-400 hover:text-slate-100 hover:bg-slate-800/40"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Drawer Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
            
            {/* Step Status Banner */}
            <div className="p-3 rounded-xl border border-slate-800 bg-slate-950/30 flex justify-between items-center">
              <span className="font-semibold text-slate-400">Step Status:</span>
              <span
                className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase ${
                  (selectedNodeRecord?.status || "PENDING") === "SUCCESS"
                    ? "bg-emerald-950 text-emerald-400 border border-emerald-500/20"
                    : (selectedNodeRecord?.status || "PENDING") === "RUNNING"
                    ? "bg-amber-950 text-amber-400 border border-amber-500/20 animate-pulse"
                    : (selectedNodeRecord?.status || "PENDING") === "FAILED"
                    ? "bg-rose-950 text-rose-400 border border-rose-500/20"
                    : "bg-slate-900 text-slate-400 border border-slate-800"
                }`}
              >
                {selectedNodeRecord?.status || "PENDING"}
              </span>
            </div>

            {/* Prompt Config */}
            <div className="space-y-1.5">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Agent Instruction:</span>
              <p className="p-3 rounded-xl border border-slate-800 bg-[#06070a]/65 text-slate-300 leading-relaxed italic text-[11px]">
                "{selectedNodeData.prompt}"
              </p>
            </div>

            {/* Model & Output Configs */}
            <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
              <div className="p-2.5 rounded-xl border border-slate-800 bg-slate-950/20">
                <span className="text-[9px] text-slate-500 block">PROVISIONED MODEL</span>
                <span className="text-slate-300 truncate block mt-0.5">{selectedNodeData.model_id?.split("/").pop()}</span>
              </div>
              <div className="p-2.5 rounded-xl border border-slate-800 bg-slate-950/20">
                <span className="text-[9px] text-slate-500 block">OUTPUT BIND KEY</span>
                <span className="text-slate-300 truncate block mt-0.5">{selectedNodeData.output_variable}</span>
              </div>
            </div>

            {/* Context Inputs and Outputs Inspection */}
            {selectedNodeRecord && (
              <div className="space-y-3">
                
                {/* Inputs Inspector */}
                <div className="space-y-1.5">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Input Bindings:</span>
                  <div className="p-2 rounded-xl border border-slate-800 bg-[#06070a] space-y-1 font-mono text-[10px] max-h-32 overflow-y-auto">
                    {selectedNodeRecord.inputs && Object.keys(selectedNodeRecord.inputs).length > 0 ? (
                      Object.entries(selectedNodeRecord.inputs).map(([k, v]: any) => (
                        <div key={k} className="border-b border-slate-900 pb-1 last:border-0 last:pb-0">
                          <span className="text-indigo-400 font-bold">{k}:</span>
                          <span className="text-slate-400 block text-[9px] line-clamp-2 mt-0.5">{String(v)}</span>
                        </div>
                      ))
                    ) : (
                      <span className="text-slate-600 italic">No input keys mapped. Seeded from pipeline inputs.</span>
                    )}
                  </div>
                </div>

                {/* Outputs Inspector */}
                {selectedNodeRecord.status === "SUCCESS" && (
                  <div className="space-y-1.5">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Generated Outputs:</span>
                    <div className="p-2.5 rounded-xl border border-slate-800 bg-[#06070a] font-mono text-[10px] max-h-36 overflow-y-auto leading-relaxed">
                      {selectedNodeRecord.outputs && Object.keys(selectedNodeRecord.outputs).length > 0 ? (
                        Object.entries(selectedNodeRecord.outputs).map(([k, v]: any) => (
                          <div key={k}>
                            <span className="text-emerald-400 font-bold block">{k}:</span>
                            <span className="text-slate-300 block text-[10px] mt-1 bg-[#040508] p-2 rounded border border-slate-900">{String(v)}</span>
                          </div>
                        ))
                      ) : (
                        <span className="text-slate-600 italic">No outputs recorded yet.</span>
                      )}
                    </div>
                  </div>
                )}

                {/* Node Error details */}
                {selectedNodeRecord.status === "FAILED" && selectedNodeRecord.error_message && (
                  <div className="space-y-1.5">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Error Exception:</span>
                    <div className="p-3 rounded-xl border border-rose-500/20 bg-rose-950/15 font-mono text-[10px] text-rose-400 overflow-x-auto leading-relaxed">
                      {selectedNodeRecord.error_message}
                    </div>
                  </div>
                )}

              </div>
            )}

            {/* Live Terminal Output Console */}
            <div className="space-y-2">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block flex items-center gap-1">
                <Terminal className="w-3.5 h-3.5 text-indigo-400" />
                <span>Agent Execution Terminal Logs</span>
              </span>
              
              <div className="w-full h-64 bg-[#040508] border border-slate-800/80 rounded-xl p-3 font-mono text-[9px] text-indigo-300 overflow-y-auto overflow-x-hidden leading-relaxed shadow-inner">
                {selectedNodeRecord?.logs ? (
                  <div className="whitespace-pre-wrap break-all space-y-1">
                    {selectedNodeRecord.logs}
                    <div ref={terminalEndRef} />
                  </div>
                ) : (
                  <span className="text-slate-700 italic">
                    {selectedNodeRecord?.status === "PENDING"
                      ? "Waiting in queue to start execution..."
                      : selectedNodeRecord?.status === "RUNNING"
                      ? "Initializing agent engine, spawning tool sandboxes and running inference..."
                      : "No execution logs recorded."}
                  </span>
                )}
              </div>
            </div>

          </div>

          {/* Close details button */}
          <div className="p-3 border-t border-slate-800/60 bg-slate-950/40 text-center">
            <button
              onClick={() => {
                setSelectedNodeId(null);
                setNodes((prevNodes) =>
                  prevNodes.map((n) => ({ ...n, data: { ...n.data, isSelected: false } }))
                );
              }}
              className="w-full py-1.5 rounded-lg border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-slate-200 transition-all font-semibold text-xs active:scale-[0.98]"
            >
              Minimize Panel
            </button>
          </div>

        </aside>
      )}

    </div>
  );
}

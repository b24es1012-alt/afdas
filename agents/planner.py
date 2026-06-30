"""
Planner agent — the central brain of AFDAS.
Creates execution plans and orchestrates tool calls using LangGraph.
"""

import json
import re
from typing import List, Dict, Any, Optional, TypedDict, Annotated
from itertools import groupby
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END, add_messages

from agents.classifier import classify_query, QueryCategory
from agents.vehicle_agent import detect_vehicle
from agents.tool_selector import select_tools, get_tool_descriptions
from agents.response_agent import generate_response
from config.settings import settings
from utils.logger import agent_logger as logger


# ============================================================================
# STATE
# ============================================================================

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    initial_query: str
    plan: list
    current_group_index: int
    current_step: str
    category: str
    vehicle_type: str


# ============================================================================
# PROMPTS
# ============================================================================

PLANNER_PROMPT = PromptTemplate(
    input_variables=["initial_query", "available_tools"],
    template="""You are a PLANNING AGENT for the AFDAS Flood Disaster Assistance System.
Flood data comes from real Copernicus EMS data loaded into PostGIS.

User request: {initial_query}

IMPORTANT: If the user's GPS coordinates are provided in the query (e.g. [User GPS: lat=..., lon=...]),
use those coordinates directly in tools. The user is at THAT location, NOT in Delhi.
Pass the user's actual city/state based on their GPS, not the default "Delhi".

AVAILABLE TOOLS (only use these):
{available_tools}

Create an execution plan. Group independent steps that can run in PARALLEL
into the same "group" number. Steps depending on previous results get a higher group.

GROUPING RULES:
- Same group = PARALLEL execution (no dependency)
- Higher group = AFTER previous group finishes
- get_coordinates_from_location MUST be group 1 if place names need resolving
- calculate_route MUST be after coordinates are resolved

OUTPUT — return ONLY valid JSON, no markdown fences:
{{
  "plan": [
    {{
      "group": 1,
      "step": 1,
      "tool": "<tool_name>",
      "purpose": "<one sentence>",
      "input_description": "<what arguments to pass>"
    }}
  ]
}}""",
)

EXECUTOR_PROMPT = PromptTemplate(
    input_variables=["initial_query", "tool_name", "purpose", "input_description", "previous_results"],
    template="""You are a FLOOD DISASTER EXECUTION AGENT.
Flood data comes from real Copernicus EMS shapefile data.

Original user request: {initial_query}

Previous tool results:
{previous_results}

YOUR TASK:
  Tool: {tool_name}
  Purpose: {purpose}
  Input hint: {input_description}

Using previous results to resolve arguments, call EXACTLY the tool "{tool_name}".
Do NOT call any other tool. Do NOT write a final answer — only the tool call.""",
)


# ============================================================================
# HELPERS
# ============================================================================

def _make_model(with_tools: bool = False, tools: list = None):
    """Create an LLM instance, optionally with tool bindings."""
    model = ChatGroq(
        model=settings.LLM_MODEL,
        temperature=0,
        api_key=settings.GROQ_API_KEY,
    )
    if with_tools and tools:
        return model.bind_tools(tools)
    return model


def _parse_json(text: str) -> dict:
    """Parse JSON from LLM output, handling markdown fences."""
    clean = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    return json.loads(clean)


def _get_groups(plan: list) -> list:
    """Group plan steps by their group number."""
    sorted_plan = sorted(plan, key=lambda s: s["group"])
    return [list(steps) for _, steps in groupby(sorted_plan, key=lambda s: s["group"])]


def _collect_tool_results(messages: list, max_chars: int = 3000) -> str:
    """Collect ToolMessage results from message history."""
    parts = []
    for m in messages:
        if isinstance(m, ToolMessage):
            content = m.content
            if len(content) > max_chars:
                content = content[:max_chars] + f"\n... [truncated]"
            parts.append(f"[{m.name}]: {content}")
    return "\n".join(parts) if parts else "No results yet."



# ============================================================================
# GRAPH NODES
# ============================================================================

async def classification_node(state: AgentState) -> AgentState:
    """Classify the query and reject non-flood requests."""
    query = state["initial_query"]
    category, confidence, reason = await classify_query(query)

    logger.info(f"[CLASSIFIER] {category.value} (conf={confidence:.2f}): {reason}")

    if category == QueryCategory.REJECTED:
        return {
            **state,
            "current_step": "rejected",
            "category": category.value,
        }

    # Detect vehicle
    vehicle = await detect_vehicle(query)
    logger.info(f"[VEHICLE] Detected: {vehicle.vehicle_type.value}")

    return {
        **state,
        "category": category.value,
        "vehicle_type": vehicle.vehicle_type.value,
        "current_step": "classified",
    }


async def planner_node(state: AgentState) -> AgentState:
    """Create an execution plan based on the query and classification."""
    query = state["initial_query"]
    category = QueryCategory(state["category"])

    # Select relevant tools
    available_tools = select_tools(category, query)
    tool_descriptions = get_tool_descriptions()
    tools_text = "\n".join(
        f"  - {name}: {tool_descriptions.get(name, '')}"
        for name in available_tools
    )

    # Generate plan via LLM
    prompt_text = PLANNER_PROMPT.format(
        initial_query=query,
        available_tools=tools_text,
    )

    model = _make_model()
    response = await model.ainvoke([HumanMessage(content=prompt_text)])

    try:
        data = _parse_json(response.content)
        plan = data.get("plan", [])
    except (json.JSONDecodeError, AttributeError) as e:
        logger.error(f"Plan parsing error: {e}")
        plan = []

    groups = _get_groups(plan) if plan else []
    logger.info(f"[PLANNER] {len(plan)} steps across {len(groups)} group(s)")

    return {
        **state,
        "messages": state["messages"] + [response],
        "plan": plan,
        "current_group_index": 0,
        "current_step": "planned",
    }


async def tool_executor_node(state: AgentState, tools_map: dict) -> AgentState:
    """Execute tools for the current group (parallel if multiple)."""
    plan = state["plan"]
    group_idx = state["current_group_index"]
    messages = state["messages"]
    query = state["initial_query"]
    groups = _get_groups(plan)

    if group_idx >= len(groups):
        return {**state, "current_step": "plan_exhausted"}

    current_group = groups[group_idx]
    previous_results = _collect_tool_results(messages[-20:], max_chars=2000)

    all_new_messages = []

    for step in current_group:
        tool_name = step["tool"]
        logger.info(f"  [EXEC] {tool_name}")

        prompt_text = EXECUTOR_PROMPT.format(
            initial_query=query,
            tool_name=tool_name,
            purpose=step["purpose"],
            input_description=step["input_description"],
            previous_results=previous_results,
        )

        tools_list = [tools_map[t] for t in tools_map if t == tool_name]
        model = _make_model(with_tools=True, tools=list(tools_map.values()))
        llm_response = await model.ainvoke([HumanMessage(content=prompt_text)])
        all_new_messages.append(llm_response)

        # Execute tool calls
        if hasattr(llm_response, "tool_calls") and llm_response.tool_calls:
            for tc in llm_response.tool_calls:
                tool_fn = tools_map.get(tc["name"])
                try:
                    result = await tool_fn.ainvoke(tc["args"]) if tool_fn else f"Unknown tool: {tc['name']}"
                except Exception as e:
                    result = f"Error: {e}"
                all_new_messages.append(
                    ToolMessage(content=str(result), tool_call_id=tc["id"], name=tc["name"])
                )

        # Update previous results for next step in same group
        previous_results = _collect_tool_results(
            messages + all_new_messages, max_chars=2000
        )

    return {
        **state,
        "messages": messages + all_new_messages,
        "current_group_index": group_idx + 1,
        "current_step": "group_executed",
    }


async def responder_node(state: AgentState) -> AgentState:
    """Generate final response from all tool results."""
    query = state["initial_query"]
    tool_results = _collect_tool_results(state["messages"])

    response_text = await generate_response(query, tool_results)
    logger.info("[RESPONDER] Final response ready")

    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=response_text)],
        "current_step": "done",
    }


# ============================================================================
# CONDITIONAL EDGES
# ============================================================================

def should_continue_after_classification(state: AgentState) -> str:
    """Route after classification: reject or proceed to planner."""
    if state["current_step"] == "rejected":
        return "rejected"
    return "plan"


def has_more_groups(state: AgentState) -> str:
    """Check if there are more tool groups to execute."""
    groups = _get_groups(state["plan"])
    if state["current_group_index"] < len(groups):
        return "continue"
    return "respond"


# ============================================================================
# GRAPH BUILDER
# ============================================================================

def create_flood_agent_graph(tools_map: dict) -> StateGraph:
    """
    Create the LangGraph workflow for the flood assistance agent.
    
    Args:
        tools_map: Dict of tool_name → tool_function
    
    Returns:
        Compiled LangGraph
    """
    workflow = StateGraph(AgentState)

    # Nodes
    workflow.add_node("classifier", classification_node)
    workflow.add_node("planner", planner_node)

    async def _tool_executor_wrapper(state):
        return await tool_executor_node(state, tools_map)

    workflow.add_node("tool_executor", _tool_executor_wrapper)
    workflow.add_node("responder", responder_node)

    # Entry
    workflow.set_entry_point("classifier")

    # Edges
    workflow.add_conditional_edges(
        "classifier",
        should_continue_after_classification,
        {"rejected": "responder", "plan": "planner"},
    )
    workflow.add_edge("planner", "tool_executor")
    workflow.add_conditional_edges(
        "tool_executor",
        has_more_groups,
        {"continue": "tool_executor", "respond": "responder"},
    )
    workflow.add_edge("responder", END)

    return workflow.compile()


# ============================================================================
# RUN
# ============================================================================

async def run_agent(query: str, tools_map: dict) -> dict:
    """
    Run the flood assistance agent on a user query.
    
    Args:
        query: User's question
        tools_map: Available tools
    
    Returns:
        Final agent state with messages
    """
    agent = create_flood_agent_graph(tools_map)

    result = await agent.ainvoke({
        "messages": [HumanMessage(content=query)],
        "initial_query": query,
        "plan": [],
        "current_group_index": 0,
        "current_step": "start",
        "category": "",
        "vehicle_type": "car",
    })

    return result

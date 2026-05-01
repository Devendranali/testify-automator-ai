# orchestrator/orchestrator.py

import json
from pathlib import Path
from threading import Lock

from mcp.messages import MCPMessage
from agents.python_agent import PlaywrightPythonAgent
from agents.typescript_agent import PlaywrightTypescriptAgent

_AGENTS = {}
_AGENT_LOCK = Lock()


def _manifest_path(filename: str) -> Path:
    return Path(__file__).resolve().parents[1] / "agents" / filename


def _load_agent_manifest(filename: str) -> dict:
    path = _manifest_path(filename)
    if not path.exists():
        raise RuntimeError(f"Agent manifest not found at {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Failed to load agent manifest at {path}: {exc}") from exc


def _get_agent(language: str):
    if language in _AGENTS:
        return _AGENTS[language]
    with _AGENT_LOCK:
        if language in _AGENTS:
            return _AGENTS[language]
        if language == "python":
            manifest = _load_agent_manifest("agent_manifest_python.json")
            _AGENTS[language] = PlaywrightPythonAgent(manifest)
        elif language == "typescript":
            manifest = _load_agent_manifest("agent_manifest_typescript.json")
            _AGENTS[language] = PlaywrightTypescriptAgent(manifest)
        else:
            raise RuntimeError(f"Unknown agent language '{language}'")
    return _AGENTS[language]

def send_message(language, action, payload):
    agent = _get_agent(language)
    msg = MCPMessage(sender="orchestrator", recipient=agent.agent_name, action=action, payload=payload)
    resp = agent.handle_message(msg)
    return resp

# adk_core.py
from typing import Dict, Any, List

class Agent:
    """
    Base class for agents. Override run(self, context) -> context
    """
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Agent must implement run(context)")

class Orchestrator:
    def __init__(self, agents: List[Agent]):
        self.agents = agents

    def run(self, initial_context=None):
        ctx = initial_context or {}
        for agent in self.agents:
            ctx = agent.run(ctx) or ctx
        return ctx

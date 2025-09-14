# agents/insurance_agent.py
from adk_core import Agent

class InsuranceAgent(Agent):
    def run(self, context):
        print("\n=== Insurance Collection ===")
        carrier = input(f"Carrier [{context.get('insurance_carrier','')}]: ").strip() or context.get('insurance_carrier','')
        member = input(f"Member ID [{context.get('member_id','')}]: ").strip() or context.get('member_id','')
        group = input(f"Group ID [{context.get('group_id','')}]: ").strip() or context.get('group_id','')
        context['insurance_carrier'] = carrier
        context['member_id'] = member
        context['group_id'] = group
        return context

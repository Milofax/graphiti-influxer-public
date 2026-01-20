#!/usr/bin/env python3
"""
agent-browser Guard - Enforces agent-browser as the only browser automation tool.

Rules:
- !!agent_browser_only: Block all other browser automation tools
- Playwright MCP → BLOCKED
- Playwright/Puppeteer/Cypress/Selenium CLI → BLOCKED
- agent-browser CLI → ALLOWED
"""
import json, sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from session_state import register_hook

# CLI tools to block (NOT agent-browser)
BLOCKED_CLI = [
    r"(?:npx|npm run|yarn|pnpm)\s+(?:exec\s+)?playwright\b",
    r"(?:npx|npm run|yarn|pnpm)\s+(?:exec\s+)?puppeteer\b",
    r"(?:npx|npm run|yarn|pnpm)\s+(?:exec\s+)?cypress\b",
    r"\bplaywright\s+(?:test|install|codegen|show-report)\b",
    r"\bpuppeteer\s+",
    r"\bcypress\s+(?:run|open|install)\b",
    r"\bselenium-webdriver\b",
    r"\bwebdriver-manager\b",
]

# MCP tools to block (playwright MCP)
BLOCKED_MCP = [
    "playwright",
]

def allow():
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}

def deny(msg):
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": msg}}

def main():
    try:
        hi = json.load(sys.stdin)
    except:
        print(json.dumps(allow()))
        return

    register_hook("agent-browser")
    tn, ti = hi.get("tool_name", ""), hi.get("tool_input", {})

    # Check Bash commands
    if tn == "Bash":
        cmd = ti.get("command", "")
        # Block other browser automation CLIs
        for p in BLOCKED_CLI:
            m = re.search(p, cmd, re.I)
            if m:
                print(json.dumps(deny(f"Browser automation CLI blocked: '{m.group()}'")))
                return

    # Check MCP bridge requests
    if tn == "mcp__mcp-funnel__bridge_tool_request":
        bt = ti.get("tool", "").lower()
        # Block Playwright MCP
        for blocked in BLOCKED_MCP:
            if blocked in bt:
                print(json.dumps(deny(f"Browser automation MCP blocked: '{ti.get('tool')}'")))
                return

    print(json.dumps(allow()))

if __name__ == "__main__":
    main()

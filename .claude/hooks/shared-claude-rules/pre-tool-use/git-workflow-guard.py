#!/usr/bin/env python3
"""
Git Workflow Guard Hook (PreToolUse)

Enforces git workflow rules:
- Conventional Commits format validation
- Branch protection (no direct push to main/develop)
- Force push protection

Triggers: Bash (when command contains git)
"""
import json, sys, os, re, shlex
HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HOOK_DIR, '..', 'lib'))
from session_state import register_hook, read_state

# Conventional Commits types
COMMIT_TYPES = ["feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore"]

# Protected branches (default, can be extended)
PROTECTED_BRANCHES = ["main", "master", "develop"]

def allow():
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}

def deny(msg):
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": msg}}

def parse_git_command(command: str) -> dict | None:
    """
    Parse a bash command to extract git operation details.
    Returns None if not a git command.
    """
    # Normalize command
    cmd = command.strip()

    # Check if it's a git command
    if not re.search(r'\bgit\b', cmd):
        return None

    result = {
        "raw": cmd,
        "operation": None,
        "args": []
    }

    # Try to parse with shlex for proper quoting handling
    try:
        parts = shlex.split(cmd)
    except ValueError:
        # Fallback to simple split if shlex fails
        parts = cmd.split()

    # Find git command position
    git_idx = None
    for i, p in enumerate(parts):
        if p == "git":
            git_idx = i
            break

    if git_idx is None:
        return None

    # Extract operation and args
    remaining = parts[git_idx + 1:]
    if remaining:
        result["operation"] = remaining[0]
        result["args"] = remaining[1:]

    return result

def validate_conventional_commit(message: str) -> tuple[bool, str]:
    """
    Validate commit message against Conventional Commits format.
    Returns (is_valid, error_message).
    """
    # Pattern: type(scope)!: description OR type!: description OR type(scope): description OR type: description
    pattern = r'^(' + '|'.join(COMMIT_TYPES) + r')(\([a-zA-Z0-9_-]+\))?!?:\s+.+'

    if re.match(pattern, message):
        return True, ""

    # Check for common errors
    if not any(message.startswith(t) for t in COMMIT_TYPES):
        types_str = ", ".join(COMMIT_TYPES)
        return False, f"!!conventional_commits: Ungültiger Commit-Typ!\n\nGültige Typen: {types_str}\n\nFormat: type(scope): description\nBeispiel: feat(auth): add login feature"

    if ": " not in message:
        return False, "!!conventional_commits: Fehlender Doppelpunkt+Leerzeichen nach Typ!\n\nFormat: type(scope): description\nBeispiel: fix(api): handle null response"

    return False, "!!conventional_commits: Ungültiges Commit-Format!\n\nFormat: type(scope): description\nBeispiele:\n  feat(auth): add OAuth login\n  fix: correct typo in README"

def check_branch_protection(args: list, operation: str) -> tuple[bool, str]:
    """
    Check if push operation violates branch protection rules.
    Returns (is_allowed, error_message).
    """
    if operation != "push":
        return True, ""

    # Check for force push
    force_flags = ["--force", "-f", "--force-with-lease"]
    has_force = any(f in args for f in force_flags)

    # Try to find target branch
    target_branch = None
    for arg in args:
        if not arg.startswith("-"):
            # Could be remote or branch
            if arg in PROTECTED_BRANCHES:
                target_branch = arg
                break
            # Check for remote:branch or origin branch patterns
            if "/" in arg:
                parts = arg.split("/")
                if parts[-1] in PROTECTED_BRANCHES:
                    target_branch = parts[-1]
                    break

    # Also check last non-flag argument
    non_flag_args = [a for a in args if not a.startswith("-")]
    if len(non_flag_args) >= 2 and non_flag_args[-1] in PROTECTED_BRANCHES:
        target_branch = non_flag_args[-1]

    if target_branch in PROTECTED_BRANCHES:
        # Check state for confirmation
        state = read_state()
        push_confirmed = state.get("protected_push_confirmed", {})

        # Build unique key for this specific push operation
        confirm_key = f"{target_branch}:{'force' if has_force else 'normal'}"

        if push_confirmed.get("key") == confirm_key:
            # Already confirmed, allow
            return True, ""

        if has_force:
            return False, f"!!force_push_warnung: Force-Push zu '{target_branch}' erkannt!\n\n⚠️ Dies überschreibt die Remote-History!\nNur nutzen wenn:\n  • History repariert werden muss\n  • Lokaler Branch definitiv korrekt ist\n  • Niemand anders am Branch arbeitet\n\n→ Falls gewollt: Befehl wiederholen zum Bestätigen"

        return False, f"!!branch_protection: Direkter Push zu '{target_branch}' erkannt!\n\nBest Practice: Feature-Branch → Pull Request → Merge\n\n→ Falls gewollt: Befehl wiederholen zum Bestätigen"

    return True, ""

def extract_commit_message_from_raw(command: str) -> str | None:
    """Extract commit message directly from raw command string using regex.
    Handles HEREDOC patterns like: git commit -m "$(cat <<'EOF'...EOF)"
    """
    # Pattern 1: HEREDOC - git commit -m "$(cat <<'EOF' or <<EOF
    heredoc_match = re.search(r'-m\s*"\$\(cat\s*<<[\'\"]?EOF[\'\"]?\s*\n(.+?)\nEOF', command, re.DOTALL)
    if heredoc_match:
        # Extract first line of HEREDOC content (the actual commit message)
        content = heredoc_match.group(1).strip()
        first_line = content.split('\n')[0].strip()
        return first_line

    # Pattern 2: Simple quoted message - git commit -m "message" or -m 'message'
    simple_match = re.search(r'-m\s*["\']([^"\']+)["\']', command)
    if simple_match:
        return simple_match.group(1)

    # Pattern 3: Unquoted message (rare) - git commit -m message
    unquoted_match = re.search(r'-m\s+(\S+)', command)
    if unquoted_match:
        return unquoted_match.group(1)

    return None

def extract_commit_message(args: list, raw_command: str = None) -> str | None:
    """Extract commit message from git commit arguments.
    Falls back to raw command parsing for complex cases like HEREDOC.
    """
    # First try: parsed args (fast path)
    try:
        for i, arg in enumerate(args):
            if arg == "-m" and i + 1 < len(args):
                return args[i + 1]
            if arg.startswith("-m"):
                # -m"message" or -mmessage
                return arg[2:].strip('"\'')
    except:
        pass

    # Second try: raw command parsing (handles HEREDOC)
    if raw_command:
        return extract_commit_message_from_raw(raw_command)

    return None

def main():
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps(allow()))
        return

    register_hook("git-workflow")

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Only process Bash commands
    if tool_name != "Bash":
        print(json.dumps(allow()))
        return

    command = tool_input.get("command", "")

    # Parse git command
    git_cmd = parse_git_command(command)

    # Not a git command, allow
    if git_cmd is None:
        print(json.dumps(allow()))
        return

    operation = git_cmd.get("operation")
    args = git_cmd.get("args", [])

    # Check commit message format
    if operation == "commit":
        message = extract_commit_message(args, command)
        if message:
            is_valid, error = validate_conventional_commit(message)
            if not is_valid:
                print(json.dumps(deny(error)))
                return

    # Check branch protection for push
    if operation == "push":
        # Determine if force push
        force_flags = ["--force", "-f", "--force-with-lease"]
        has_force = any(f in args for f in force_flags)

        is_allowed, error = check_branch_protection(args, operation)
        if not is_allowed:
            # Store for repeat-to-confirm pattern
            from session_state import write_state
            # Find target branch
            non_flag_args = [a for a in args if not a.startswith("-")]
            if len(non_flag_args) >= 2:
                target = non_flag_args[-1]
            elif len(non_flag_args) == 1:
                target = non_flag_args[0]
            else:
                target = "unknown"

            # Build unique key for this specific push operation
            confirm_key = f"{target}:{'force' if has_force else 'normal'}"

            state = read_state()
            confirmed = state.get("protected_push_confirmed", {})

            if confirmed.get("key") == confirm_key:
                # Already confirmed, clear and allow
                write_state("protected_push_confirmed", {})
                print(json.dumps(allow()))
                return

            # First attempt, store for confirmation
            write_state("protected_push_confirmed", {"key": confirm_key})
            print(json.dumps(deny(error)))
            return

    # All checks passed
    print(json.dumps(allow()))

if __name__ == "__main__":
    main()

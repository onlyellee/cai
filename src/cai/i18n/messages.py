"""
CAI i18n Message Definitions

All user-facing messages are defined here.
To add a new language, add a new dictionary with the language code as key.
"""

EN = {
    # === CLI Core Messages ===
    "turn_limit_increased": "Turn limit increased. You can now continue using CAI.",
    "error_max_turns": "Error: Maximum turn limit ({max_turns}) reached.",
    "config_increase_turns": "You must increase the limit using the /config command: /config CAI_MAX_TURNS=<new_value>",
    "only_cli_commands": "Only CLI commands (starting with '/') will be processed until the limit is increased.",
    "error_switch_agent": "Error switching agent: {error}",
    "error_turn_limit": "Error: Turn limit reached. Only CLI commands are allowed.",
    "increase_turns_hint": "Please use /config to increase CAI_MAX_TURNS limit.",
    "error_agent_run": "{agent_name} execution error",
    "command_failed": "Command failed or unknown: {command}",
    "log_file": "Log file: {filename}",
    "error_general": "Error: {error}",
    "error_traceback": "Traceback: {tb_info}",
    "error_litellm_patch": "Something went wrong patching LiteLLM fix_litellm_transcription_annotations",
    "error_streaming": "Error occurred during streaming: {error}",

    # === Security Guardrails ===
    "guardrail_triggered": "SECURITY GUARDRAIL TRIGGERED",
    "guardrail_name": "Guardrail: {name}",
    "guardrail_reason": "Reason: {reason}",
    "guardrail_output_blocked": "The agent's output was blocked for security reasons.",
    "guardrail_continue": "You can continue the conversation with a different request.",
    "guardrail_input_triggered": "INPUT SECURITY GUARDRAIL TRIGGERED",
    "guardrail_input_blocked": "Your input was blocked for security reasons.",
    "guardrail_history_warning": "This may be due to malicious content in the conversation history.",
    "guardrail_options": "Options:",
    "guardrail_option_clear": "1. Type /clear to clear the conversation history",
    "guardrail_option_disable": "2. Type /config set 26 false to temporarily disable guardrails",
    "guardrail_option_exit": "3. Type /exit to exit CAI",
    "guardrail_rephrase": "Please rephrase your request or try a different approach.",

    # === Session & Cost ===
    "session_cost": "Total CAI Session Cost: ${cost}",
    "warning_pricing_local": "WARNING: Error loading local pricing.json: {error}",
    "warning_pricing_fetch": "WARNING: Error fetching model pricing: {error}",
    "warning_template": "Warning: Failed to render system master template: {error}",

    # === Agent & Tools ===
    "no_agent_visualize": "No agent provided to visualize.",
    "tools_header": "Tools",
    "handoff_info": "{handoff_name} via {tool_name}",
    "error_creating_stream": "Error creating streaming context: {error}",

    # === REPL Commands ===
    "cmd_run_parallel_only": "Error: /run command is only available in parallel mode",
    "cmd_run_enable_parallel": "Enable parallel mode first with appropriate environment variables",
    "cmd_run_no_prompts": "No prompts queued. Use '/run queue <agent> <prompt>' to add prompts.",
    "cmd_run_executing": "Executing {count} queued prompts...",
    "cmd_run_processing": "Prompts configured for parallel execution. Processing will begin now.",
    "cmd_run_agent_prompt_required": "Error: Agent and prompt required",
    "cmd_run_usage_queue": "Usage: /run queue <agent_key> <prompt>",
    "cmd_run_unknown_agent": "Error: Unknown agent '{agent_key}'",
    "cmd_run_available_agents": "Available agents:",
    "cmd_run_queued": "Queued prompt for {agent_name}: {prompt}...",
    "cmd_run_total_queued": "Total queued: {count}",
    "cmd_run_use_run": "Use '/run' to execute all queued prompts",
    "cmd_run_cleared": "Cleared {count} queued prompts",
    "cmd_run_index_required": "Error: Index required",
    "cmd_run_usage_remove": "Usage: /run remove <index>",
    "cmd_run_invalid_index": "Error: Invalid index '{index}'",

    # === Config ===
    "config_env_vars": "Environment Variables",
    "config_usage_set": "Usage: /config set <number> <value> to configure a variable",
    "config_usage_get": "Usage: /config get <number>",
    "config_var_not_found": "Error: Variable number {num} not found",
    "config_var_invalid": "Error: Variable number must be an integer",
    "config_var_set": "Set {var_name} to '{value}'",
    "config_no_env_vars": "No CAI_ or CTF_ environment variables found",

    # === Memory ===
    "memory_unknown_cmd": "Unknown subcommand. Available commands:",
    "memory_no_memories": "No memories stored yet",
    "memory_use_save": "Use '/memory save' to create a memory from current history",
    "memory_control_panel": "Memory Management Control Panel",
    "memory_stored": "Stored Memories",
    "memory_applied": "Applied Memories",

    # === Help ===
    "help_available_commands": "Available Commands",
    "help_usage": "Usage",
    "help_examples": "Examples",
    "help_options": "Options",

    # === Util: Tool Display ===
    "tool_call": "Tool Call:",
    "tool_name": "Name:",
    "tool_args": "Args:",
    "tool_output": "Output:",
    "current_agent": "Current Agent",
    "reasoning_header": "{model} Reasoning | {agent_name} | {model_name} | {timestamp}",

    # === Util: CTF ===
    "flag_found": "Flag found: {flag}",
    "flag_in_output": " in output ",
    "ctf_not_found": "CTF environment not found or provided",
    "ctf_name_required": "CTF name not provided, necessary to run CTF",
    "ctf_module_unavailable": "pentestperf module not available, cannot setup CTF",
    "ctf_setting_up": "Setting up CTF: ",
    "ctf_testing": "Testing CTF: ",
    "ctf_no_challenge": "No challenge provided or challenge not found. Attempting to use the first challenge.",
    "ctf_testing_challenge": "Testing challenge: ",

    # === Util: Streaming & Errors ===
    "error_streaming_cleanup": "Error during streaming cleanup: {error}",
    "error_thinking_context": "Error creating {model} thinking context: {error}",
    "error_thinking_start": "Error starting {model} thinking display: {error}",
    "error_thinking_update": "Error updating {model} thinking content: {error}",
    "error_thinking_finish": "Error finishing {model} thinking display: {error}",
}

KO = {
    # === CLI Core Messages ===
    "turn_limit_increased": "턴 제한이 증가되었습니다. CAI를 계속 사용할 수 있습니다.",
    "error_max_turns": "오류: 최대 턴 제한({max_turns})에 도달했습니다.",
    "config_increase_turns": "/config 명령어로 제한을 증가하세요: /config CAI_MAX_TURNS=<새 값>",
    "only_cli_commands": "제한이 증가될 때까지 CLI 명령어('/'로 시작)만 처리됩니다.",
    "error_switch_agent": "에이전트 전환 오류: {error}",
    "error_turn_limit": "오류: 턴 제한에 도달했습니다. CLI 명령어만 사용 가능합니다.",
    "increase_turns_hint": "/config 명령어로 CAI_MAX_TURNS 제한을 증가하세요.",
    "error_agent_run": "{agent_name} 실행 오류",
    "command_failed": "명령어 실패 또는 알 수 없는 명령어: {command}",
    "log_file": "로그 파일: {filename}",
    "error_general": "오류: {error}",
    "error_traceback": "트레이스백: {tb_info}",
    "error_litellm_patch": "LiteLLM 패치(fix_litellm_transcription_annotations) 적용 중 오류가 발생했습니다",
    "error_streaming": "스트리밍 중 오류 발생: {error}",

    # === Security Guardrails ===
    "guardrail_triggered": "보안 가드레일 작동",
    "guardrail_name": "가드레일: {name}",
    "guardrail_reason": "사유: {reason}",
    "guardrail_output_blocked": "보안상의 이유로 에이전트의 출력이 차단되었습니다.",
    "guardrail_continue": "다른 요청으로 대화를 계속할 수 있습니다.",
    "guardrail_input_triggered": "입력 보안 가드레일 작동",
    "guardrail_input_blocked": "보안상의 이유로 입력이 차단되었습니다.",
    "guardrail_history_warning": "대화 기록에 악성 콘텐츠가 포함되어 있을 수 있습니다.",
    "guardrail_options": "선택지:",
    "guardrail_option_clear": "1. /clear 를 입력하여 대화 기록을 초기화하세요",
    "guardrail_option_disable": "2. /config set 26 false 를 입력하여 가드레일을 임시 비활성화하세요",
    "guardrail_option_exit": "3. /exit 를 입력하여 CAI를 종료하세요",
    "guardrail_rephrase": "요청을 다시 작성하거나 다른 방법을 시도해주세요.",

    # === Session & Cost ===
    "session_cost": "CAI 세션 총 비용: ${cost}",
    "warning_pricing_local": "경고: 로컬 pricing.json 로딩 오류: {error}",
    "warning_pricing_fetch": "경고: 모델 가격 정보 조회 오류: {error}",
    "warning_template": "경고: 시스템 마스터 템플릿 렌더링 실패: {error}",

    # === Agent & Tools ===
    "no_agent_visualize": "시각화할 에이전트가 없습니다.",
    "tools_header": "도구",
    "handoff_info": "{tool_name}을 통한 {handoff_name}",
    "error_creating_stream": "스트리밍 컨텍스트 생성 오류: {error}",

    # === REPL Commands ===
    "cmd_run_parallel_only": "오류: /run 명령어는 병렬 모드에서만 사용 가능합니다",
    "cmd_run_enable_parallel": "먼저 적절한 환경 변수로 병렬 모드를 활성화하세요",
    "cmd_run_no_prompts": "대기 중인 프롬프트가 없습니다. '/run queue <에이전트> <프롬프트>'로 추가하세요.",
    "cmd_run_executing": "{count}개의 대기 중인 프롬프트를 실행합니다...",
    "cmd_run_processing": "병렬 실행을 위한 프롬프트가 설정되었습니다. 곧 처리가 시작됩니다.",
    "cmd_run_agent_prompt_required": "오류: 에이전트와 프롬프트가 필요합니다",
    "cmd_run_usage_queue": "사용법: /run queue <에이전트_키> <프롬프트>",
    "cmd_run_unknown_agent": "오류: 알 수 없는 에이전트 '{agent_key}'",
    "cmd_run_available_agents": "사용 가능한 에이전트:",
    "cmd_run_queued": "{agent_name}에 프롬프트 대기열 추가: {prompt}...",
    "cmd_run_total_queued": "총 대기열: {count}개",
    "cmd_run_use_run": "'/run'을 입력하여 모든 대기 중인 프롬프트를 실행하세요",
    "cmd_run_cleared": "{count}개의 대기 중인 프롬프트를 삭제했습니다",
    "cmd_run_index_required": "오류: 인덱스가 필요합니다",
    "cmd_run_usage_remove": "사용법: /run remove <인덱스>",
    "cmd_run_invalid_index": "오류: 잘못된 인덱스 '{index}'",

    # === Config ===
    "config_env_vars": "환경 변수",
    "config_usage_set": "사용법: /config set <번호> <값> 으로 변수를 설정합니다",
    "config_usage_get": "사용법: /config get <번호>",
    "config_var_not_found": "오류: 변수 번호 {num}을(를) 찾을 수 없습니다",
    "config_var_invalid": "오류: 변수 번호는 정수여야 합니다",
    "config_var_set": "{var_name}을(를) '{value}'(으)로 설정했습니다",
    "config_no_env_vars": "CAI_ 또는 CTF_ 환경 변수를 찾을 수 없습니다",

    # === Memory ===
    "memory_unknown_cmd": "알 수 없는 하위 명령어입니다. 사용 가능한 명령어:",
    "memory_no_memories": "저장된 메모리가 없습니다",
    "memory_use_save": "'/memory save'를 사용하여 현재 기록에서 메모리를 생성하세요",
    "memory_control_panel": "메모리 관리 제어판",
    "memory_stored": "저장된 메모리",
    "memory_applied": "적용된 메모리",

    # === Help ===
    "help_available_commands": "사용 가능한 명령어",
    "help_usage": "사용법",
    "help_examples": "예시",
    "help_options": "옵션",

    # === Util: Tool Display ===
    "tool_call": "도구 호출:",
    "tool_name": "이름:",
    "tool_args": "인자:",
    "tool_output": "출력:",
    "current_agent": "현재 에이전트",
    "reasoning_header": "{model} 추론 | {agent_name} | {model_name} | {timestamp}",

    # === Util: CTF ===
    "flag_found": "플래그 발견: {flag}",
    "flag_in_output": " 출력에서 발견 ",
    "ctf_not_found": "CTF 환경을 찾을 수 없거나 제공되지 않았습니다",
    "ctf_name_required": "CTF 이름이 제공되지 않았습니다. CTF 실행에 필요합니다",
    "ctf_module_unavailable": "pentestperf 모듈을 사용할 수 없습니다. CTF 설정 불가",
    "ctf_setting_up": "CTF 설정 중: ",
    "ctf_testing": "CTF 테스트 중: ",
    "ctf_no_challenge": "챌린지가 제공되지 않았거나 찾을 수 없습니다. 첫 번째 챌린지를 시도합니다.",
    "ctf_testing_challenge": "챌린지 테스트 중: ",

    # === Util: Streaming & Errors ===
    "error_streaming_cleanup": "스트리밍 정리 중 오류: {error}",
    "error_thinking_context": "{model} 추론 컨텍스트 생성 오류: {error}",
    "error_thinking_start": "{model} 추론 표시 시작 오류: {error}",
    "error_thinking_update": "{model} 추론 내용 업데이트 오류: {error}",
    "error_thinking_finish": "{model} 추론 표시 종료 오류: {error}",
}

MESSAGES = {
    "en": EN,
    "ko": KO,
}

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/src/cai"

echo "=== CAI 한글화 적용 스크립트 ==="
echo ""

# 1. site-packages 경로 자동 탐지
SP_BASE=$(python3 -c "import cai; import os; print(os.path.dirname(cai.__file__))" 2>/dev/null) || {
    echo "[오류] cai 패키지를 찾을 수 없습니다. 먼저 cai를 설치하세요."
    exit 1
}
echo "[1/4] site-packages 경로: $SP_BASE"

# 2. 수정된 파일 복사
echo "[2/4] 한글화 파일 복사 중..."

COPIED=0
FAILED=0

copy_file() {
    local rel="$1"
    local src="$SRC_DIR/$rel"
    local dst="$SP_BASE/$rel"
    if [ -f "$src" ]; then
        mkdir -p "$(dirname "$dst")"
        cp "$src" "$dst"
        COPIED=$((COPIED + 1))
    else
        echo "  경고: $rel 소스 파일 없음"
        FAILED=$((FAILED + 1))
    fi
}

# i18n
copy_file "i18n/__init__.py"
copy_file "i18n/messages.py"

# cli.py, util.py
copy_file "cli.py"
copy_file "util.py"

# repl/commands/
for f in "$SRC_DIR"/repl/commands/*.py; do
    rel="repl/commands/$(basename "$f")"
    copy_file "$rel"
done

# repl/ui/
copy_file "repl/ui/banner.py"
copy_file "repl/ui/toolbar.py"

# tui/
copy_file "tui/cai_terminal.py"
if [ -f "$SRC_DIR/tui/__init__.py" ]; then
    copy_file "tui/__init__.py"
fi
if [ -f "$SRC_DIR/tui/components/__init__.py" ]; then
    copy_file "tui/components/__init__.py"
fi
for f in sidebar.py banner_widget.py graph_canvas.py agent_creator_panel.py \
         agent_selector_panel.py session_manager_panel.py command_handler.py \
         info_status_bar.py; do
    copy_file "tui/components/$f"
done

echo "  복사 완료: ${COPIED}개 파일, 실패: ${FAILED}개"

# 3. __pycache__ 정리
echo "[3/4] __pycache__ 정리 중..."
find "$SP_BASE" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo "  정리 완료"

# 4. 적용 결과 검증
echo "[4/4] 적용 결과 검증..."

KO_KEYS=$(python3 -c "
from cai.i18n.messages import MESSAGES
ko = MESSAGES.get('ko', {})
en = MESSAGES.get('en', {})
print(f'{len(ko)}/{len(en)}')
" 2>/dev/null) || KO_KEYS="검증 실패"

echo "  한국어 번역 키: ${KO_KEYS} (KO/EN)"

# 한글 출력 테스트
echo ""
echo "=== 한글 출력 테스트 ==="
CAI_LANGUAGE=ko python3 -c "
from cai.i18n import t
test_keys = ['help_welcome', 'cmd_help_desc', 'cmd_exit_desc']
for key in test_keys:
    result = t(key)
    status = 'OK' if result != key else 'MISS'
    print(f'  [{status}] {key}: {result[:60]}')
" 2>/dev/null || echo "  [경고] 한글 출력 테스트 실패 - CAI_LANGUAGE=ko 설정을 확인하세요"

echo ""
echo "=== 적용 완료! ==="
echo "TUI 확인: cai --tui"
echo "REPL 확인: CAI_LANGUAGE=ko cai"

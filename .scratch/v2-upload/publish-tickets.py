#!/usr/bin/env python3
"""批量创建 ticket 到 GitHub，按依赖顺序，关联 blocker 引用"""
import os
import re
import subprocess
from pathlib import Path

ISSUES_DIR = Path(__file__).parent / "issues"

# (文件名, 标题, labels)
TICKETS = [
    ("01-upload-config-and-disk.md", "01 — 上传配置中心 + 物理盘适配", "ready-for-agent"),
    ("02-obs-multipart-service.md", "02 — OBS Multipart Upload 服务封装", "ready-for-agent"),
    ("04-upload-sse-events.md", "04 — 上传进度事件流（SSE 端点）", "ready-for-agent"),
    ("03-multipart-upload-api.md", "03 — 分片上传后端 API（5 端点）+ DB 表", "ready-for-agent"),
    ("05-frontend-multipart-client.md", "05 — 前端分片上传器（带断点续传）", "ready-for-agent"),
    ("06-uploadzone-multipart-integration.md", "06 — UploadZone 接入分片路径", "ready-for-agent"),
    ("07-vs-upload-50mb-jpg.md", "07 — [VS] 上传 50MB JPG 直传（端到端）", "ready-for-agent"),
    ("08-vs-upload-200mb-arw.md", "08 — [VS] 上传 200MB ARW 分片（端到端）", "ready-for-agent"),
    ("09-vs-resumable-upload-1gb.md", "09 — [VS] 上传 1GB MP4 + 断点续传（端到端）", "ready-for-agent"),
    ("10-upload-page-skeleton.md", "10 — 独立上传页面骨架（/upload 路由）", "ready-for-agent"),
    ("11-upload-page-state-machine-ui.md", "11 — 上传页面 5 阶段状态机 UI", "ready-for-agent"),
    ("12-upload-page-controls.md", "12 — 上传页面 暂停/继续/重试/移除 操作", "ready-for-agent"),
    ("13-ai-import-regression-and-docs.md", "13 — AI 导入脚本回归 + 文档更新", "ready-for-agent"),
    ("14-e2e-stress-and-verify.md", "14 — 端到端压测 + hermes verify 全绿", "ready-for-agent"),
]

# 创建顺序（blockers 先）
# 01, 02 并行（无 blocker）
# 04 与 03 并行，03 依赖 01+02
# 05 依赖 03
# 06 依赖 05
# 07 依赖 03,05,06
# 08 依赖 07
# 09 依赖 08
# 10 依赖 04,06
# 11 依赖 10
# 12 依赖 11
# 13 依赖 03
# 14 依赖 07,08,09,11,12,13


def parse_blocked_by(filename: str) -> list[str]:
    """从 ticket md 文件解析 Blocked by 字段"""
    content = (ISSUES_DIR / filename).read_text()
    m = re.search(r"\*\*Blocked by:\*\*\s*(.+?)(?:\n|$)", content)
    if not m:
        return []
    text = m.group(1).strip()
    if text.startswith("None"):
        return []
    # 提取 #NN 格式的 ticket 编号
    nums = re.findall(r"#(\d+)", text)
    return nums


def main():
    # 第一遍：创建所有 issue，记录 ticket 编号 -> issue 编号映射
    issue_map: dict[str, int] = {}  # ticket_num -> issue_num

    for filename, title, label in TICKETS:
        ticket_num = filename.split("-")[0]
        body = (ISSUES_DIR / filename).read_text()

        # 临时去掉 Blocked by 行（先创建，后补）
        body_for_create = re.sub(
            r"\*\*Blocked by:\*\*\s*.+?(?:\n|$)",
            "**Blocked by:** _see comments_",
            body,
        )

        cmd = [
            "gh", "issue", "create",
            "--title", title,
            "--label", label,
            "--body", body_for_create,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ {title}: {result.stderr.strip()}")
            continue

        # 解析 issue 编号
        m = re.search(r"issues/(\d+)", result.stdout)
        if m:
            issue_num = int(m.group(1))
            issue_map[ticket_num] = issue_num
            print(f"✅ #{issue_num}: {title}")
        else:
            print(f"⚠️ 创建成功但未解析到编号: {title}\n{result.stdout}")

    print("\n=== 创建完成 ===")
    print("Ticket -> Issue 映射:")
    for k, v in sorted(issue_map.items()):
        print(f"  #{k} -> #{v}")

    # 第二遍：补充 Blocked by 关联（用 comment）
    for filename, title, label in TICKETS:
        ticket_num = filename.split("-")[0]
        if ticket_num not in issue_map:
            continue
        blocked = parse_blocked_by(filename)
        if not blocked:
            continue
        # 映射到 issue 编号
        blocker_issues = [f"#{issue_map[b]}" for b in blocked if b in issue_map]
        if not blocker_issues:
            continue

        issue_num = issue_map[ticket_num]
        cmd = [
            "gh", "issue", "edit", str(issue_num),
            "--body", "",  # 不修改 body
        ]
        # 用 comment 写依赖关系
        comment = f"**Blocked by:** {', '.join(blocker_issues)}"
        subprocess.run(
            ["gh", "issue", "comment", str(issue_num), "--body", comment],
            capture_output=True, text=True,
        )
        print(f"  #{issue_num} blocked by {blocker_issues}")

    print("\n全部完成")


if __name__ == "__main__":
    main()
"""Count compactions in one local Codex rollout. Standard library only."""

import argparse
import json
import os
from pathlib import Path
import sys
from uuid import UUID


class CountError(Exception):
    pass


def validate_thread_id(value):
    if not value:
        raise CountError("无法获取当前对话 ID，可通过 --thread-id 指定。")
    try:
        return str(UUID(value))
    except (ValueError, AttributeError):
        raise CountError("对话 ID 不是有效的 UUID。") from None


def find_rollout(codex_home, thread_id):
    candidates = []
    for name in ("sessions", "archived_sessions"):
        folder = codex_home / name
        if folder.is_dir():
            candidates.extend(folder.rglob(f"rollout-*-{thread_id}.jsonl"))
    if not candidates:
        raise CountError("未找到该对话的本地日志。")
    if len(candidates) != 1:
        raise CountError("找到多个同 ID 日志，无法可靠确定统计来源。")
    return candidates[0]


def count_compactions(path, thread_id):
    count = 0
    metadata_seen = False
    seen_ids = set()
    with path.open("rb") as stream:
        # Fix the snapshot boundary: querying an active thread must terminate.
        remaining = os.fstat(stream.fileno()).st_size
        while remaining:
            raw = stream.readline(remaining)
            if not raw:
                raise CountError("读取期间日志被截断，请重试。")
            remaining -= len(raw)
            if not raw.strip():
                continue
            try:
                record = json.loads(raw)
            except (ValueError, UnicodeError):
                if not remaining and not raw.endswith(b"\n"):
                    raise CountError("日志末尾尚未写完，请稍后重试。") from None
                raise CountError("日志包含无法解析的记录。") from None
            if not isinstance(record, dict) or not isinstance(record.get("type"), str):
                raise CountError("日志格式无法识别。")
            kind = record["type"]
            if kind not in ("session_meta", "compacted"):
                continue
            payload = record.get("payload")
            if not isinstance(payload, dict):
                raise CountError("会话或压缩记录的格式无法识别。")
            if kind == "session_meta":
                if metadata_seen:
                    raise CountError("存在多段会话元数据，可能包含继承历史。")
                if payload.get("id") != thread_id:
                    raise CountError("日志身份与指定对话不一致。")
                if any("parent" in key or "fork" in key for key in payload) or (
                    "subagent_history_start_ordinal" in payload
                ):
                    raise CountError("该对话包含分支或子任务信息，暂不统计继承历史。")
                metadata_seen = True
                continue
            if not metadata_seen:
                raise CountError("压缩记录之前缺少会话身份信息。")
            if "message" not in payload and "replacement_history" not in payload:
                raise CountError("压缩记录格式未知。")
            identifiers = {
                (key, payload[key])
                for key in ("compaction_response_id", "window_id")
                if isinstance(payload.get(key), str) and payload[key]
            }
            if not identifiers or not seen_ids.intersection(identifiers):
                count += 1
            seen_ids.update(identifiers)
    if not metadata_seen:
        raise CountError("日志缺少会话身份信息。")
    return count


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="查询 Codex 对话压缩次数（只读本地日志）")
    parser.add_argument("--thread-id", default=os.environ.get("CODEX_THREAD_ID"))
    parser.add_argument(
        "--codex-home", type=Path,
        default=Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex"),
    )
    args = parser.parse_args()
    try:
        thread_id = validate_thread_id(args.thread_id)
        path = find_rollout(args.codex_home.expanduser(), thread_id)
        count = count_compactions(path, thread_id)
    except CountError as error:
        print(f"无法可靠统计：{error}")
        return 1
    except OSError:
        print("无法可靠统计：日志目录或文件无法读取，请检查路径和读取权限。")
        return 1
    print(f"该对话压缩了 {count} 次（按本地保留记录）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""从 rosbag2 的 .db3 文件重建 metadata.yaml。

什么时候需要它：`ros2 bag record` 靠 Ctrl+C 收尾才会写 metadata.yaml。
如果你用了 `kill -9`、Windows 上强杀、或者机器直接断电，就会留下一个
**有数据但没有索引**的包——`ros2 bag info` 和 `ros2 bag play` 都会报
"Could not find metadata in bag directory"。

数据其实都在 .db3 里，只是缺一份说明书。这个脚本把说明书补回来。

用法：
    python3 scripts/rebuild_bag_metadata.py <bag目录>
    python3 scripts/rebuild_bag_metadata.py <bag目录> --dry-run   # 只看结果不写文件
    python3 scripts/rebuild_bag_metadata.py <bag目录> --force     # 覆盖已有的 metadata.yaml
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

# rosbag2 的元数据版本：Humble 用 5，Iron/Jazzy 用 6/7/8。
# 只写版本号不影响读取，Humble 上的 ros2 bag info 认这个格式。
METADATA_VERSION = 5


def collect(db: Path) -> dict:
    """从 .db3 里读出话题、消息数、起止时间。"""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        cur = con.cursor()
        topics = cur.execute(
            "SELECT id, name, type, serialization_format FROM topics ORDER BY id"
        ).fetchall()

        per_topic = []
        total = 0
        global_start = None
        global_end = None
        for tid, name, typ, ser in topics:
            row = cur.execute(
                "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM messages WHERE topic_id = ?",
                (tid,),
            ).fetchone()
            count, lo, hi = row[0], row[1], row[2]
            total += count
            if lo is not None:
                global_start = lo if global_start is None else min(global_start, lo)
                global_end = hi if global_end is None else max(global_end, hi)
            per_topic.append(
                {
                    "name": name,
                    "type": typ,
                    "serialization_format": ser or "cdr",
                    "count": count,
                    "start": lo,
                    "end": hi,
                }
            )
    finally:
        con.close()

    if global_start is None:
        global_start = 0
        global_end = 0

    return {
        "db_name": db.name,
        "topics": per_topic,
        "total": total,
        "start": global_start,
        "duration": max(global_end - global_start, 0),
    }


def render(info: dict) -> str:
    """生成 metadata.yaml 的内容。"""
    lines = [
        "rosbag2_bagfile_information:",
        f"  version: {METADATA_VERSION}",
        "  storage_identifier: sqlite3",
        "  duration:",
        f"    nanoseconds: {info['duration']}",
        "  starting_time:",
        f"    nanoseconds_since_epoch: {info['start']}",
        f"  message_count: {info['total']}",
        "  topics_with_message_count:",
    ]
    for t in info["topics"]:
        lines += [
            "    - topic_metadata:",
            f"        name: {t['name']}",
            f"        type: {t['type']}",
            f"        serialization_format: {t['serialization_format']}",
            '        offered_qos_profiles: ""',
            f"      message_count: {t['count']}",
        ]
    lines += [
        '  compression_format: ""',
        '  compression_mode: ""',
        "  relative_file_paths:",
        f"    - {info['db_name']}",
        "  files:",
        f"    - path: {info['db_name']}",
        "      starting_time:",
        f"        nanoseconds_since_epoch: {info['start']}",
        "      duration:",
        f"        nanoseconds: {info['duration']}",
        f"      message_count: {info['total']}",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="从 .db3 重建 rosbag2 的 metadata.yaml")
    ap.add_argument("bag_dir", help="bag 目录（里面有 .db3）")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不写文件")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的 metadata.yaml")
    args = ap.parse_args()

    bag = Path(args.bag_dir)
    if not bag.is_dir():
        print(f"不是目录：{bag}", file=sys.stderr)
        return 2

    dbs = sorted(bag.glob("*.db3"))
    if not dbs:
        print(f"{bag} 里没有 .db3 文件", file=sys.stderr)
        return 2
    if len(dbs) > 1:
        print(f"警告：发现 {len(dbs)} 个 .db3，只用第一个 {dbs[0].name}", file=sys.stderr)

    target = bag / "metadata.yaml"
    if target.exists() and not args.force:
        print(f"{target} 已存在；要覆盖请加 --force")
        return 1

    info = collect(dbs[0])
    text = render(info)

    print(f"数据库：{info['db_name']}（{dbs[0].stat().st_size / 1024:.1f} KB）")
    print(f"消息总数：{info['total']}")
    print(f"时间跨度：{info['duration'] / 1e9:.2f} 秒")
    print("话题：")
    for t in info["topics"]:
        print(f"  {t['name']:28s} {t['type']:40s} {t['count']} 条")

    if args.dry_run:
        print("\n--- 生成的 metadata.yaml（dry-run，未写入）---")
        print(text)
        return 0

    target.write_text(text, encoding="utf-8", newline="\n")
    print(f"\n已写入 {target}")
    print("现在可以：ros2 bag info " + str(bag))
    return 0


if __name__ == "__main__":
    sys.exit(main())

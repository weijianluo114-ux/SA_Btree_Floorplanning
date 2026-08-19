#!/usr/bin/env python3
"""
play_snapshots.py —— 把一次运行生成的快照图合成可播放的动画 GIF。

服务器（无图形界面）下无法弹出交互窗口，因此“播放”采用最朴素的实现：
把 figures/snapshots/ 下同一 run 的 *_floorplan.png（及 *_btree.png）
按迭代号排序，合成 runN_snapshots_animation.gif，用支持 GIF 的工具即可播放。

用法：
    python play_snapshots.py --snap_dir <figures/snapshots> [--duration 500] [--out <dir>]
也可作为模块被 test_scripts.py 调用：play(Namespace(...))
"""
import argparse
import re
from pathlib import Path


def _iter_label(name: str) -> int:
    m = re.search(r"_iter(\d+)", name)
    return int(m.group(1)) if m else 0


def collect_frames(snap_dir: Path, suffix: str):
    """返回 {run_prefix: [Path, ...]}，每个 run 的帧按迭代号升序。"""
    frames = {}
    for p in sorted(snap_dir.glob(f"*{suffix}.png")):
        m = re.search(r"(run\d+).*?_iter(\d+)", p.stem)
        if not m:
            continue
        run = m.group(1)
        frames.setdefault(run, []).append(p)
    for run in frames:
        frames[run].sort(key=lambda p: _iter_label(p.name))
    return frames


def make_gif(frame_paths, out_path, duration_ms=500, loop=0) -> bool:
    try:
        from PIL import Image
    except ImportError:
        raise SystemExit("需要 Pillow 才能生成 GIF: pip install pillow")
    imgs = [Image.open(p).convert("RGB") for p in frame_paths]
    if not imgs:
        return False
    imgs[0].save(out_path, save_all=True, append_images=imgs[1:],
                 duration=duration_ms, loop=loop)
    return True


def play(args):
    """args.snap_dir: 快照图目录；args.out: GIF 输出目录（None=与 snap_dir 相同）；
    args.duration: 每帧毫秒数。"""
    snap_dir = Path(args.snap_dir)
    if not snap_dir.is_dir():
        print(f"[播放] 快照目录不存在: {snap_dir}")
        return
    out_dir = Path(args.out) if getattr(args, "out", None) else snap_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    n_gifs = 0
    for suffix in ("_floorplan", "_btree"):
        for run, frames in collect_frames(snap_dir, suffix).items():
            out_path = out_dir / f"{run}{suffix}_animation.gif"
            if make_gif(frames, out_path, getattr(args, "duration", 500)):
                print(f"[播放] {run} {suffix}: {len(frames)} 帧 -> {out_path}")
                n_gifs += 1
    if n_gifs == 0:
        print("[播放] 未找到快照帧（请先开启 snapshot 并运行生成快照图）")


def main(argv=None):
    parser = argparse.ArgumentParser(description="把快照图合成可播放的动画 GIF")
    parser.add_argument("--snap_dir", type=str, required=True,
                        help="快照图所在目录（figures/snapshots）")
    parser.add_argument("--out", type=str, default=None,
                        help="GIF 输出目录（默认与 snap_dir 相同）")
    parser.add_argument("--duration", type=int, default=500,
                        help="每帧停留毫秒数（默认 500）")
    args = parser.parse_args(argv)
    play(args)


if __name__ == "__main__":
    main()
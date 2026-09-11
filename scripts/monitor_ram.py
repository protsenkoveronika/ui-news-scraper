"""Poll RAM usage of a running process (by PID or name match) and report the peak.

Usage:
    python scripts/monitor_ram.py                # watches any process with "streamlit" in its command line
    python scripts/monitor_ram.py --pid 21440     # watches one specific PID
    python scripts/monitor_ram.py --name python   # match a different substring
    python scripts/monitor_ram.py --interval 0.5  # poll twice a second

Requires psutil: pip install psutil

Prints a live-updating line and, on Ctrl+C, a summary with the peak RSS
observed (summed across all matching processes, since Streamlit can spawn a
small helper process alongside the main one).
"""
import argparse
import sys
import time

import psutil


def find_matching_pids(name_substring, match_cmdline=False):
    """Match against the process's own executable name by default (e.g.
    "streamlit.exe"). Matching full command lines instead (match_cmdline=True)
    is broader but can false-positive on unrelated shell/wrapper processes
    that merely mention the substring in their invocation.

    The matched process's entry-point stub (e.g. streamlit.exe on Windows)
    typically spawns the real worker as a child process, so descendants of
    each match are included too."""
    matches = set()
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            haystack = proc.info["name"] or ""
            if match_cmdline:
                haystack += " " + " ".join(proc.info["cmdline"] or [])
            if name_substring.lower() in haystack.lower():
                matches.add(proc.info["pid"])
                for child in proc.children(recursive=True):
                    matches.add(child.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return list(matches)


def total_rss_mb(pids):
    total = 0.0
    alive = []
    for pid in pids:
        try:
            total += psutil.Process(pid).memory_info().rss / (1024 * 1024)
            alive.append(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return total, alive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, help="Watch this exact PID only.")
    parser.add_argument(
        "--name", default="streamlit",
        help="Substring to match against process name/cmdline (default: 'streamlit').",
    )
    parser.add_argument(
        "--interval", type=float, default=1.0,
        help="Seconds between samples (default: 1.0).",
    )
    parser.add_argument(
        "--cmdline", action="store_true",
        help="Also search full command lines, not just the executable name "
             "(broader, but can match unrelated wrapper processes).",
    )
    args = parser.parse_args()

    pids = [args.pid] if args.pid else find_matching_pids(args.name, args.cmdline)
    if not pids:
        print(f"No running process matched {'PID ' + str(args.pid) if args.pid else '\"' + args.name + '\"'}.")
        sys.exit(1)

    print(f"Watching PID(s): {pids} (Ctrl+C to stop)")
    peak_mb = 0.0
    samples = 0
    total_mb_sum = 0.0

    try:
        while True:
            current_mb, pids = total_rss_mb(pids)
            if not pids:
                print("\nAll watched processes have exited.")
                break
            peak_mb = max(peak_mb, current_mb)
            samples += 1
            total_mb_sum += current_mb
            avg_mb = total_mb_sum / samples
            print(
                f"\rcurrent: {current_mb:7.1f} MB   peak: {peak_mb:7.1f} MB   avg: {avg_mb:7.1f} MB",
                end="", flush=True,
            )
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass

    print(f"\n\nSamples: {samples}")
    print(f"Peak RSS:    {peak_mb:.1f} MB")
    if samples:
        print(f"Average RSS: {total_mb_sum / samples:.1f} MB")


if __name__ == "__main__":
    main()

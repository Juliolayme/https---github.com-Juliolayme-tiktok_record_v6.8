#!/usr/bin/env python3
import os
import sys
import subprocess

def main():
    idx = int(os.environ.get('INSTANCE_INDEX', '0'))
    total = int(os.environ.get('TOTAL_INSTANCES', '1'))

    path = 'src/username.txt'
    if not os.path.exists(path):
        print('username.txt not found at', path)
        sys.exit(0)

    with open(path, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]

    n = len(lines)
    if n == 0:
        print('No usernames found')
        sys.exit(0)

    # compute chunk size and slice for this instance
    chunk = (n + total - 1) // total
    start = idx * chunk
    end = min(start + chunk, n)
    subset = lines[start:end]

    if not subset:
        print(f'Instance {idx} has no usernames (start {start} >= {n})')
        sys.exit(0)

    print(f'Instance {idx}: running {len(subset)} users (lines {start}-{end-1})')

    # per-instance output directory
    output_dir = f'outputs/instance-{idx}'
    os.makedirs(output_dir, exist_ok=True)

    # run one process per user in parallel, then wait for all to finish
    procs = []
    for user in subset:
        safe_user = user.replace(' ', '_')
        user_output = os.path.join(output_dir, safe_user)
        os.makedirs(user_output, exist_ok=True)
        cmd = ['python3', 'src/main.py', '-mode', 'automatic', '-user', user, '-output', user_output, '-no-update-check']
        print('Starting:', ' '.join(cmd))
        p = subprocess.Popen(cmd)
        procs.append((user, p))

    # wait for all user processes
    exit_errors = 0
    for user, p in procs:
        ret = p.wait()
        if ret != 0:
            print(f'User {user} exited with code {ret}')
            exit_errors += 1
    if exit_errors:
        sys.exit(exit_errors)

if __name__ == '__main__':
    main()

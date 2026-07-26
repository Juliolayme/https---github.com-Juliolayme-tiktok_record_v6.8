#!/usr/bin/env python3
"""Verify that src/cookies.json actually authenticates against TikTok.

Prints only cookie NAMES and masked identifiers - never a cookie value -
so it is safe to run in a public repo's Actions log.

Exit code 0 = logged in, 1 = not logged in / cookies broken.
"""
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, 'src'))

# cookies that actually carry the login session
REQUIRED = ['sessionid', 'sessionid_ss', 'sid_guard', 'sid_tt', 'uid_tt']
# nice to have: keeps requests on the right datacenter / passes bot checks
OPTIONAL = ['ttwid', 'tt-target-idc', 'odin_tt', 'msToken', 'tt_csrf_token']


def mask(value: str) -> str:
    if not value:
        return '(empty)'
    return f'{value[:6]}...{value[-4:]} (len {len(value)})'


def check_file():
    path = os.path.join(REPO_ROOT, 'src', 'cookies.json')
    if not os.path.exists(path):
        print('FAIL: src/cookies.json does not exist')
        return None

    with open(path, 'r', encoding='utf-8') as f:
        try:
            cookies = json.load(f)
        except json.JSONDecodeError as e:
            print(f'FAIL: src/cookies.json is not valid JSON - {e}')
            return None

    if not isinstance(cookies, dict):
        print('FAIL: cookies.json must be a flat object {"name": "value"}, '
              f'got {type(cookies).__name__}. Re-export or convert it.')
        return None

    if not cookies:
        print('FAIL: cookies.json is empty ({}). Is the TIKTOK_COOKIES secret set?')
        return None

    print(f'cookies.json loaded: {len(cookies)} cookies')

    missing = [k for k in REQUIRED if not cookies.get(k)]
    for k in REQUIRED:
        print(f'  [{"x" if cookies.get(k) else " "}] {k}')
    for k in OPTIONAL:
        print(f'  [{"x" if cookies.get(k) else " "}] {k} (optional)')

    if missing:
        print(f'FAIL: missing required cookies: {", ".join(missing)}')
        return None

    return cookies


def main():
    print('=== 1. cookies.json ===')
    cookies = check_file()
    if cookies is None:
        return 1

    from core.tiktok_api import TikTokAPI

    api = TikTokAPI(proxy=None, cookies=cookies)

    print('\n=== 2. runner region ===')
    try:
        blacklisted = api.is_country_blacklisted()
        print(f'country blacklisted (login required): {blacklisted}')
    except Exception as e:
        print(f'could not determine region: {type(e).__name__}: {e}')

    print('\n=== 3. login status ===')
    try:
        authenticated = api._is_authenticated()
    except Exception as e:
        print(f'FAIL: request to /foryou failed - {type(e).__name__}: {e}')
        return 1

    if not authenticated:
        print('FAIL: NOT logged in - TikTok served the login page.')
        print('The cookies are expired or incomplete. Re-export them from a '
              'logged-in browser and update the TIKTOK_COOKIES secret.')
        return 1

    print('OK: logged in - TikTok did not serve the login page.')

    print('\n=== 4. account identity ===')
    try:
        sec_uid = api.get_sec_uid()
        if sec_uid:
            print(f'secUid resolved: {mask(sec_uid)}')
        else:
            print('WARNING: logged in but secUid not found in /foryou. '
                  'Usually still fine for recording.')
    except Exception as e:
        print(f'WARNING: could not read secUid - {type(e).__name__}: {e}')

    print('\n=== 5. live lookup (end-to-end) ===')
    target = os.environ.get('CHECK_USERNAME', '').strip()
    if not target:
        path = os.path.join(REPO_ROOT, 'src', 'username.txt')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                names = [l.strip() for l in f if l.strip()]
            target = names[0] if names else ''

    if not target:
        print('skipped: no username to test')
    else:
        try:
            room_id = api.get_room_id_from_user(target)
            if room_id:
                print(f'@{target}: room_id found ({room_id}) -> live right now')
            else:
                print(f'@{target}: no room_id -> user is offline '
                      '(this is a normal result, the lookup itself worked)')
        except Exception as e:
            print(f'WARNING: lookup for @{target} failed - {type(e).__name__}: {e}')
            print('If this says IPBlockedByWAF, the GitHub runner IP is blocked, '
                  'not your cookies.')

    print('\nRESULT: cookies are valid and authenticated.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

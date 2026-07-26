#!/usr/bin/env python3
"""Verify that src/cookies.json actually authenticates against TikTok.

Prints only cookie NAMES and masked identifiers - never a cookie value,
never the account's username - so it is safe to run in a public repo's
Actions log.

Env:
  CHECK_SKIP_LOOKUP=1   skip the live-lookup section (used before recording)
  CHECK_USERNAME=<name> username for the live-lookup section

Exit code 0 = logged in, 1 = not logged in / cookies broken.
"""
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, 'src'))

# cookies that actually carry the login session
REQUIRED = ['sessionid', 'sessionid_ss', 'sid_guard', 'sid_tt', 'uid_tt']
# nice to have: keeps requests on the right datacenter / passes bot checks
OPTIONAL = ['ttwid', 'tt-target-idc', 'odin_tt', 'msToken', 'tt_csrf_token']

ACCOUNT_INFO_URL = 'https://www.tiktok.com/passport/web/account/info/?aid=1459'
REHYDRATION_RE = re.compile(
    r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>',
    re.DOTALL,
)


def mask(value) -> str:
    """Enough to tell two identities apart, not enough to identify the account."""
    if not value:
        return '(empty)'
    value = str(value)
    if len(value) <= 10:
        return f'{value[:2]}...{value[-2:]}'
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


def check_passport(http_client):
    """Ask TikTok's own account endpoint who we are.

    Returns True (logged in), False (not logged in), or None (inconclusive).
    This is the authoritative check: it answers 'error' for anonymous
    sessions instead of quietly serving public content.
    """
    try:
        response = http_client.get(ACCOUNT_INFO_URL)
        data = response.json()
    except Exception as e:
        print(f'  passport endpoint unreachable - {type(e).__name__}: {e}')
        return None

    payload = data.get('data', {})
    if data.get('message') == 'success' and payload.get('user_id_str'):
        print(f'  passport: logged in as uid {mask(payload["user_id_str"])}')
        return True

    print(f'  passport: NOT logged in - message={data.get("message")!r} '
          f'error_code={payload.get("error_code")!r} '
          f'description={payload.get("description")!r}')
    return False


def check_app_context(http_client):
    """Second opinion: does the /foryou page render with a logged-in user?

    Note the upstream `TikTokAPI._is_authenticated()` (which greps for
    'login-title') is NOT usable here - it returns True even for a junk
    sessionid, because TikTok serves the feed to anonymous visitors too.
    """
    try:
        html = http_client.get('https://www.tiktok.com/foryou').text
    except Exception as e:
        print(f'  /foryou unreachable - {type(e).__name__}: {e}')
        return None, None

    match = REHYDRATION_RE.search(html)
    if not match:
        print('  /foryou: page data not found (layout changed or WAF page)')
        return None, None

    try:
        context = json.loads(match.group(1)).get(
            '__DEFAULT_SCOPE__', {}).get('webapp.app-context', {})
    except json.JSONDecodeError:
        print('  /foryou: page data not parseable')
        return None, None

    region = context.get('region')
    user = context.get('user') or {}
    if user.get('uid'):
        print(f'  /foryou: logged in as uid {mask(user["uid"])} '
              f'(user @{mask(user.get("uniqueId"))}), region {region}')
        return True, region

    print(f'  /foryou: anonymous session (no user in page data), region {region}')
    return False, region


def main():
    print('=== 1. cookies.json ===')
    cookies = check_file()
    if cookies is None:
        return 1

    from core.tiktok_api import TikTokAPI

    api = TikTokAPI(proxy=None, cookies=cookies)

    print('\n=== 2. login status ===')
    passport = check_passport(api.http_client)
    context, region = check_app_context(api.http_client)

    # Trust passport when it answered; fall back to the page data if it didn't.
    authenticated = passport if passport is not None else context

    if authenticated is None:
        print('INCONCLUSIVE: could not reach TikTok to verify the session.')
        return 1

    if not authenticated:
        print('FAIL: NOT logged in - TikTok treats this session as anonymous.')
        print('The cookies are expired or revoked. Re-export them from a '
              'logged-in browser and update the TIKTOK_COOKIES secret.')
        return 1

    if context is False:
        print('WARNING: passport says logged in but /foryou rendered anonymous. '
              'Session is probably degraded; consider re-exporting cookies.')

    print('OK: logged in.')

    print('\n=== 3. runner region ===')
    try:
        blacklisted = api.is_country_blacklisted()
        print(f'country blacklisted (login required): {blacklisted}')
    except Exception as e:
        print(f'could not determine region: {type(e).__name__}: {e}')

    print('\n=== 4. live lookup (end-to-end) ===')
    if os.environ.get('CHECK_SKIP_LOOKUP'):
        # pre-record runs skip this: the recorder is about to do the same
        # lookup anyway, and a 9-way matrix hitting TikTok 9 extra times
        # only raises the odds of tripping the WAF.
        print('skipped (CHECK_SKIP_LOOKUP set)')
        print('\nRESULT: cookies are valid and authenticated.')
        return 0

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

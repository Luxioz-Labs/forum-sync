"""Every run: any forum post whose newest message is from a tester (not Tanay, not a bot or webhook)
gets the Waiting tag, so it shows up as needing a reply."""
import json, os, urllib.request

API = 'https://discord.com/api/v10'
GUILD, FORUM = '1536391412222787734', '1536391626132291594'
WAITING = '1536731208740896778'
STAFF = {'707261197606584440'}          # arrowtan (Tanay)

def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization': 'Bot ' + os.environ['TOKEN'], 'Content-Type': 'application/json',
                 'User-Agent': 'LuxiozLabs forum-sync (github, 1.0)'})
    with urllib.request.urlopen(req) as r:
        data = r.read()
        return json.loads(data) if data else None

EMOJI = {'1536731186779525130': '✅', '1536731208740896778': '⏳', '1537034262383951913': '🔄'}

def named(name, tags):
    """Post name with the current tag's emoji at the end, any old status emoji removed."""
    base = name
    while True:
        stripped = base.rstrip()
        for e in EMOJI.values():
            if stripped.endswith(e):
                stripped = stripped[:-len(e)]
        stripped = stripped.rstrip()
        if stripped == base.rstrip():
            break
        base = stripped
    mark = next((EMOJI[t] for t in tags if t in EMOJI), '')
    return (base.rstrip() + (' ' + mark if mark else ''))[:100]

def from_tester(m):
    a = m['author']
    return not (a.get('bot') or m.get('webhook_id') or a['id'] in STAFF)

threads = [t for t in call('GET', f'/guilds/{GUILD}/threads/active')['threads'] if t.get('parent_id') == FORUM]
changed = 0
for t in threads:
    tags = t.get('applied_tags') or []
    if WAITING not in tags:
        msgs = call('GET', f"/channels/{t['id']}/messages?limit=1")
        if msgs and from_tester(msgs[0]):
            tags = [WAITING]
            call('PATCH', f"/channels/{t['id']}", {'applied_tags': tags})
            print(f"{t['name']}: Waiting (last message from {msgs[0]['author']['username']})")
            changed += 1
    want = named(t['name'], tags)
    if want != t['name']:
        call('PATCH', f"/channels/{t['id']}", {'name': want})
        print(f"renamed {t['name']!r} -> {want!r}")
print(f'checked {len(threads)} posts, changed {changed}')

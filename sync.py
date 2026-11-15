"""Every run: any forum post whose newest message is from a tester (not Tanay, not a bot or webhook)
gets the Waiting tag, so it shows up as needing a reply."""
import json, os, re, urllib.request

API = 'https://discord.com/api/v10'
GUILD, FORUM = '1536391412222787734', '1536391626132291594'
WAITING = '1536731208740896778'
ONGOING = '1537034262383951913'
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

STATUS = {'1536731186779525130': 'Done', '1536731208740896778': 'Waiting on dev', '1537034262383951913': 'With testers'}
REPOS = json.loads(os.environ.get('THREAD_REPOS') or '{}')   # thread id -> repo name

def gh(method, path, body=None):
    req = urllib.request.Request('https://api.github.com' + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json',
                 'User-Agent': 'LuxiozLabs forum-sync'})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or b'null')

def set_repo_status(thread_id, tags):
    repo = REPOS.get(thread_id)
    tag = next((t for t in tags if t in STATUS), None)
    if not repo or not os.environ.get('GH_TOKEN'):
        return
    want = (f"{EMOJI[tag]} {STATUS[tag]} · " if tag else '') + f"Test builds, guide and bug reports for {repo}"
    have = gh('GET', f'/repos/Luxioz-Labs/{repo}').get('description')
    if have != want:
        gh('PATCH', f'/repos/Luxioz-Labs/{repo}', {'description': want})
        print(f'{repo}: description -> {want}')

def asks_question(text):
    """True when a message asks something: a '?' outside code and links."""
    t = re.sub(r'```.*?```', ' ', text or '', flags=re.S)
    t = re.sub(r'`[^`]*`', ' ', t)
    t = re.sub(r'https?://\S+', ' ', t)
    return '?' in t

def from_tester(m):
    a = m['author']
    return not (a.get('bot') or m.get('webhook_id') or a['id'] in STAFF)

threads = [t for t in call('GET', f'/guilds/{GUILD}/threads/active')['threads'] if t.get('parent_id') == FORUM]
changed = 0
for t in threads:
    tags = t.get('applied_tags') or []
    msgs = call('GET', f"/channels/{t['id']}/messages?limit=1")
    last = msgs[0] if msgs else None
    if last and from_tester(last) and WAITING not in tags:
        tags = [WAITING]
        call('PATCH', f"/channels/{t['id']}", {'applied_tags': tags})
        print(f"{t['name']}: Waiting (last message from {last['author']['username']})")
        changed += 1
    elif last and last['author']['id'] in STAFF and asks_question(last['content']) and WAITING in tags:
        tags = [ONGOING]
        call('PATCH', f"/channels/{t['id']}", {'applied_tags': tags})
        print(f"{t['name']}: On going (Tanay asked a question)")
        changed += 1
    want = named(t['name'], tags)
    if want != t['name']:
        call('PATCH', f"/channels/{t['id']}", {'name': want})
        print(f"renamed {t['name']!r} -> {want!r}")
    set_repo_status(t['id'], tags)
print(f'checked {len(threads)} posts, changed {changed}')

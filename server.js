#!/usr/bin/env node
// 용접사 자격 인증서 관리 — 사내 서버 (외부 라이브러리 없음, Node.js 18+)
//
//   node server.js                 (처음 실행하면 마스터 계정을 만듭니다)
//   node server.js --port 8080     (포트 변경)
//
// - 같은 폴더의 welder-cert.html 을 웹으로 제공하고, 데이터는 ./data 폴더에 JSON 파일로 저장합니다.
// - 마스터(master): 모든 기능 + 계정 관리 / 조회자(viewer): 조회·내려받기(엑셀·PDF·백업)만 가능 — 서버가 쓰기 요청을 거부합니다.
// - 같은 사내망의 PC 에서 http://<서버PC 주소>:<포트> 로 접속합니다.
'use strict';
const http = require('http'), fs = require('fs'), path = require('path'), crypto = require('crypto'), os = require('os'), readline = require('readline');

const ROOT = __dirname, DATA = path.join(ROOT, 'data'), HTML = path.join(ROOT, 'welder-cert.html');
const STORES = ['welders', 'records', 'settings', 'images', 'wps', 'pqr', 'joints'];
const KEYPATH = { settings: 'key' };           // 나머지는 id 자동 증가
const argv = process.argv.slice(2), arg = (k, d) => { const i = argv.indexOf('--' + k); return i >= 0 && argv[i + 1] ? argv[i + 1] : d; };
const PORT = +arg('port', process.env.PORT || 8080), MAX_BODY = 400 * 1024 * 1024, SESSION_MS = 12 * 3600 * 1000;

fs.mkdirSync(path.join(DATA, 'backup'), { recursive: true });

// ---------- 저장소 (메모리 + 파일, 쓰기는 임시 파일 → 교체) ----------
const store = {}; let version = Date.now();
for (const s of STORES) {
  const f = path.join(DATA, s + '.json'); let d = { seq: 0, items: {} };
  try { d = JSON.parse(fs.readFileSync(f, 'utf8')); } catch (e) { if (e.code !== 'ENOENT') { console.error(`[오류] ${f} 을(를) 읽을 수 없습니다: ${e.message}`); process.exit(1); } }
  store[s] = d;
}
const dirty = new Set(); let saveT = null;
function markDirty(s) { dirty.add(s); version++; clearTimeout(saveT); saveT = setTimeout(flush, 300); }
function flush() { for (const s of [...dirty]) { const f = path.join(DATA, s + '.json'), t = f + '.tmp'; fs.writeFileSync(t, JSON.stringify(store[s])); fs.renameSync(t, f); dirty.delete(s); } }
process.on('SIGINT', () => { flush(); process.exit(0); }); process.on('SIGTERM', () => { flush(); process.exit(0); });
const kp = s => KEYPATH[s] || 'id';
function putOne(s, v) { const st = store[s], k = kp(s); if (k === 'id') { if (v.id == null) v.id = ++st.seq; else if (+v.id > st.seq) st.seq = +v.id; } st.items[String(v[k])] = v; return v[k]; }

// ---------- 쪽지 (조회 전용 계정 -> 마스터 의견, 마스터 답장) ----------
const MF = path.join(DATA, 'messages.json'); let msgs = [];
try { msgs = JSON.parse(fs.readFileSync(MF, 'utf8')); } catch (e) { msgs = []; }
const saveMsgs = () => { const t = MF + '.tmp'; fs.writeFileSync(t, JSON.stringify(msgs)); fs.renameSync(t, MF); };
const msgCount = ses => ses.role === 'master' ? msgs.filter(m => !m.done).length : msgs.filter(m => m.from === ses.name && m.ru).length;
const msgSent = new Map();   // 사용자별 시간당 전송 제한

// ---------- 계정 ----------
const UF = path.join(DATA, 'users.json'); let users = {};
try { users = JSON.parse(fs.readFileSync(UF, 'utf8')); } catch (e) { users = {}; }
const saveUsers = () => { const t = UF + '.tmp'; fs.writeFileSync(t, JSON.stringify(users, null, 1)); fs.renameSync(t, UF); };
const hashPw = (pw, salt) => crypto.scryptSync(String(pw), salt, 32).toString('hex');
function setUser(name, pw, role) { const salt = crypto.randomBytes(16).toString('hex'); users[name] = { salt, hash: hashPw(pw, salt), role, created: users[name] ? users[name].created : new Date().toISOString() }; saveUsers(); }
function checkUser(name, pw) { const u = users[name]; if (!u) { hashPw(pw, 'x'); return null; } const a = Buffer.from(hashPw(pw, u.salt), 'hex'), b = Buffer.from(u.hash, 'hex'); return a.length === b.length && crypto.timingSafeEqual(a, b) ? u : null; }
const masters = () => Object.keys(users).filter(n => users[n].role === 'master');

const sessions = new Map();   // token -> {name, role, exp}
const fails = new Map();      // ip -> [timestamps]
function session(req) { const m = /(?:^|;\s*)wsess=([0-9a-f]{64})/.exec(req.headers.cookie || ''); if (!m) return null; const s = sessions.get(m[1]); if (!s || s.exp < Date.now()) { sessions.delete(m[1]); return null; } s.exp = Date.now() + SESSION_MS; s.token = m[1]; return s; }
setInterval(() => { const n = Date.now(); for (const [k, s] of sessions) if (s.exp < n) sessions.delete(k); }, 600000).unref();

// ---------- 백업 (하루 1회, 14일 보관) ----------
function dailyBackup() {
  try { flush(); const day = new Date().toISOString().slice(0, 10), dir = path.join(DATA, 'backup', day); if (fs.existsSync(dir)) return; fs.mkdirSync(dir, { recursive: true });
    for (const f of [...STORES.map(s => s + '.json'), 'users.json', 'messages.json']) if (fs.existsSync(path.join(DATA, f))) fs.copyFileSync(path.join(DATA, f), path.join(dir, f));
    const days = fs.readdirSync(path.join(DATA, 'backup')).sort(); while (days.length > 14) fs.rmSync(path.join(DATA, 'backup', days.shift()), { recursive: true, force: true });
  } catch (e) { console.error('[백업 실패]', e.message); } }
setInterval(dailyBackup, 6 * 3600 * 1000).unref();

// ---------- HTTP ----------
const send = (res, code, obj, extra) => { const b = typeof obj === 'string' ? obj : JSON.stringify(obj); res.writeHead(code, { 'Content-Type': typeof obj === 'string' ? 'text/html; charset=utf-8' : 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', ...(extra || {}) }); res.end(b); };
function body(req) { return new Promise((ok, no) => { const a = []; let n = 0; req.on('data', c => { n += c.length; if (n > MAX_BODY) { no(new Error('too large')); req.destroy(); } else a.push(c); }); req.on('end', () => { try { ok(a.length ? JSON.parse(Buffer.concat(a).toString('utf8')) : {}); } catch (e) { no(e); } }); req.on('error', no); }); }

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://x'), p = url.pathname;
  try {
    if (req.method === 'GET' && (p === '/' || p === '/index.html' || p === '/welder-cert.html')) { if (!fs.existsSync(HTML)) return send(res, 500, 'welder-cert.html 파일이 server.js 와 같은 폴더에 없습니다.'); res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' }); return fs.createReadStream(HTML).pipe(res); }
    if (!p.startsWith('/api/')) return send(res, 404, { error: 'not found' });
    if (req.method === 'POST' && req.headers['x-requested-with'] !== 'welder') return send(res, 403, { error: 'bad request' });
    if (p === '/api/login' && req.method === 'POST') {
      const ip = req.socket.remoteAddress, now = Date.now(), f = (fails.get(ip) || []).filter(t => now - t < 300000);
      if (f.length >= 8) return send(res, 429, { error: '로그인 시도가 너무 많습니다. 5분 뒤 다시 시도하세요.' });
      const b = await body(req), u = checkUser(String(b.user || '').trim(), b.pass);
      if (!u) { f.push(now); fails.set(ip, f); return send(res, 401, { error: '아이디 또는 비밀번호가 올바르지 않습니다.' }); }
      fails.delete(ip); const token = crypto.randomBytes(32).toString('hex'); sessions.set(token, { name: String(b.user).trim(), role: u.role, exp: now + SESSION_MS });
      return send(res, 200, { user: String(b.user).trim(), role: u.role, v: version }, { 'Set-Cookie': `wsess=${token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=${SESSION_MS / 1000}` }); }
    if (p === '/api/hello') return send(res, 200, { server: true, needSetup: !masters().length });   // 서버 모드 감지용(로그인 불필요)
    const ses = session(req); if (!ses) return send(res, 401, { error: 'login' });
    if (p === '/api/logout') { sessions.delete(ses.token); return send(res, 200, {}, { 'Set-Cookie': 'wsess=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0' }); }
    if (p === '/api/me') return send(res, 200, { user: ses.name, role: ses.role, v: version });
    if (p === '/api/version') return send(res, 200, { v: version, m: msgCount(ses) });
    if (p === '/api/msgs' && req.method === 'GET') return send(res, 200, ses.role === 'master' ? msgs : msgs.filter(m => m.from === ses.name));
    if (p === '/api/msg' && req.method === 'POST') { const b = await body(req), text = String(b.text || '').trim().slice(0, 2000); if (!text) return send(res, 400, { error: '내용을 입력하세요.' });
      const now = Date.now(), a = (msgSent.get(ses.name) || []).filter(t => now - t < 3600000); if (a.length >= 30) return send(res, 429, { error: '쪽지를 너무 많이 보냈습니다. 잠시 뒤 다시 시도하세요.' }); a.push(now); msgSent.set(ses.name, a);
      msgs.push({ id: crypto.randomBytes(6).toString('hex'), from: ses.name, role: ses.role, text, ref: String(b.ref || '').slice(0, 200), ts: now, done: false, ru: false, replies: [] }); saveMsgs(); return send(res, 200, {}); }
    if (p === '/api/msg/seen' && req.method === 'POST') { let ch = false; for (const m of msgs) if (m.from === ses.name && m.ru) { m.ru = false; ch = true; } if (ch) saveMsgs(); return send(res, 200, {}); }
    if (p === '/api/passwd' && req.method === 'POST') { const b = await body(req); if (!checkUser(ses.name, b.old)) return send(res, 400, { error: '현재 비밀번호가 틀립니다.' }); if (String(b.pass || '').length < 6) return send(res, 400, { error: '비밀번호는 6자 이상이어야 합니다.' }); setUser(ses.name, b.pass, users[ses.name].role); return send(res, 200, {}); }
    let m;
    if ((m = /^\/api\/all\/(\w+)$/.exec(p)) && req.method === 'GET') { if (!STORES.includes(m[1])) return send(res, 404, {}); return send(res, 200, Object.values(store[m[1]].items)); }
    // ---- 이하 마스터 전용 ----
    if (ses.role !== 'master') return send(res, 403, { error: '조회 전용 계정은 수정할 수 없습니다.' });
    if (p === '/api/msg/reply' && req.method === 'POST') { const b = await body(req), m = msgs.find(x => x.id === b.id), text = String(b.text || '').trim().slice(0, 2000); if (!m || !text) return send(res, 400, { error: '쪽지를 찾을 수 없거나 내용이 없습니다.' }); m.replies.push({ from: ses.name, text, ts: Date.now() }); m.ru = true; saveMsgs(); return send(res, 200, {}); }
    if (p === '/api/msg/done' && req.method === 'POST') { const b = await body(req), m = msgs.find(x => x.id === b.id); if (!m) return send(res, 404, {}); m.done = !!b.done; saveMsgs(); return send(res, 200, {}); }
    if (p === '/api/msg/del' && req.method === 'POST') { const b = await body(req); msgs = msgs.filter(x => x.id !== b.id); saveMsgs(); return send(res, 200, {}); }
    if (p === '/api/users' && req.method === 'GET') return send(res, 200, Object.keys(users).map(n => ({ name: n, role: users[n].role, created: users[n].created })));
    if (p === '/api/users' && req.method === 'POST') { const b = await body(req), n = String(b.name || '').trim(), role = 'viewer';   // 마스터는 1명만 (처음 실행 때 만든 계정)
      if (!/^[\w.@\-가-힣]{2,30}$/.test(n)) return send(res, 400, { error: '아이디는 2~30자(한글/영문/숫자/._-@)로 입력하세요.' }); if (String(b.pass || '').length < 6) return send(res, 400, { error: '비밀번호는 6자 이상이어야 합니다.' });
      setUser(n, b.pass, users[n] ? users[n].role : role); for (const [k, s] of sessions) if (s.name === n) sessions.delete(k); return send(res, 200, {}); }
    if (p === '/api/users/del' && req.method === 'POST') { const b = await body(req), n = String(b.name || ''); if (!users[n]) return send(res, 404, { error: '없는 계정' }); if (users[n].role === 'master' && masters().length <= 1) return send(res, 400, { error: '마지막 마스터 계정은 삭제할 수 없습니다.' }); delete users[n]; saveUsers(); for (const [k, s] of sessions) if (s.name === n) sessions.delete(k); return send(res, 200, {}); }
    if ((m = /^\/api\/put\/(\w+)$/.exec(p)) && req.method === 'POST') { if (!STORES.includes(m[1])) return send(res, 404, {}); const v = await body(req); const id = putOne(m[1], v); markDirty(m[1]); return send(res, 200, { id, v: version }); }
    if ((m = /^\/api\/putMany\/(\w+)$/.exec(p)) && req.method === 'POST') { if (!STORES.includes(m[1])) return send(res, 404, {}); const a = await body(req); if (!Array.isArray(a)) return send(res, 400, {}); const ids = a.map(v => putOne(m[1], v)); markDirty(m[1]); return send(res, 200, { ids, v: version }); }
    if ((m = /^\/api\/del\/(\w+)\/(.+)$/.exec(p)) && req.method === 'POST') { if (!STORES.includes(m[1])) return send(res, 404, {}); delete store[m[1]].items[decodeURIComponent(m[2])]; markDirty(m[1]); return send(res, 200, { v: version }); }
    if ((m = /^\/api\/clear\/(\w+)$/.exec(p)) && req.method === 'POST') { if (!STORES.includes(m[1])) return send(res, 404, {}); store[m[1]].items = {}; markDirty(m[1]); return send(res, 200, { v: version }); }
    return send(res, 404, { error: 'not found' });
  } catch (e) { console.error('[요청 오류]', p, e.message); try { send(res, 400, { error: String(e.message || e) }); } catch (_) {} }
});

// ---------- 시작 ----------
function ask(q, hidden) { return new Promise(ok => { const rl = readline.createInterface({ input: process.stdin, output: process.stdout }); if (hidden) { rl._writeToOutput = s => { if (s.includes(q)) process.stdout.write(s); }; } rl.question(q, a => { rl.close(); if (hidden) process.stdout.write('\n'); ok(a.trim()); }); }); }
(async () => {
  if (!masters().length) {
    const m = (arg('master', '') || '').match(/^([^:]+):(.+)$/);
    console.log('\n=== 처음 실행: 마스터 계정을 만듭니다 (모든 기능 + 계정 관리) ===');
    const name = m ? m[1] : await ask('마스터 아이디: '); const pw = m ? m[2] : await ask('마스터 비밀번호 (6자 이상): ', true);
    if (!name || pw.length < 6) { console.error('아이디와 6자 이상의 비밀번호가 필요합니다.'); process.exit(1); }
    setUser(name, pw, 'master'); console.log(`마스터 계정 "${name}" 을(를) 만들었습니다.\n`);
  }
  dailyBackup();
  server.listen(PORT, '0.0.0.0', () => {
    const ips = Object.values(os.networkInterfaces()).flat().filter(i => i && i.family === 'IPv4' && !i.internal).map(i => i.address);
    console.log(`서버가 시작되었습니다 (종료: Ctrl+C)\n  이 PC에서:  http://localhost:${PORT}\n${ips.map(ip => `  다른 PC에서: http://${ip}:${PORT}`).join('\n')}\n  데이터 폴더: ${DATA}\n`); });
})();

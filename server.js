import express from 'express';
import session from 'express-session';
import Database from 'better-sqlite3';
import net from 'node:net';
import fs from 'node:fs';

const app = express();

const PORT = Number(process.env.PORT || 3000);
const SOCKS_PORT = Number(process.env.SOCKS_PORT || 1080);

const ADMIN_USER = process.env.ADMIN_USER || 'admin';
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'change-me';
const SESSION_SECRET = process.env.SESSION_SECRET || 'change-me-too';

fs.mkdirSync('./data', { recursive: true });

const db = new Database('./data/panel.db');

db.exec(`
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    quota INTEGER NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    expires TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
`);

app.use(express.urlencoded({ extended: true }));
app.use(express.json());

app.use(session({
    secret: SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: {
        httpOnly: true,
        sameSite: 'lax'
    }
}));

const esc = s =>
    String(s ?? '').replace(/[&<>"']/g, c => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }[c]));

const gb = n => Math.max(1, Number(n) || 1) * 1024 ** 3;

function bytes(n) {
    n = Number(n) || 0;

    if (n < 1024 ** 2)
        return (n / 1024).toFixed(1) + ' KB';

    if (n < 1024 ** 3)
        return (n / 1024 ** 2).toFixed(2) + ' MB';

    return (n / 1024 ** 3).toFixed(2) + ' GB';
}

function auth(req, res, next) {
    if (req.session.admin) return next();
    res.redirect('/login');
}

function page(title, body) {
    return `
<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(title)}</title>
<style>${css}</style>
</head>
<body>
<header>
<b>MAXO SOCKS</b>
<a href="/logout">خروج</a>
</header>
<main>${body}</main>
</body>
</html>`;
}

const css = `
*{box-sizing:border-box}

body{
    margin:0;
    background:#080b11;
    color:#eef2f8;
    font-family:Arial,sans-serif
}

header{
    height:64px;
    padding:0 6%;
    display:flex;
    align-items:center;
    justify-content:space-between;
    background:#111722;
    border-bottom:1px solid #252d3b
}

a{
    color:#9db7ff;
    text-decoration:none
}

main{
    max-width:1200px;
    margin:auto;
    padding:26px 16px
}

.hero{
    margin-bottom:20px
}

.hero h1{
    font-size:30px;
    margin:0 0 8px
}

.grid{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:18px
}

.card{
    background:#111722;
    border:1px solid #273043;
    border-radius:18px;
    padding:20px;
    margin-bottom:18px;
    box-shadow:0 14px 40px #0006
}

label{
    display:block;
    color:#aeb8ca;
    margin:12px 0 6px
}

input{
    width:100%;
    padding:12px;
    border:1px solid #303a4d;
    border-radius:10px;
    background:#080b11;
    color:#fff
}

button{
    border:0;
    border-radius:10px;
    padding:11px 16px;
    background:#557cff;
    color:white;
    cursor:pointer;
    margin-top:13px
}

.danger{
    background:#a83b4c
}

.inline{
    display:inline
}

.inline button{
    margin:2px
}

table{
    width:100%;
    border-collapse:collapse
}

th,td{
    text-align:right;
    padding:12px;
    border-bottom:1px solid #273043;
    white-space:nowrap
}

.table{
    overflow:auto
}

.ok{
    color:#7de0a5
}

.bad{
    color:#ff9aaa
}

.login{
    min-height:100vh;
    display:grid;
    place-items:center
}

.login .card{
    width:min(420px,92vw)
}

@media(max-width:800px){
    .grid{
        grid-template-columns:1fr
    }
}
`;


/* =========================
   LOGIN
========================= */

app.get('/login', (req, res) => {
    res.send(page('ورود', `
        <div class="login">
            <div class="card">
                <h1>MAXO SOCKS</h1>
                <p>ورود مدیریت</p>

                <form method="post">

                    <input
                        name="username"
                        placeholder="نام کاربری"
                        required
                    >

                    <input
                        name="password"
                        type="password"
                        placeholder="رمز عبور"
                        required
                    >

                    <button>ورود</button>

                </form>
            </div>
        </div>
    `));
});

app.post('/login', (req, res) => {

    if (
        req.body.username === ADMIN_USER &&
        req.body.password === ADMIN_PASSWORD
    ) {
        req.session.admin = true;
        return res.redirect('/');
    }

    res.status(401).send('نام کاربری یا رمز عبور اشتباه است');
});

app.get('/logout', (req, res) => {
    req.session.destroy(() => res.redirect('/login'));
});


/* =========================
   PANEL
========================= */

app.get('/', auth, (req, res) => {

    const users = db
        .prepare('SELECT * FROM users ORDER BY id DESC')
        .all();

    const rows = users.map(u => {

        const expired = new Date(u.expires) < new Date();

        const active =
            u.enabled &&
            !expired &&
            u.used < u.quota;

        return `
<tr>

<td>${esc(u.name)}</td>

<td>${esc(u.username)}</td>

<td>
${bytes(u.used)}
/
${bytes(u.quota)}
</td>

<td>
${esc(u.expires)}
</td>

<td class="${active ? 'ok' : 'bad'}">
${active ? 'فعال' : 'غیرفعال'}
</td>

<td>

<form
    class="inline"
    method="post"
    action="/users/${u.id}/toggle"
>
<button>
${u.enabled ? 'خاموش' : 'روشن'}
</button>
</form>

<form
    class="inline"
    method="post"
    action="/users/${u.id}/delete"
    onsubmit="return confirm('حذف شود؟')"
>
<button class="danger">
حذف
</button>
</form>

</td>

</tr>
`;
    }).join('');

    res.send(page('پنل', `

<section class="hero">
<h1>مدیریت پروکسی</h1>
<p>ساخت اکانت با حجم و تاریخ انقضا</p>
</section>

<section class="grid">

<div class="card">

<h2>ساخت اکانت</h2>

<form method="post" action="/users">

<label>نام</label>
<input
    name="name"
    placeholder="مثلاً MAXO-01"
    required
>

<label>Username</label>
<input
    name="username"
    required
>

<label>Password</label>
<input
    name="password"
    required
>

<label>حجم (GB)</label>
<input
    name="quota"
    type="number"
    min="1"
    value="10"
    required
>

<label>تاریخ انقضا</label>
<input
    name="expires"
    type="datetime-local"
    required
>

<button>
ساخت کاربر
</button>

</form>

</div>

<div class="card">

<h2>IP تمیز</h2>

<p>
IP خروجی باید متعلق به خود Railway یا یک upstream واقعی باشد.
</p>

<p>
TCP Proxy فعلی برای اتصال خارجی استفاده می‌شود.
</p>

</div>

</section>

<section class="card">

<h2>کاربران</h2>

<div class="table">

<table>

<thead>

<tr>
<th>نام</th>
<th>Username</th>
<th>مصرف</th>
<th>انقضا</th>
<th>وضعیت</th>
<th>عملیات</th>
</tr>

</thead>

<tbody>

${rows || `
<tr>
<td colspan="6">
کاربری وجود ندارد
</td>
</tr>
`}

</tbody>

</table>

</div>

</section>

`));
});


/* =========================
   USERS
========================= */

app.post('/users', auth, (req, res) => {

    try {

        const name =
            String(req.body.name || '').trim();

        const username =
            String(req.body.username || '').trim();

        const password =
            String(req.body.password || '');

        const expires =
            String(req.body.expires || '');

        if (
            !name ||
            !username ||
            !password ||
            !expires
        ) {
            throw Error('اطلاعات ناقص');
        }

        db.prepare(`
            INSERT INTO users
            (name,username,password,quota,expires)
            VALUES(?,?,?,?,?)
        `).run(
            name,
            username,
            password,
            gb(req.body.quota),
            expires
        );

        res.redirect('/');

    } catch (e) {

        res
            .status(400)
            .send('خطا: ' + esc(e.message));

    }

});


app.post('/users/:id/toggle', auth, (req, res) => {

    db.prepare(`
        UPDATE users
        SET enabled = 1 - enabled
        WHERE id = ?
    `).run(req.params.id);

    res.redirect('/');
});


app.post('/users/:id/delete', auth, (req, res) => {

    db.prepare(`
        DELETE FROM users
        WHERE id = ?
    `).run(req.params.id);

    res.redirect('/');
});


/* ==========================================================
   SOCKS5
   استاندارد RFC 1928 + RFC 1929
========================================================== */

const socks = net.createServer(socket => {

    socket.setTimeout(120000);

    let buffer = Buffer.alloc(0);
    let processing = false;

    function append(data) {

        buffer = Buffer.concat([
            buffer,
            data
        ]);

    }

    function need(n) {

        return buffer.length >= n;

    }

    function take(n) {

        const out = buffer.subarray(0, n);

        buffer = buffer.subarray(n);

        return out;

    }

    function readMore() {

        return new Promise((resolve, reject) => {

            const onData = data => {
                cleanup();
                resolve(data);
            };

            const onError = err => {
                cleanup();
                reject(err);
            };

            const onClose = () => {
                cleanup();
                reject(new Error('socket closed'));
            };

            function cleanup() {
                socket.off('data', onData);
                socket.off('error', onError);
                socket.off('close', onClose);
            }

            socket.once('data', onData);
            socket.once('error', onError);
            socket.once('close', onClose);

        });

    }

    async function readBytes(n) {

        while (!need(n)) {

            const data = await readMore();

            append(data);

        }

        return take(n);

    }


    async function run() {

        try {

            /* =========================
               METHOD NEGOTIATION
            ========================= */

            const head =
                await readBytes(2);

            if (head[0] !== 0x05) {
                socket.destroy();
                return;
            }

            const methodCount = head[1];

            const methods =
                await readBytes(methodCount);

            let usernamePassword = false;

            for (const method of methods) {

                if (method === 0x02) {
                    usernamePassword = true;
                    break;
                }

            }

            if (!usernamePassword) {

                socket.end(
                    Buffer.from([0x05, 0xff])
                );

                return;
            }

            socket.write(
                Buffer.from([0x05, 0x02])
            );


            /* =========================
               USERNAME / PASSWORD
               RFC 1929
            ========================= */

            const authHead =
                await readBytes(2);

            if (authHead[0] !== 0x01) {

                socket.destroy();

                return;
            }

            const usernameLength =
                authHead[1];

            const username =
                (await readBytes(usernameLength))
                    .toString('utf8');

            const passwordLength =
                (await readBytes(1))[0];

            const password =
                (await readBytes(passwordLength))
                    .toString('utf8');


            /* =========================
               CHECK USER
            ========================= */

            const user = db
                .prepare(`
                    SELECT *
                    FROM users
                    WHERE username = ?
                `)
                .get(username);

            const valid =
                user &&
                user.enabled === 1 &&
                user.password === password &&
                new Date(user.expires) >= new Date() &&
                Number(user.used) < Number(user.quota);

            if (!valid) {

                socket.end(
                    Buffer.from([
                        0x01,
                        0x01
                    ])
                );

                return;
            }

            socket.write(
                Buffer.from([
                    0x01,
                    0x00
                ])
            );


            /* =========================
               SOCKS REQUEST
            ========================= */

            const requestHead =
                await readBytes(4);

            if (
                requestHead[0] !== 0x05 ||
                requestHead[1] !== 0x01
            ) {

                socket.end(
                    Buffer.from([
                        0x05,
                        0x07,
                        0x00,
                        0x01,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0
                    ])
                );

                return;
            }

            const addressType =
                requestHead[3];

            let host;


            /* IPv4 */

            if (addressType === 0x01) {

                const ip =
                    await readBytes(4);

                host =
                    `${ip[0]}.${ip[1]}.${ip[2]}.${ip[3]}`;

            }


            /* DOMAIN */

            else if (addressType === 0x03) {

                const length =
                    (await readBytes(1))[0];

                host =
                    (await readBytes(length))
                        .toString('utf8');

            }


            /* IPv6 */

            else if (addressType === 0x04) {

                const ip =
                    await readBytes(16);

                const parts = [];

                for (let i = 0; i < 16; i += 2) {

                    parts.push(
                        ip.readUInt16BE(i)
                            .toString(16)
                    );

                }

                host = parts.join(':');

            }

            else {

                socket.end(
                    Buffer.from([
                        0x05,
                        0x08,
                        0x00,
                        0x01,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0
                    ])
                );

                return;

            }


            /* PORT */

            const portBuffer =
                await readBytes(2);

            const port =
                portBuffer.readUInt16BE(0);


            /* =========================
               CONNECT
            ========================= */

            const remote =
                net.createConnection({
                    host,
                    port
                });


            remote.once('connect', () => {

                socket.write(
                    Buffer.from([
                        0x05,
                        0x00,
                        0x00,
                        0x01,
                        0x00,
                        0x00,
                        0x00,
                        0x00,
                        0x00,
                        0x00
                    ])
                );


                /* =========================
                   TRAFFIC ACCOUNTING
                ========================= */

                let pendingBytes = 0;

                function addUsage(amount) {

                    pendingBytes += amount;

                    /*
                     * هر 64KB در دیتابیس ثبت می‌شود.
                     */
                    if (pendingBytes >= 64 * 1024) {

                        const amountToSave =
                            pendingBytes;

                        pendingBytes = 0;

                        db.prepare(`
                            UPDATE users
                            SET used =
                                MIN(
                                    quota,
                                    used + ?
                                )
                            WHERE id = ?
                        `).run(
                            amountToSave,
                            user.id
                        );

                    }

                }


                socket.on('data', data => {

                    addUsage(data.length);

                });

                remote.on('data', data => {

                    addUsage(data.length);

                });


                socket.pipe(remote);
                remote.pipe(socket);

            });


            remote.once('error', () => {

                if (!socket.destroyed) {

                    socket.end(
                        Buffer.from([
                            0x05,
                            0x05,
                            0x00,
                            0x01,
                            0,
                            0,
                            0,
                            0,
                            0,
                            0
                        ])
                    );

                }

            });


            socket.once('close', () => {

                remote.destroy();

            });

            remote.once('close', () => {

                if (!socket.destroyed)
                    socket.destroy();

            });

        }

        catch (err) {

            console.error(
                'SOCKS ERROR:',
                err.message
            );

            if (!socket.destroyed)
                socket.destroy();

        }

    }


    socket.once('data', data => {

        append(data);

        if (!processing) {

            processing = true;

            run();

        }

    });

    socket.once('error', () => {});

    socket.once('timeout', () => {

        socket.destroy();

    });

});


/* =========================
   START
========================= */

socks.listen(
    SOCKS_PORT,
    '0.0.0.0',
    () => {

        console.log(
            `SOCKS ${SOCKS_PORT}`
        );

    }
);


app.listen(
    PORT,
    '0.0.0.0',
    () => {

        console.log(
            `WEB ${PORT}`
        );

    }
);
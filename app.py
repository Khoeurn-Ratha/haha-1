from flask import Flask, request, jsonify, session, render_template_string
import os
import requests
import psycopg2
import psycopg2.extras
import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "ratha_quant_secure_secret_2026")

ADMIN_PASSWORD = "admin123"
USER_PASSWORD = "user123"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8622254541:AAHOwR8hHnfjMrkz4y8udsEuC1jn49EHjII")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "6915043499")

def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram Alert Error: {e}")
        return False

# Database Connection with SSL Support for Render PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://ramote_user:KB6MBdQ5zXkT5zDZ5APXNmBAVgUx6SDZ@dpg-da8k9vijnfac73emabgg-a/ramote")

def get_db_connection():
    if DATABASE_URL:
        try:
            # Added sslmode='require' for Render PostgreSQL
            conn = psycopg2.connect(DATABASE_URL, sslmode='require', cursor_factory=psycopg2.extras.RealDictCursor)
            return conn, "postgres"
        except Exception as e:
            print(f"PostgreSQL connection failed: {e}, falling back to SQLite...")
    
    conn = sqlite3.connect("quant_trading.db")
    conn.row_factory = sqlite3.Row
    return conn, "sqlite"

def init_db():
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        if db_type == "postgres":
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id SERIAL PRIMARY KEY,
                    date TEXT NOT NULL,
                    pair TEXT NOT NULL,
                    type TEXT NOT NULL,
                    pnl DOUBLE PRECISION NOT NULL
                )
            ''')
            cursor.execute("SELECT COUNT(*) as count FROM trades")
            row = cursor.fetchone()
            count = row['count'] if row else 0
            if count == 0:
                sample_data = [
                    ("2026-06-01", "XAUUSD", "BUY", 15.0),
                    ("2026-06-02", "EURUSD", "SELL", 25.0),
                    ("2026-06-03", "XAUUSD", "BUY", 30.0)
                ]
                for item in sample_data:
                    cursor.execute("INSERT INTO trades (date, pair, type, pnl) VALUES (%s, %s, %s, %s)", item)
                conn.commit()
        else:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    pair TEXT NOT NULL,
                    type TEXT NOT NULL,
                    pnl REAL NOT NULL
                )
            ''')
            cursor.execute("SELECT COUNT(*) FROM trades")
            if cursor.fetchone()[0] == 0:
                sample_data = [
                    ("2026-06-01", "XAUUSD", "BUY", 15.0),
                    ("2026-06-02", "EURUSD", "SELL", 25.0),
                    ("2026-06-03", "XAUUSD", "BUY", 30.0)
                ]
                cursor.executemany("INSERT INTO trades (date, pair, type, pnl) VALUES (?, ?, ?, ?)", sample_data)
                conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database Initialization Error: {e}")

init_db()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RATHA // RENDER QUANT TERMINAL</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;800&family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    fontFamily: { sans: ['Inter', 'sans-serif'], mono: ['JetBrains Mono', 'monospace'] },
                    boxShadow: { 'neon': '0 0 30px rgba(0, 240, 255, 0.4)' }
                }
            }
        }
    </script>
    <style>
        body { background-color: #010308; position: relative; overflow-x: hidden; margin: 0; padding: 0; }
        .cyber-grid {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background-image: linear-gradient(rgba(0, 240, 255, 0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 240, 255, 0.06) 1px, transparent 1px);
            background-size: 60px 60px; z-index: -3; pointer-events: none;
        }
        .glass-panel {
            background: rgba(3, 7, 18, 0.85); backdrop-filter: blur(16px);
            border: 1px solid rgba(0, 240, 255, 0.25); box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8);
        }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #000000; }
        ::-webkit-scrollbar-thumb { background: #00f0ff; border-radius: 3px; }
    </style>
</head>
<body class="text-slate-200 font-sans min-h-screen flex flex-col selection:bg-cyan-400 selection:text-black">
    <div class="cyber-grid"></div>

    <div class="bg-black/90 backdrop-blur-md border-b border-cyan-500/30 py-2 px-4 text-[11px] font-mono flex justify-between items-center z-40 text-cyan-400">
        <div class="flex items-center gap-6 overflow-x-auto whitespace-nowrap">
            <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping"></span><strong class="text-white">AI-UNIT // XAUUSD:</strong> 2,485.40 <span class="text-emerald-400">+0.42%</span></span>
        </div>
        <div class="hidden md:flex items-center gap-4 text-cyan-400">
            <span><i class="fa-solid fa-cloud mr-1"></i> RENDER CLOUD: ONLINE</span>
            <span><i class="fa-solid fa-database mr-1"></i> POSTGRESQL: ACTIVE (SSL SECURED)</span>
        </div>
    </div>

    <!-- Login Modal -->
    <div id="loginModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-md p-4 hidden">
        <div class="glass-panel rounded-2xl w-full max-w-md p-8 space-y-6 relative z-10 border border-cyan-500/60 shadow-neon">
            <div class="text-center">
                <h2 class="text-xl font-extrabold tracking-wider text-white font-mono">ROBOTIC QUANT TERMINAL</h2>
                <p class="text-xs text-cyan-400/80 mt-1 font-mono uppercase tracking-widest">AI Security Authorization Required</p>
            </div>
            <form onsubmit="handleLogin(event)" class="space-y-4 text-xs font-mono">
                <div>
                    <label class="block text-cyan-400/70 mb-2 uppercase font-semibold">Security Protocol Key</label>
                    <input type="password" id="loginPassword" placeholder="Enter key (admin123 / user123)" required
                        class="w-full bg-black/90 border border-cyan-500/40 rounded-xl px-4 py-3 text-cyan-200 focus:outline-none focus:border-cyan-400">
                </div>
                <div id="loginError" class="text-rose-400 text-[11px] font-bold bg-rose-500/10 border border-rose-500/20 p-2.5 rounded-lg hidden text-center"></div>
                <button type="submit" class="w-full py-3.5 rounded-xl bg-gradient-to-r from-cyan-500 to-emerald-400 text-black font-extrabold text-xs uppercase hover:opacity-95">Initialize Terminal</button>
            </form>
            <div class="text-[10px] text-center text-slate-400 font-mono">Hint: <span class="text-cyan-400">admin123</span> or <span class="text-slate-200">user123</span></div>
        </div>
    </div>

    <!-- Main Container -->
    <div class="container mx-auto px-4 py-6 max-w-7xl space-y-6 flex-grow relative z-10">
        <div class="flex justify-between items-center glass-panel rounded-2xl p-6 border-cyan-500/40">
            <div>
                <h1 class="text-xl font-bold text-white font-mono">RATHA // CYBER TRADING COMMAND</h1>
                <p class="text-xs text-slate-400 font-mono mt-0.5">Role: <span id="roleDisplay" class="text-cyan-400 font-bold uppercase">Loading...</span></p>
            </div>
            <button onclick="logout()" class="px-4 py-2.5 bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-mono rounded-xl hover:bg-rose-500/20">SHUTDOWN</button>
        </div>

        <!-- Chart -->
        <div class="glass-panel rounded-2xl p-6 border-cyan-500/30">
            <h2 class="text-sm font-bold text-slate-200 mb-4 font-mono"><i class="fa-solid fa-chart-line text-cyan-400"></i> Render PostgreSQL Telemetry Curve</h2>
            <div class="h-72 w-full"><canvas id="performanceChart"></canvas></div>
        </div>

        <!-- Table & Admin Input -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div id="adminPanel" class="glass-panel border-cyan-500/50 rounded-2xl p-6 hidden space-y-4">
                <h2 class="text-sm font-bold text-cyan-400 font-mono">Execute Neural Trade</h2>
                <form onsubmit="addTrade(event)" class="space-y-3 text-xs font-mono">
                    <input type="date" id="tradeDate" required class="w-full bg-black border border-cyan-500/40 rounded-xl px-3 py-2 text-cyan-200">
                    <input type="text" id="tradePair" placeholder="XAUUSD" required class="w-full bg-black border border-cyan-500/40 rounded-xl px-3 py-2 text-cyan-200 uppercase">
                    <select id="tradeType" class="w-full bg-black border border-cyan-500/40 rounded-xl px-3 py-2 text-cyan-200">
                        <option value="BUY">BUY</option><option value="SELL">SELL</option>
                    </select>
                    <input type="number" step="any" id="tradePnl" placeholder="Net PnL ($)" required class="w-full bg-black border border-cyan-500/40 rounded-xl px-3 py-2 text-cyan-200">
                    <button type="submit" class="w-full py-2.5 bg-cyan-500 text-black font-bold rounded-xl uppercase">Broadcast</button>
                </form>
            </div>
            <div id="tableContainer" class="lg:col-span-3 glass-panel rounded-2xl p-6 overflow-x-auto border-cyan-500/30">
                <table class="w-full text-left text-xs font-mono whitespace-nowrap">
                    <thead>
                        <tr class="border-b border-cyan-500/40 text-cyan-400">
                            <th class="pb-3 px-3">ID</th><th class="pb-3 px-3">Date</th><th class="pb-3 px-3">Pair</th><th class="pb-3 px-3">Vector</th><th class="pb-3 px-3">PnL</th><th class="pb-3 px-3 text-right action-col">Action</th>
                        </tr>
                    </thead>
                    <tbody id="tradesTableBody" class="divide-y divide-cyan-500/10"></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let currentUserRole = null;
        let performanceChart = null;

        document.addEventListener('DOMContentLoaded', () => {
            document.getElementById('tradeDate').valueAsDate = new Date();
            checkAuthStatus();
        });

        async function checkAuthStatus() {
            try {
                const res = await fetch('/api/auth-status');
                const data = await res.json();
                if (!data.authenticated) {
                    document.getElementById('loginModal').classList.remove('hidden');
                } else {
                    currentUserRole = data.role;
                    document.getElementById('roleDisplay').textContent = currentUserRole;
                    applyRolePermissions();
                    loadTrades();
                }
            } catch (err) { console.error('Auth error:', err); }
        }

        async function handleLogin(e) {
            e.preventDefault();
            const password = document.getElementById('loginPassword').value;
            const res = await fetch('/api/login', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password })
            });
            const data = await res.json();
            if (data.status === 'success') {
                currentUserRole = data.role;
                document.getElementById('loginModal').classList.add('hidden');
                document.getElementById('roleDisplay').textContent = currentUserRole;
                applyRolePermissions();
                loadTrades();
            } else {
                document.getElementById('loginError').textContent = data.message;
                document.getElementById('loginError').classList.remove('hidden');
            }
        }

        async function logout() {
            await fetch('/api/logout', { method: 'POST' });
            window.location.reload();
        }

        function applyRolePermissions() {
            const adminPanel = document.getElementById('adminPanel');
            const tableContainer = document.getElementById('tableContainer');
            if (currentUserRole === 'admin') {
                adminPanel.classList.remove('hidden');
                tableContainer.classList.remove('lg:col-span-3');
                tableContainer.classList.add('lg:col-span-2');
            } else {
                adminPanel.classList.add('hidden');
                tableContainer.classList.remove('lg:col-span-2');
                tableContainer.classList.add('lg:col-span-3');
                document.querySelectorAll('.action-col').forEach(el => el.style.display = 'none');
            }
        }

        async function loadTrades() {
            try {
                const res = await fetch('/api/trades');
                const trades = await res.json();
                const tbody = document.getElementById('tradesTableBody');
                tbody.innerHTML = '';
                let cumulative = 0;
                const labels = [], dataVals = [];

                trades.forEach(t => {
                    cumulative += t.pnl;
                    labels.push(t.date);
                    dataVals.push(cumulative);

                    const tr = document.createElement('tr');
                    let actionHtml = currentUserRole === 'admin' ? `<td class="py-3 px-3 text-right action-col"><button onclick="deleteTrade(${t.id})" class="text-rose-400 bg-rose-500/10 px-2 py-1 rounded"><i class="fa-solid fa-trash"></i></button></td>` : '';
                    tr.innerHTML = `<td class="py-3 px-3 text-cyan-400">#${t.id}</td><td class="py-3 px-3">${t.date}</td><td class="py-3 px-3 text-white font-bold">${t.pair}</td><td class="py-3 px-3">${t.type}</td><td class="py-3 px-3 font-bold ${t.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}">$${t.pnl.toFixed(2)}</td>${actionHtml}`;
                    tbody.appendChild(tr);
                });
                renderChart(labels, dataVals);
            } catch (err) { console.error('Error loading trades:', err); }
        }

        async function addTrade(e) {
            e.preventDefault();
            try {
                const res = await fetch('/api/trades', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        date: document.getElementById('tradeDate').value,
                        pair: document.getElementById('tradePair').value,
                        type: document.getElementById('tradeType').value,
                        pnl: document.getElementById('tradePnl').value
                    })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    document.getElementById('tradePair').value = '';
                    document.getElementById('tradePnl').value = '';
                    loadTrades();
                } else {
                    alert('Error: ' + (data.error || 'Unknown error'));
                }
            } catch (err) { console.error('Error adding trade:', err); }
        }

        async function deleteTrade(id) {
            if (!confirm('Delete record?')) return;
            try {
                await fetch(`/api/trades?id=${id}`, { method: 'DELETE' });
                loadTrades();
            } catch (err) { console.error('Error deleting trade:', err); }
        }

        function renderChart(labels, data) {
            const ctx = document.getElementById('performanceChart').getContext('2d');
            if (performanceChart) performanceChart.destroy();
            performanceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['Start', ...labels],
                    datasets: [{ label: 'Balance ($)', data: [10, ...data.map(v => 10 + v)], borderColor: '#00f0ff', backgroundColor: 'rgba(0, 240, 255, 0.1)', fill: true, tension: 0.3 }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    password = data.get("password", "").strip()
    if password == ADMIN_PASSWORD:
        session["role"] = "admin"
        return jsonify({"status": "success", "role": "admin"})
    elif password == USER_PASSWORD:
        session["role"] = "user"
        return jsonify({"status": "success", "role": "user"})
    return jsonify({"status": "error", "message": "Invalid password"}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "success"})

@app.route("/api/auth-status", methods=["GET"])
def auth_status():
    role = session.get("role")
    return jsonify({"authenticated": bool(role), "role": role})

@app.route("/api/trades", methods=["GET", "POST", "DELETE"])
def handle_trades():
    if not session.get("role"):
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()

        if request.method == "GET":
            cursor.execute("SELECT id, date, pair, type, pnl FROM trades ORDER BY id ASC")
            rows = cursor.fetchall()
            trades_list = [dict(row) for row in rows]
            conn.close()
            return jsonify(trades_list)
        
        if session.get("role") != "admin":
            conn.close()
            return jsonify({"error": "Admin required"}), 403

        if request.method == "POST":
            data = request.get_json() or {}
            date, pair, t_type, pnl = data.get("date"), data.get("pair", "").upper(), data.get("type", "").upper(), float(data.get("pnl", 0))
            
            if db_type == "postgres":
                cursor.execute("INSERT INTO trades (date, pair, type, pnl) VALUES (%s, %s, %s, %s) RETURNING id", (date, pair, t_type, pnl))
                row = cursor.fetchone()
                new_id = row['id'] if row else 1
            else:
                cursor.execute("INSERT INTO trades (date, pair, type, pnl) VALUES (?, ?, ?, ?)", (date, pair, t_type, pnl))
                new_id = cursor.lastrowid
            conn.commit()
            conn.close()

            send_telegram_alert(f"🤖 *TRADE EXECUTED*\nPair: `{pair}`\nVector: `{t_type}`\nPnL: `${pnl:.2f}`")
            return jsonify({"status": "success", "id": new_id})

        if request.method == "DELETE":
            trade_id = request.args.get("id", type=int)
            if db_type == "postgres":
                cursor.execute("DELETE FROM trades WHERE id = %s", (trade_id,))
            else:
                cursor.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
            conn.commit()
            conn.close()
            return jsonify({"status": "success"})
            
    except Exception as e:
        print(f"Database Operation Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

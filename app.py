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
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or not TELEGRAM_BOT_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram Alert Error: {e}")
        return False

# Database Connection Helper (Supports both Render PostgreSQL and Local SQLite)
DATABASE_URL = os.environ.get("postgresql://ramote_user:KB6MBdQ5zXkT5zDZ5APXNmBAVgUx6SDZ@dpg-da8k9vijnfac73emabgg-a/ramote")

def get_db_connection():
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        return conn, "postgres"
    else:
        conn = sqlite3.connect("quant_trading.db")
        conn.row_factory = sqlite3.Row
        return conn, "sqlite"

def init_db():
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
        cursor.execute("SELECT COUNT(*) FROM trades")
        count = cursor.fetchone()['count']
        if count == 0:
            sample_data = [
                ("2026-06-01", "XAUUSD", "BUY", 15.0),
                ("2026-06-02", "EURUSD", "SELL", 25.0),
                ("2026-06-03", "XAUUSD", "BUY", 30.0)
            ]
            for row in sample_data:
                cursor.execute("INSERT INTO trades (date, pair, type, pnl) VALUES (%s, %s, %s, %s)", row)
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

init_db()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RATHA // QUANT TRADING TERMINAL</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: { cyber: { 900: '#070a14', 950: '#020408', 800: '#0f172a' } },
                    boxShadow: {
                        'neon': '0 0 30px rgba(6, 182, 212, 0.25)',
                        'neon-glow': '0 0 35px rgba(16, 185, 129, 0.3)',
                        'neon-hover': '0 0 25px rgba(6, 182, 212, 0.5)',
                        'rose-hover': '0 0 25px rgba(244, 63, 94, 0.5)'
                    }
                }
            }
        }
    </script>
    <style>
        body {
            background-color: #020408;
            background-image: 
                radial-gradient(circle at 15% 20%, rgba(6, 182, 212, 0.08) 0%, transparent 40%),
                radial-gradient(circle at 85% 80%, rgba(16, 185, 129, 0.08) 0%, transparent 40%),
                radial-gradient(circle at 50% 50%, rgba(59, 130, 246, 0.05) 0%, transparent 60%),
                linear-gradient(to right, rgba(30, 41, 59, 0.15) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(30, 41, 59, 0.15) 1px, transparent 1px);
            background-size: 100% 100%, 100% 100%, 100% 100%, 32px 32px, 32px 32px;
            background-attachment: fixed;
        }
        .scanline {
            position: fixed; top: 0; left: 0; width: 100%; height: 2px;
            background: linear-gradient(90deg, transparent, rgba(6, 182, 212, 0.5), transparent);
            animation: scan 8s linear infinite; pointer-events: none; z-index: 100;
        }
        @keyframes scan {
            0% { transform: translateY(-100vh); }
            100% { transform: translateY(100vh); }
        }
        .glass-panel {
            background: rgba(7, 10, 20, 0.75);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(30, 41, 59, 0.8);
            transition: all 0.3s ease-in-out;
        }
        .glass-panel:hover {
            border-color: rgba(6, 182, 212, 0.4);
            box-shadow: 0 0 25px rgba(6, 182, 212, 0.12);
            transform: translateY(-2px);
        }
    </style>
</head>
<body class="text-slate-100 font-mono min-h-screen flex flex-col selection:bg-cyan-500 selection:text-cyber-950 relative overflow-x-hidden">
    <div class="scanline"></div>
    <div class="absolute top-10 left-10 w-96 h-96 bg-cyan-500/10 rounded-full blur-[120px] pointer-events-none"></div>
    <div class="absolute bottom-10 right-10 w-96 h-96 bg-emerald-500/10 rounded-full blur-[120px] pointer-events-none"></div>

    <!-- Ultra-Immersive Cyber Login Modal Background & Colors -->
    <div id="loginModal" class="fixed inset-0 z-50 flex items-center justify-center bg-[#010307]/95 backdrop-blur-3xl p-4 hidden">
        <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-tr from-cyan-600/20 via-teal-500/15 to-emerald-500/20 rounded-full blur-[160px] pointer-events-none animate-pulse"></div>
        <div class="absolute inset-0 bg-[radial-gradient(#06b6d4_1px,transparent_1px)] [background-size:32px_32px] opacity-[0.15] pointer-events-none"></div>

        <div class="glass-panel rounded-3xl w-full max-w-md p-8 shadow-[0_0_60px_rgba(6,182,212,0.3)] space-y-6 text-center border border-cyan-400/40 relative overflow-hidden z-10 bg-gradient-to-b from-[#0b1329]/90 to-[#030712]/95">
            <div class="absolute top-0 left-0 right-0 h-[4px] bg-gradient-to-r from-cyan-500 via-teal-300 to-emerald-400 shadow-[0_0_15px_#06b6d4]"></div>
            
            <div class="w-20 h-20 mx-auto rounded-2xl bg-gradient-to-br from-cyan-500/30 via-slate-900 to-emerald-500/30 border border-cyan-400/60 flex items-center justify-center text-cyan-300 text-3xl shadow-[0_0_30px_rgba(6,182,212,0.4)] transition-transform duration-300 hover:scale-110">
                <i class="fa-solid fa-fingerprint animate-pulse"></i>
            </div>

            <div>
                <h2 class="text-2xl font-black tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 via-teal-200 to-emerald-300 drop-shadow-[0_2px_10px_rgba(6,182,212,0.3)]">RATHA QUANT ACCESS</h2>
                <p class="text-xs text-cyan-400/70 mt-1.5 tracking-widest font-semibold uppercase">Secure Neural Gateway // Encrypted</p>
            </div>

            <form onsubmit="handleLogin(event)" class="space-y-4 text-left text-xs">
                <div>
                    <label class="block text-cyan-300 mb-1.5 font-extrabold uppercase tracking-widest text-[10px]">Access Password</label>
                    <div class="relative group">
                        <span class="absolute inset-y-0 left-0 pl-3.5 flex items-center text-cyan-400 group-focus-within:text-emerald-400 transition-colors"><i class="fa-solid fa-shield-keyhole"></i></span>
                        <input type="password" id="loginPassword" placeholder="Enter secure password..." required
                            class="w-full bg-[#030712] border border-cyan-900/60 rounded-xl pl-10 pr-4 py-3.5 text-cyan-100 placeholder:text-slate-600 focus:outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-500/30 hover:border-cyan-700/50 transition-all text-sm shadow-inner">
                    </div>
                </div>

                <div id="loginError" class="text-rose-400 text-[11px] font-bold bg-rose-500/10 border border-rose-500/30 p-2.5 rounded-lg hidden text-center shadow-sm"></div>

                <button type="submit" class="w-full py-4 rounded-xl bg-gradient-to-r from-cyan-500 via-teal-400 to-emerald-400 text-slate-950 font-black text-sm tracking-widest hover:opacity-95 hover:shadow-[0_0_35px_rgba(6,182,212,0.6)] hover:scale-[1.02] active:scale-[0.98] transition-all uppercase shadow-neon">
                    Authorize Terminal
                </button>
            </form>

            <div class="text-[10px] text-slate-400 tracking-widest pt-3 border-t border-cyan-950/80 font-bold">
                CORE PROTOCOL: ACTIVE // SECURE TUNNEL
            </div>
        </div>
    </div>

    <div class="container mx-auto px-4 py-8 max-w-6xl space-y-8 flex-grow relative z-10">
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center border-b border-slate-800/80 pb-6 gap-4">
            <div>
                <h1 class="text-2xl font-black text-cyan-400 tracking-wider flex items-center gap-3">
                    <i class="fa-solid fa-microchip text-emerald-400"></i> RATHA // QUANT TRADING DASHBOARD
                </h1>
                <p class="text-xs text-slate-400 mt-1">System Role: <span id="roleDisplay" class="text-emerald-400 font-bold uppercase tracking-widest px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">Loading...</span></p>
            </div>
            <button onclick="logout()" class="px-4 py-2.5 bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs rounded-xl hover:bg-rose-500/20 hover:border-rose-500/60 hover:shadow-rose-hover hover:scale-105 active:scale-95 transition-all flex items-center gap-2 font-bold shadow-lg">
                <i class="fa-solid fa-power-off"></i> TERMINATE SESSION
            </button>
        </div>

        <div class="glass-panel border-emerald-500/30 rounded-2xl p-6 shadow-neon-glow relative overflow-hidden group">
            <div class="absolute -right-6 -bottom-6 text-emerald-500/5 text-9xl font-black pointer-events-none transition-transform duration-500 group-hover:scale-110">
                $100
            </div>
            <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-4 gap-2">
                <div>
                    <h2 class="text-sm font-bold text-emerald-400 tracking-wider flex items-center gap-2">
                        <i class="fa-solid fa-bullseye text-cyan-400 transition-transform duration-300 group-hover:rotate-45"></i> MISSION: $10 TO $100 CHALLENGE
                    </h2>
                    <p class="text-xs text-slate-400 mt-0.5">Real-time database equity growth tracking objective.</p>
                </div>
                <div class="text-right">
                    <span id="missionProgressText" class="text-lg font-black text-cyan-400">$0.00 / $100.00</span>
                    <span id="missionPercentage" class="text-xs text-emerald-400 ml-2 font-bold">(0%)</span>
                </div>
            </div>
            <div class="w-full bg-cyber-950 rounded-full h-3.5 p-0.5 border border-slate-800">
                <div id="missionProgressBar" class="bg-gradient-to-r from-cyan-500 to-emerald-400 h-full rounded-full transition-all duration-500 shadow-neon" style="width: 0%;"></div>
            </div>
        </div>

        <div class="glass-panel rounded-2xl p-6 shadow-xl">
            <h2 class="text-sm font-bold text-slate-300 mb-4 tracking-wide flex items-center gap-2">
                <i class="fa-solid fa-wave-square text-cyan-400"></i> Equity Curve & Performance Metrics
            </h2>
            <div class="h-72 w-full">
                <canvas id="performanceChart"></canvas>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div id="adminPanel" class="glass-panel border-cyan-500/30 rounded-2xl p-6 shadow-xl hidden space-y-4">
                <h2 class="text-sm font-bold text-cyan-400 tracking-wide flex items-center gap-2">
                    <i class="fa-solid fa-square-plus"></i> Input Trade (Admin Control)
                </h2>
                <form onsubmit="addTrade(event)" class="space-y-3 text-xs">
                    <div>
                        <label class="block text-slate-400 mb-1 font-bold">Date</label>
                        <input type="date" id="tradeDate" required class="w-full bg-cyber-950 border border-slate-800 rounded-xl px-3 py-2.5 text-slate-100 focus:border-cyan-400 hover:border-slate-700 focus:outline-none transition-colors">
                    </div>
                    <div>
                        <label class="block text-slate-400 mb-1 font-bold">Asset Pair</label>
                        <input type="text" id="tradePair" placeholder="e.g. XAUUSD" required class="w-full bg-cyber-950 border border-slate-800 rounded-xl px-3 py-2.5 text-slate-100 focus:border-cyan-400 hover:border-slate-700 focus:outline-none transition-colors">
                    </div>
                    <div>
                        <label class="block text-slate-400 mb-1 font-bold">Execution Type</label>
                        <select id="tradeType" class="w-full bg-cyber-950 border border-slate-800 rounded-xl px-3 py-2.5 text-slate-100 focus:border-cyan-400 hover:border-slate-700 focus:outline-none transition-colors">
                            <option value="BUY">BUY</option>
                            <option value="SELL">SELL</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-slate-400 mb-1 font-bold">Net PnL ($)</label>
                        <input type="number" step="any" id="tradePnl" placeholder="e.g. 10.50 or -5" required class="w-full bg-cyber-950 border border-slate-800 rounded-xl px-3 py-2.5 text-slate-100 focus:border-cyan-400 hover:border-slate-700 focus:outline-none transition-colors">
                    </div>
                    <button type="submit" class="w-full py-3 bg-gradient-to-r from-cyan-500 to-emerald-400 text-cyber-950 font-extrabold rounded-xl hover:opacity-90 hover:shadow-neon-hover hover:scale-[1.02] active:scale-[0.98] transition-all tracking-wider shadow-neon">
                        EXECUTE & TELEGRAM ALERT
                    </button>
                </form>

                <!-- NEW: Test Telegram Bot Alert Button -->
                <div class="pt-3 border-t border-slate-800">
                    <button type="button" onclick="testTelegramBot()" class="w-full py-2.5 bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 font-bold rounded-xl hover:bg-cyan-500/20 hover:border-cyan-400 hover:shadow-neon transition-all flex items-center justify-center gap-2">
                        <i class="fa-brands fa-telegram text-cyan-400"></i> TEST TELEGRAM BOT
                    </button>
                    <div id="testTelegramStatus" class="text-[11px] text-center mt-2 hidden font-bold"></div>
                </div>
            </div>

            <div id="tableContainer" class="lg:col-span-3 glass-panel rounded-2xl p-6 shadow-xl overflow-x-auto">
                <h2 class="text-sm font-bold text-slate-300 mb-4 tracking-wide flex items-center gap-2">
                    <i class="fa-solid fa-database text-cyan-400"></i> Database Execution History Log
                </h2>
                <table class="w-full text-left text-xs whitespace-nowrap">
                    <thead>
                        <tr class="border-b border-slate-800 text-slate-400 font-bold">
                            <th class="pb-3 px-2">ID</th>
                            <th class="pb-3 px-2">Date</th>
                            <th class="pb-3 px-2">Pair</th>
                            <th class="pb-3 px-2">Type</th>
                            <th class="pb-3 px-2">PnL</th>
                            <th class="pb-3 px-2 text-right action-col">Action</th>
                        </tr>
                    </thead>
                    <tbody id="tradesTableBody" class="divide-y divide-slate-800/40"></tbody>
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
                    document.getElementById('loginModal').classList.add('hidden');
                    document.getElementById('roleDisplay').textContent = currentUserRole;
                    applyRolePermissions();
                    loadTrades();
                }
            } catch (err) { console.error('Auth error:', err); }
        }

        async function handleLogin(e) {
            e.preventDefault();
            const password = document.getElementById('loginPassword').value;
            const errorEl = document.getElementById('loginError');
            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
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
                    errorEl.textContent = data.message;
                    errorEl.classList.remove('hidden');
                }
            } catch (err) {
                errorEl.textContent = 'Connection error with database core.';
                errorEl.classList.remove('hidden');
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
                const chartLabels = [];
                const chartData = [];

                trades.forEach(t => {
                    cumulative += t.pnl;
                    chartLabels.push(t.date);
                    chartData.push(cumulative);

                    const tr = document.createElement('tr');
                    tr.className = 'hover:bg-cyan-500/5 hover:text-cyan-200 transition-all duration-200';
                    let actionHtml = '';
                    if (currentUserRole === 'admin') {
                        actionHtml = `<td class="py-3 px-2 text-right action-col">
                            <button onclick="deleteTrade(${t.id})" class="text-rose-400 hover:text-white hover:bg-rose-500 p-1.5 bg-rose-500/10 border border-rose-500/20 rounded-lg transition-all duration-200 hover:scale-110 shadow-sm"><i class="fa-solid fa-trash-can"></i></button>
                        </td>`;
                    }
                    tr.innerHTML = `
                        <td class="py-3 px-2 text-slate-500 font-mono">#${t.id}</td>
                        <td class="py-3 px-2 text-slate-300">${t.date}</td>
                        <td class="py-3 px-2 font-bold text-cyan-300">${t.pair}</td>
                        <td class="py-3 px-2"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${t.type === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'}">${t.type}</span></td>
                        <td class="py-3 px-2 font-bold ${t.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}">${t.pnl >= 0 ? '+' : ''}$${t.pnl.toFixed(2)}</td>
                        ${actionHtml}
                    `;
                    tbody.appendChild(tr);
                });
                updateMissionTracker(cumulative);
                renderChart(chartLabels, chartData);
            } catch (err) { console.error('Failed to load trades:', err); }
        }

        function updateMissionTracker(totalProfit) {
            const baseCapital = 10;
            const targetCapital = 100;
            const currentEquity = baseCapital + totalProfit;
            let percentage = ((currentEquity - baseCapital) / (targetCapital - baseCapital)) * 100;
            if (percentage < 0) percentage = 0;
            if (percentage > 100) percentage = 100;
            document.getElementById('missionProgressText').textContent = `$${currentEquity.toFixed(2)} / $${targetCapital.toFixed(2)}`;
            document.getElementById('missionPercentage').textContent = `(${percentage.toFixed(1)}%)`;
            document.getElementById('missionProgressBar').style.width = `${percentage}%`;
        }

        async function addTrade(e) {
            e.preventDefault();
            const date = document.getElementById('tradeDate').value;
            const pair = document.getElementById('tradePair').value;
            const type = document.getElementById('tradeType').value;
            const pnl = document.getElementById('tradePnl').value;
            try {
                const res = await fetch('/api/trades', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ date, pair, type, pnl })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    document.getElementById('tradePair').value = '';
                    document.getElementById('tradePnl').value = '';
                    loadTrades();
                }
            } catch (err) { console.error('Error adding trade:', err); }
        }

        async function deleteTrade(id) {
            if (!confirm('Are you sure you want to delete this database record?')) return;
            try {
                const res = await fetch(`/api/trades?id=${id}`, { method: 'DELETE' });
                const data = await res.json();
                if (data.status === 'success') loadTrades();
            } catch (err) { console.error('Error deleting trade:', err); }
        }

        async function testTelegramBot() {
            const statusEl = document.getElementById('testTelegramStatus');
            statusEl.textContent = "Sending test alert...";
            statusEl.className = "text-[11px] text-center mt-2 text-cyan-400 font-bold";
            statusEl.classList.remove('hidden');

            try {
                const res = await fetch('/api/test-telegram', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'success') {
                    statusEl.textContent = "✅ Telegram test alert sent successfully!";
                    statusEl.className = "text-[11px] text-center mt-2 text-emerald-400 font-bold";
                } else {
                    statusEl.textContent = "❌ Failed: " + (data.message || "Check Bot Token & Chat ID");
                    statusEl.className = "text-[11px] text-center mt-2 text-rose-400 font-bold";
                }
            } catch (err) {
                statusEl.textContent = "❌ Connection error testing telegram.";
                statusEl.className = "text-[11px] text-center mt-2 text-rose-400 font-bold";
            }
        }

        function renderChart(labels, data) {
            const ctx = document.getElementById('performanceChart').getContext('2d');
            if (performanceChart) performanceChart.destroy();
            const adjustedData = data.map(val => 10 + val);
            const chartLabels = ['Start', ...labels];
            const chartValues = [10, ...adjustedData];
            performanceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: chartLabels,
                    datasets: [{
                        label: 'Challenge Account Balance ($)',
                        data: chartValues,
                        borderColor: '#06b6d4',
                        backgroundColor: 'rgba(6, 182, 212, 0.12)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.35,
                        pointBackgroundColor: '#10b981',
                        pointBorderColor: '#06b6d4',
                        pointRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: '#94a3b8', font: { family: 'monospace', weight: 'bold' } } } },
                    scales: {
                        x: { ticks: { color: '#64748b' }, grid: { color: 'rgba(30, 41, 59, 0.4)' } },
                        y: { ticks: { color: '#64748b' }, grid: { color: 'rgba(30, 41, 59, 0.4)' } }
                    }
                }
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
    else:
        return jsonify({"status": "error", "message": "Invalid access password!"}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "success"})

@app.route("/api/auth-status", methods=["GET"])
def auth_status():
    role = session.get("role")
    if not role:
        return jsonify({"authenticated": False, "role": None})
    return jsonify({"authenticated": True, "role": role})

# NEW: Test Telegram Route Endpoint
@app.route("/api/test-telegram", methods=["POST"])
def test_telegram():
    if session.get("role") != "admin":
        return jsonify({"error": "Admin rights required."}), 403
    
    test_msg = "🧪 *RATHA QUANT SYSTEM*\n\n✅ Telegram Bot connection test successful! Ready for live trade execution alerts."
    success = send_telegram_alert(test_msg)
    
    if success:
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID configurations."}), 400

@app.route("/api/trades", methods=["GET", "POST", "DELETE"])
def handle_trades():
    if not session.get("role"):
        return jsonify({"error": "Unauthorized"}), 401
    
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
        return jsonify({"error": "Access denied. Admin rights required."}), 403

    if request.method == "POST":
        data = request.get_json()
        date = data.get("date")
        pair = data.get("pair", "").upper()
        t_type = data.get("type", "").upper()
        pnl = float(data.get("pnl", 0))

        if db_type == "postgres":
            cursor.execute("INSERT INTO trades (date, pair, type, pnl) VALUES (%s, %s, %s, %s) RETURNING id", (date, pair, t_type, pnl))
            new_id = cursor.fetchone()['id']
            conn.commit()
        else:
            cursor.execute("INSERT INTO trades (date, pair, type, pnl) VALUES (?, ?, ?, ?)", (date, pair, t_type, pnl))
            conn.commit()
            new_id = cursor.lastrowid
        
        conn.close()

        alert_msg = f"🚨 *NEW TRADE EXECUTED*\n\n📈 Pair: `{pair}`\n🔹 Type: `{t_type}`\n💰 PnL: `${pnl:.2f}`\n📅 Date: `{date}`"
        send_telegram_alert(alert_msg)

        return jsonify({"status": "success", "trade": {"id": new_id, "date": date, "pair": pair, "type": t_type, "pnl": pnl}})

    if request.method == "DELETE":
        trade_id = request.args.get("id", type=int)
        if db_type == "postgres":
            cursor.execute("DELETE FROM trades WHERE id = %s", (trade_id,))
        else:
            cursor.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
from flask import Flask, request, jsonify, session, render_template_string
import os
import requests
import psycopg2
import psycopg2.extras
import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "ratha_quant_secure_secret_2026")

ADMIN_PASSWORD = "Ratha123"
USER_PASSWORD = "user123"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8622254541:AAHOwR8hHnfjMrkz4y8udsEuC1jn49EHjII")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "6915043499")

def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram Alert Error: {e}")
        return False

# Database Connection Helper supporting Render PostgreSQL & SQLite Fallback
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://ratha_user:QNbnhmZFRbWKJJepa6oRIgjZq7XwTgGD@dpg-dad3caajnfac73e945r0-a/ratha")

def get_db_connection():
    if DATABASE_URL:
        try:
            conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
            return conn, "postgres"
        except Exception as e:
            print(f"PostgreSQL connection failed ({e}), falling back to SQLite...")
    
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
                    fontFamily: {
                        sans: ['Inter', 'sans-serif'],
                        mono: ['JetBrains Mono', 'monospace'],
                    },
                    boxShadow: {
                        'neon': '0 0 30px rgba(0, 240, 255, 0.4)',
                        'neon-glow': '0 0 35px rgba(16, 185, 129, 0.4)',
                        'gold-glow': '0 0 35px rgba(245, 158, 11, 0.4)',
                    }
                }
            }
        }
    </script>
    <style>
        body {
            background-color: #010308;
            position: relative;
            overflow-x: hidden;
            margin: 0;
            padding: 0;
        }

        .cyber-grid {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background-image: 
                linear-gradient(rgba(0, 240, 255, 0.06) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 240, 255, 0.06) 1px, transparent 1px);
            background-size: 60px 60px;
            will-change: transform;
            animation: gridMove 20s linear infinite;
            z-index: -3;
            pointer-events: none;
        }

        @keyframes gridMove {
            0% { transform: translate3d(0, 0, 0); }
            100% { transform: translate3d(60px, 60px, 0); }
        }

        .cyber-orb {
            position: fixed;
            border-radius: 50%;
            filter: blur(80px);
            z-index: -2;
            pointer-events: none;
            opacity: 0.5;
            will-change: transform, background-color;
            animation: orbFloat 12s ease-in-out infinite alternate, colorShift 20s linear infinite;
        }
        .orb-1 { width: 500px; height: 500px; top: -150px; left: -150px; }
        .orb-2 { width: 600px; height: 600px; bottom: -200px; right: -200px; animation-delay: -6s; }

        @keyframes orbFloat {
            0% { transform: translate3d(0px, 0px, 0px) scale(1); }
            50% { transform: translate3d(60px, 40px, 0px) scale(1.15); }
            100% { transform: translate3d(-40px, -50px, 0px) scale(0.95); }
        }

        @keyframes colorShift {
            0% { background: rgba(0, 240, 255, 0.3); }
            33% { background: rgba(16, 185, 129, 0.3); }
            66% { background: rgba(245, 158, 11, 0.3); }
            100% { background: rgba(0, 240, 255, 0.3); }
        }

        .laser-scan {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 4px;
            background: linear-gradient(to right, transparent, rgba(0, 240, 255, 0.7), transparent);
            box-shadow: 0 0 12px #00f0ff;
            will-change: top, opacity;
            animation: laserMove 8s ease-in-out infinite;
            z-index: 9999;
            pointer-events: none;
        }

        @keyframes laserMove {
            0% { top: 0%; opacity: 0.6; }
            50% { opacity: 0.2; }
            100% { top: 100%; opacity: 0.6; }
        }

        .glass-panel {
            background: rgba(3, 7, 18, 0.85);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(0, 240, 255, 0.25);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8);
            transition: border-color 0.3s ease, box-shadow 0.3s ease;
        }

        .glass-panel:hover {
            border-color: rgba(0, 240, 255, 0.5);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.9), 0 0 15px rgba(0, 240, 255, 0.15);
        }

        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #000000; }
        ::-webkit-scrollbar-thumb { background: #00f0ff; border-radius: 3px; }
    </style>
</head>
<body class="text-slate-200 font-sans min-h-screen flex flex-col selection:bg-cyan-400 selection:text-black">
    
    <div class="cyber-grid"></div>
    <div class="cyber-orb orb-1"></div>
    <div class="cyber-orb orb-2"></div>
    <div class="laser-scan"></div>

    <div class="bg-black/90 backdrop-blur-md border-b border-cyan-500/30 py-2 px-4 text-[11px] font-mono flex justify-between items-center z-40 text-cyan-400 shadow-[0_2px_15px_rgba(0,240,255,0.2)]">
        <div class="flex items-center gap-6 overflow-x-auto whitespace-nowrap">
            <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping"></span><strong class="text-white">AI-UNIT // XAUUSD:</strong> 2,485.40 <span class="text-emerald-400">+0.42%</span></span>
            <span class="flex items-center gap-1.5"><strong class="text-white">EURUSD:</strong> 1.0924 <span class="text-rose-400">-0.12%</span></span>
            <span class="flex items-center gap-1.5"><strong class="text-white">BTCUSD:</strong> 61,420.00 <span class="text-emerald-400">+1.85%</span></span>
        </div>
        <div class="hidden md:flex items-center gap-4 text-cyan-400">
            <span><i class="fa-solid fa-cloud mr-1"></i> RENDER CLOUD: ONLINE</span>
            <span><i class="fa-solid fa-database mr-1"></i> POSTGRESQL: ACTIVE</span>
        </div>
    </div>

    <!-- Login Modal -->
    <div id="loginModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-md p-4 hidden">
        <div class="glass-panel rounded-2xl w-full max-w-md p-8 space-y-6 relative z-10 border border-cyan-500/60 shadow-neon">
            <div class="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-cyan-400 via-emerald-400 to-amber-500"></div>
            
            <div class="w-16 h-16 mx-auto rounded-xl bg-gradient-to-br from-cyan-500/20 to-black border border-cyan-500/60 flex items-center justify-center text-cyan-400 text-3xl shadow-neon">
                <i class="fa-solid fa-robot"></i>
            </div>

            <div class="text-center">
                <h2 class="text-xl font-extrabold tracking-wider text-white font-mono">ROBOTIC QUANT TERMINAL</h2>
                <p class="text-xs text-cyan-400/80 mt-1 font-mono uppercase tracking-widest">AI Security Authorization Required</p>
            </div>

            <form onsubmit="handleLogin(event)" class="space-y-4 text-xs font-mono">
                <div>
                    <label class="block text-cyan-400/70 mb-2 uppercase font-semibold">Security Protocol Key</label>
                    <div class="relative">
                        <span class="absolute inset-y-0 left-0 pl-3.5 flex items-center text-cyan-500"><i class="fa-solid fa-terminal"></i></span>
                        <input type="password" id="loginPassword" placeholder="Enter key (admin123 / user123)" required
                            class="w-full bg-black/90 border border-cyan-500/40 rounded-xl pl-10 pr-4 py-3 text-cyan-200 placeholder:text-slate-600 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 transition-all text-xs font-mono">
                    </div>
                </div>

                <div id="loginError" class="text-rose-400 text-[11px] font-bold bg-rose-500/10 border border-rose-500/20 p-2.5 rounded-lg hidden text-center"></div>

                <button type="submit" class="w-full py-3.5 rounded-xl bg-gradient-to-r from-cyan-500 to-emerald-400 text-black font-extrabold text-xs tracking-wider uppercase hover:opacity-90 hover:shadow-neon transition-all">
                    Initialize Terminal
                </button>
            </form>
            
            <div class="text-[10px] text-center text-slate-400 font-mono">
                System Hint: Use <span class="text-cyan-400 font-bold">admin123</span> (Full Control) or <span class="text-slate-200 font-bold">user123</span> (View Only).
            </div>
        </div>
    </div>

    <!-- Main Container -->
    <div class="container mx-auto px-4 py-6 max-w-7xl space-y-6 flex-grow relative z-10">
        
        <!-- Header Section -->
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center glass-panel rounded-2xl p-6 gap-4 border-cyan-500/40">
            <div class="flex items-center gap-4">
                <div class="w-12 h-12 rounded-xl bg-gradient-to-tr from-cyan-500/20 to-black border border-cyan-500/50 flex items-center justify-center text-cyan-400 text-xl shadow-neon">
                    <i class="fa-solid fa-microchip"></i>
                </div>
                <div>
                    <h1 class="text-xl font-bold tracking-tight text-white flex items-center gap-2 font-mono">
                        RATHA // CYBER TRADING COMMAND
                    </h1>
                    <p class="text-xs text-slate-400 font-mono mt-0.5">Active Unit Role: <span id="roleDisplay" class="text-cyan-400 font-bold uppercase px-2 py-0.5 bg-cyan-500/10 border border-cyan-500/30 rounded-md">Loading...</span></p>
                </div>
            </div>
            <button onclick="logout()" class="px-4 py-2.5 bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-mono rounded-xl hover:bg-rose-500/20 hover:border-rose-500/50 transition-all flex items-center gap-2">
                <i class="fa-solid fa-power-off"></i> SHUTDOWN SESSION
            </button>
        </div>

        <!-- Mission Challenge Tracker Banner -->
        <div class="glass-panel border-amber-500/50 rounded-2xl p-6 shadow-gold-glow relative overflow-hidden group">
            <div class="absolute -right-4 -bottom-4 text-amber-500/10 text-9xl font-black font-mono pointer-events-none select-none">
                $100
            </div>
            <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-4 gap-2 relative z-10">
                <div>
                    <h2 class="text-sm font-bold text-amber-400 tracking-wider flex items-center gap-2 font-mono">
                        <i class="fa-solid fa-bullseye text-cyan-400"></i> ROBOTIC MISSION: $10 TO $100 COMPOUNDING PROTOCOL
                    </h2>
                    <p class="text-xs text-slate-400 mt-0.5">Automated equity growth telemetry benchmarked against algorithmic risk matrices.</p>
                </div>
                <div class="text-right font-mono">
                    <span id="missionProgressText" class="text-lg font-black text-white">$0.00 / $100.00</span>
                    <span id="missionPercentage" class="text-xs text-amber-400 ml-2 font-bold">(0%)</span>
                </div>
            </div>
            <div class="w-full bg-black rounded-full h-3 p-0.5 border border-white/10 relative z-10">
                <div id="missionProgressBar" class="bg-gradient-to-r from-amber-500 via-emerald-400 to-cyan-400 h-full rounded-full transition-all duration-700 shadow-neon-glow" style="width: 0%;"></div>
            </div>
        </div>

        <!-- Risk Management & Rules Matrix Section -->
        <div class="glass-panel rounded-2xl p-6 border-cyan-500/40">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-sm font-bold text-cyan-400 tracking-wide flex items-center gap-2 font-mono">
                    <i class="fa-solid fa-shield-cat text-cyan-400"></i> QUANTITATIVE RISK & TRADING RULES PROTOCOL
                </h2>
                <span class="text-xs text-cyan-400/80 font-mono">Status: Enforced</span>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 font-mono">
                <!-- Rule 1 -->
                <div class="bg-black/80 border border-cyan-500/30 rounded-xl p-4 flex flex-col justify-between hover:border-cyan-400 transition-colors">
                    <div>
                        <div class="flex justify-between items-center mb-2">
                            <span class="text-[10px] text-cyan-400 bg-cyan-500/10 border border-cyan-500/30 px-2 py-0.5 rounded font-bold">RULE #01</span>
                            <i class="fa-solid fa-wallet text-amber-400"></i>
                        </div>
                        <h3 class="text-xs font-bold text-white mb-1">Daily Target / Limit</h3>
                        <p class="text-[11px] text-slate-400 leading-relaxed">Target profit or drawdown limit restricted strictly to <strong class="text-emerald-400">$5 to $10</strong> per day.</p>
                    </div>
                    <div class="mt-4 pt-2 border-t border-white/15 flex items-center justify-between text-[10px]">
                        <span class="text-slate-400">State:</span>
                        <span class="text-emerald-400 font-bold"><i class="fa-solid fa-circle-check mr-1"></i> ACTIVE</span>
                    </div>
                </div>

                <!-- Rule 2 -->
                <div class="bg-black/80 border border-cyan-500/30 rounded-xl p-4 flex flex-col justify-between hover:border-cyan-400 transition-colors">
                    <div>
                        <div class="flex justify-between items-center mb-2">
                            <span class="text-[10px] text-rose-400 bg-rose-500/10 border border-rose-500/30 px-2 py-0.5 rounded font-bold">RULE #02</span>
                            <i class="fa-solid fa-ban text-rose-400"></i>
                        </div>
                        <h3 class="text-xs font-bold text-white mb-1">Zero FOMO Policy</h3>
                        <p class="text-[11px] text-slate-400 leading-relaxed">No chasing impulsive market moves. Wait for clean structure confirmation.</p>
                    </div>
                    <div class="mt-4 pt-2 border-t border-white/15 flex items-center justify-between text-[10px]">
                        <span class="text-slate-400">State:</span>
                        <span class="text-emerald-400 font-bold"><i class="fa-solid fa-circle-check mr-1"></i> ACTIVE</span>
                    </div>
                </div>

                <!-- Rule 3 -->
                <div class="bg-black/80 border border-cyan-500/30 rounded-xl p-4 flex flex-col justify-between hover:border-cyan-400 transition-colors">
                    <div>
                        <div class="flex justify-between items-center mb-2">
                            <span class="text-[10px] text-cyan-400 bg-cyan-500/10 border border-cyan-500/30 px-2 py-0.5 rounded font-bold">RULE #03</span>
                            <i class="fa-solid fa-layer-group text-cyan-400"></i>
                        </div>
                        <h3 class="text-xs font-bold text-white mb-1">HTF 4H + Entry 5M</h3>
                        <p class="text-[11px] text-slate-400 leading-relaxed">Analyze primary bias on <strong class="text-cyan-300">4-Hour (HTF)</strong> and execute precision entries on <strong class="text-cyan-300">5-Minute (LTF)</strong>.</p>
                    </div>
                    <div class="mt-4 pt-2 border-t border-white/15 flex items-center justify-between text-[10px]">
                        <span class="text-slate-400">Model:</span>
                        <span class="text-cyan-400 font-bold">4H / 5M SMC</span>
                    </div>
                </div>

                <!-- Rule 4 -->
                <div class="bg-black/80 border border-cyan-500/30 rounded-xl p-4 flex flex-col justify-between hover:border-cyan-400 transition-colors">
                    <div>
                        <div class="flex justify-between items-center mb-2">
                            <span class="text-[10px] text-cyan-400 bg-cyan-500/10 border border-cyan-500/30 px-2 py-0.5 rounded font-bold">RULE #04</span>
                            <i class="fa-solid fa-clock text-cyan-400"></i>
                        </div>
                        <h3 class="text-xs font-bold text-white mb-1">HTF 1H + Entry 1M</h3>
                        <p class="text-[11px] text-slate-400 leading-relaxed">Analyze primary bias on <strong class="text-cyan-300">1-Hour (HTF)</strong> and execute rapid scalping entries on <strong class="text-cyan-300">1-Minute (LTF)</strong>.</p>
                    </div>
                    <div class="mt-4 pt-2 border-t border-white/15 flex items-center justify-between text-[10px]">
                        <span class="text-slate-400">Model:</span>
                        <span class="text-cyan-400 font-bold">1H / 1M Scalp</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Performance Chart Section -->
        <div class="glass-panel rounded-2xl p-6 border-cyan-500/30">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-sm font-bold text-slate-200 tracking-wide flex items-center gap-2 font-mono">
                    <i class="fa-solid fa-chart-line text-cyan-400"></i> Algorithmic Equity Telemetry Curve
                </h2>
                <div class="flex gap-2 text-xs font-mono text-cyan-400/80">
                    <span class="px-2.5 py-1 bg-black/90 border border-cyan-500/40 rounded-lg">Render Cloud Database</span>
                </div>
            </div>
            <div class="h-72 w-full">
                <canvas id="performanceChart"></canvas>
            </div>
        </div>

        <!-- Interactive Grid: Input Controls & Trade Ledger -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            <!-- Admin Control Panel -->
            <div id="adminPanel" class="glass-panel border-cyan-500/50 rounded-2xl p-6 hidden space-y-5">
                <h2 class="text-sm font-bold text-cyan-400 tracking-wide flex items-center gap-2 font-mono">
                    <i class="fa-solid fa-terminal"></i> Execute Neural Trade Order
                </h2>
                <form onsubmit="addTrade(event)" class="space-y-3.5 text-xs font-mono">
                    <div>
                        <label class="block text-cyan-400/70 mb-1 font-semibold">Timestamp Date</label>
                        <input type="date" id="tradeDate" required class="w-full bg-black/90 border border-cyan-500/40 rounded-xl px-3 py-2.5 text-cyan-200 focus:border-cyan-400 focus:outline-none transition-colors">
                    </div>
                    <div>
                        <label class="block text-cyan-400/70 mb-1 font-semibold">Asset Pair</label>
                        <input type="text" id="tradePair" placeholder="e.g. XAUUSD" required class="w-full bg-black/90 border border-cyan-500/40 rounded-xl px-3 py-2.5 text-cyan-200 focus:border-cyan-400 focus:outline-none transition-colors uppercase">
                    </div>
                    <div>
                        <label class="block text-cyan-400/70 mb-1 font-semibold">Execution Vector</label>
                        <select id="tradeType" class="w-full bg-black/90 border border-cyan-500/40 rounded-xl px-3 py-2.5 text-cyan-200 focus:border-cyan-400 focus:outline-none transition-colors">
                            <option value="BUY">BUY (LONG)</option>
                            <option value="SELL">SELL (SHORT)</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-cyan-400/70 mb-1 font-semibold">Net PnL ($)</label>
                        <input type="number" step="any" id="tradePnl" placeholder="e.g. 15.50 or -4.20" required class="w-full bg-black/90 border border-cyan-500/40 rounded-xl px-3 py-2.5 text-cyan-200 focus:border-cyan-400 focus:outline-none transition-colors">
                    </div>
                    <button type="submit" class="w-full py-3 bg-gradient-to-r from-cyan-500 to-emerald-400 text-black font-extrabold rounded-xl hover:opacity-90 hover:shadow-neon transition-all tracking-wider uppercase">
                        Transmit & Broadcast Telegram
                    </button>
                </form>

                <div class="pt-4 border-t border-cyan-500/30">
                    <button type="button" onclick="testTelegramBot()" class="w-full py-2.5 bg-cyan-500/10 border border-cyan-500/40 text-cyan-300 font-bold font-mono rounded-xl hover:bg-cyan-500/20 transition-all flex items-center justify-center gap-2 text-xs">
                        <i class="fa-brands fa-telegram text-cyan-400"></i> TEST TELEGRAM BOT LINK
                    </button>
                    <div id="testTelegramStatus" class="text-[11px] text-center mt-2 hidden font-mono font-bold"></div>
                </div>
            </div>

            <!-- Database Execution History Log Table -->
            <div id="tableContainer" class="lg:col-span-3 glass-panel rounded-2xl p-6 overflow-x-auto border-cyan-500/30">
                <div class="flex justify-between items-center mb-4">
                    <h2 class="text-sm font-bold text-slate-200 tracking-wide flex items-center gap-2 font-mono">
                        <i class="fa-solid fa-database text-cyan-400"></i> Render Database Execution Log
                    </h2>
                    <span class="text-xs text-cyan-400/80 font-mono">Storage: PostgreSQL Cloud</span>
                </div>
                <table class="w-full text-left text-xs font-mono whitespace-nowrap">
                    <thead>
                        <tr class="border-b border-cyan-500/40 text-cyan-400 font-bold">
                            <th class="pb-3 px-3">ID</th>
                            <th class="pb-3 px-3">Date</th>
                            <th class="pb-3 px-3">Pair</th>
                            <th class="pb-3 px-3">Vector</th>
                            <th class="pb-3 px-3">Net PnL</th>
                            <th class="pb-3 px-3 text-right action-col">Action</th>
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
                    tr.className = 'hover:bg-cyan-500/15 transition-colors duration-150';
                    let actionHtml = '';
                    if (currentUserRole === 'admin') {
                        actionHtml = `<td class="py-3 px-3 text-right action-col">
                            <button onclick="deleteTrade(${t.id})" class="text-rose-400 hover:text-white hover:bg-rose-500 p-1.5 bg-rose-500/10 border border-rose-500/30 rounded-lg transition-all"><i class="fa-solid fa-trash-can"></i></button>
                        </td>`;
                    }
                    tr.innerHTML = `
                        <td class="py-3 px-3 text-cyan-400/60">#${t.id}</td>
                        <td class="py-3 px-3 text-slate-300">${t.date}</td>
                        <td class="py-3 px-3 font-bold text-cyan-300">${t.pair}</td>
                        <td class="py-3 px-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${t.type === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'}">${t.type}</span></td>
                        <td class="py-3 px-3 font-bold ${t.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}">${t.pnl >= 0 ? '+' : ''}$${t.pnl.toFixed(2)}</td>
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
            if (!confirm('Are you sure you want to purge this database record?')) return;
            try {
                const res = await fetch(`/api/trades?id=${id}`, { method: 'DELETE' });
                const data = await res.json();
                if (data.status === 'success') loadTrades();
            } catch (err) { console.error('Error deleting trade:', err); }
        }

        async function testTelegramBot() {
            const statusEl = document.getElementById('testTelegramStatus');
            statusEl.textContent = "Transmitting neural test alert...";
            statusEl.className = "text-[11px] text-center mt-2 text-cyan-400 font-bold font-mono";
            statusEl.classList.remove('hidden');

            try {
                const res = await fetch('/api/test-telegram', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'success') {
                    statusEl.textContent = "✅ Telegram neural alert broadcasted successfully!";
                    statusEl.className = "text-[11px] text-center mt-2 text-emerald-400 font-bold font-mono";
                } else {
                    statusEl.textContent = "❌ Failed: " + (data.message || "Check Bot Token & Chat ID");
                    statusEl.className = "text-[11px] text-center mt-2 text-rose-400 font-bold font-mono";
                }
            } catch (err) {
                statusEl.textContent = "❌ Connection error linking telegram.";
                statusEl.className = "text-[11px] text-center mt-2 text-rose-400 font-bold font-mono";
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
                        label: 'Neural Balance Curve ($)',
                        data: chartValues,
                        borderColor: '#00f0ff',
                        backgroundColor: 'rgba(0, 240, 255, 0.1)',
                        borderWidth: 2.5,
                        fill: true,
                        tension: 0.3,
                        pointBackgroundColor: '#10b981',
                        pointBorderColor: '#00f0ff',
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { 
                        legend: { labels: { color: '#00f0ff', font: { family: 'JetBrains Mono', weight: 'bold', size: 11 } } } 
                    },
                    scales: {
                        x: { ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 10 } }, grid: { color: 'rgba(0, 240, 255, 0.05)' } },
                        y: { ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 10 } }, grid: { color: 'rgba(0, 240, 255, 0.05)' } }
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
        return jsonify({"status": "error", "message": "Invalid security protocol key!"}), 401

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

@app.route("/api/test-telegram", methods=["POST"])
def test_telegram():
    if session.get("role") != "admin":
        return jsonify({"error": "Admin rights required."}), 403
    
    test_msg = "🤖 *RATHA RENDER QUANT SYSTEM*\n\n✅ Telegram neural link established! Ready for live trade execution broadcasts."
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

        alert_msg = f"🤖 *NEW NEURAL TRADE EXECUTED*\n\n📈 Pair: `{pair}`\n🔹 Vector: `{t_type}`\n💰 Net PnL: `${pnl:.2f}`\n📅 Timestamp: `{date}`"
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
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

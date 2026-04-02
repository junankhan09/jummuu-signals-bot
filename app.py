import os
import time
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta

load_dotenv()

app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
app.config['DEBUG'] = os.getenv('DEBUG', 'False').lower() == 'true'

QUOTEX_API_BASE = os.getenv('QUOTEX_API_BASE', 'https://quotex-api.jummuubot.workers.dev/?pairs=')

# ALL YOUR PAIRS
PAIR_MAP = {
    'USDBDT_otc': 'USD/BDT (OTC)',
    'USDBRL_otc': 'BRL/USD (OTC)',
    'USDPKR_otc': 'USD/PKR (OTC)',
    'USDINR_otc': 'USD/INR (OTC)',
    'USDARS_otc': 'USD/ARS (OTC)',
    'USDPHP_otc': 'USD/PHP (OTC)',
    'USDMXN_otc': 'USD/MXN (OTC)',
    'USDCOP_otc': 'USD/COP (OTC)',
    'USDEGP_otc': 'USD/EGP (OTC)',
    'USDTRY_otc': 'USD/TRY (OTC)',
    'USDDZD_otc': 'USD/DZD (OTC)',
    'USDIDR_otc': 'USD/IDR (OTC)',
    'USDZAR_otc': 'USD/ZAR (OTC)',
    'USDNGN_otc': 'USD/NGN (OTC)',
}


def get_current_bd_time():
    """Get current Bangladesh time (UTC+6)"""
    return datetime.utcnow() + timedelta(hours=6)


def get_next_signal(pair):
    """Get the NEXT upcoming signal from API based on current BD time"""
    api_url = f"{QUOTEX_API_BASE}{pair}"

    try:
        response = requests.get(api_url, timeout=10)
        data = response.json()

        if data.get('status') != 'success' or not data.get('signals'):
            print(f"API error for {pair}")
            return None

        signals = data['signals']
        current_time = get_current_bd_time()
        current_minutes = current_time.hour * 60 + current_time.minute

        print(f"Current BD Time: {current_time.strftime('%H:%M')} (minutes: {current_minutes})")

        # Find all future signals (after current time)
        future_signals = []
        for sig in signals:
            if 'time' in sig:
                try:
                    h, m = map(int, sig['time'].split(':'))
                    sig_minutes = h * 60 + m
                    if sig_minutes > current_minutes:
                        future_signals.append({
                            'signal': sig,
                            'minutes': sig_minutes,
                            'time': sig['time']
                        })
                except:
                    continue

        # Sort by time
        future_signals.sort(key=lambda x: x['minutes'])

        if future_signals:
            next_sig = future_signals[0]['signal']
            print(f"Next signal: {future_signals[0]['time']} - {next_sig.get('direction')}")
            return next_sig

        # If no future signals today, return first of tomorrow
        if signals:
            first_sig = signals[0]
            print(f"No more today, showing first tomorrow: {first_sig.get('time')}")
            return first_sig

        return None

    except Exception as e:
        print(f"API Error: {e}")
        return None


@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@app.route('/health')
def health():
    """Health check endpoint"""
    current = get_current_bd_time()
    return jsonify({
        'status': 'ok',
        'current_time': current.strftime('%H:%M:%S'),
        'pairs': len(PAIR_MAP),
        'timezone': 'UTC+6 (Bangladesh Time)'
    })


@app.route('/api/generate-signal', methods=['POST'])
def generate_signal():
    """Get next real signal from API"""
    try:
        data = request.get_json()
        pair = data.get('pair')

        if not pair:
            return jsonify({'status': 'error', 'message': 'No pair selected'}), 400

        # Get next signal from API
        signal = get_next_signal(pair)

        if not signal:
            return jsonify({'status': 'error', 'message': 'No signals available'}), 404

        current = get_current_bd_time()

        response = jsonify({
            'status': 'success',
            'signal': {
                'time': signal.get('time', '--:--'),
                'direction': signal.get('direction', 'CALL'),
                'duration': signal.get('duration', 'M1'),
                'martingale': signal.get('martingale', 'MG1'),
                'accuracy': signal.get('accuracy', '--'),
                'pair': PAIR_MAP.get(pair, pair.replace('_otc', '').replace('_', '/'))
            },
            'current_time': current.strftime('%H:%M')
        })

        # Prevent any caching
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

        return response

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/status')
def status():
    """API status endpoint"""
    current = get_current_bd_time()
    current_min = current.hour * 60 + current.minute

    # Test API connection
    api_connected = False
    signals_count = 0
    try:
        r = requests.get(f"{QUOTEX_API_BASE}USDBDT_otc", timeout=5)
        if r.status_code == 200:
            api_connected = True
            signals_count = len(r.json().get('signals', []))
    except:
        pass

    return jsonify({
        'status': 'running',
        'current_time': current.strftime('%H:%M:%S'),
        'current_minutes': current_min,
        'api_connected': api_connected,
        'signals_count': signals_count,
        'pairs': len(PAIR_MAP)
    })


@app.route('/api/pairs')
def get_pairs():
    """Return all trading pairs"""
    return jsonify({
        'status': 'success',
        'pairs': PAIR_MAP,
        'count': len(PAIR_MAP)
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    current = get_current_bd_time()

    print("=" * 60)
    print("🚀 QUOTEX SIGNAL BOT - READY")
    print("=" * 60)
    print(f"Current BD Time: {current.strftime('%H:%M:%S')}")
    print(f"Pairs Loaded: {len(PAIR_MAP)}")
    print(f"API Endpoint: {QUOTEX_API_BASE}")
    print("=" * 60)

    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
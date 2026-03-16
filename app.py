import os
import random
import time
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
import requests
from functools import wraps

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
app.config['DEBUG'] = os.getenv('DEBUG', 'False').lower() == 'true'

# API Base URL (hidden in backend)
QUOTEX_API_BASE = 'https://quotex-api.jummuubot.workers.dev/?pairs='

# Pair mapping (same as frontend but hidden in backend)
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


def get_current_time_in_minutes():
    """Get current time in minutes since midnight"""
    from datetime import datetime
    now = datetime.now()
    return now.hour * 60 + now.minute


def find_next_signal(signals):
    """Find the next signal based on current time"""
    if not signals or len(signals) == 0:
        return None

    current_minutes = get_current_time_in_minutes()

    signals_with_time = []
    for sig in signals:
        try:
            hours, minutes = map(int, sig['time'].split(':'))
            signal_minutes = hours * 60 + minutes
            signals_with_time.append({**sig, 'signal_minutes': signal_minutes})
        except (ValueError, KeyError):
            continue

    signals_with_time.sort(key=lambda x: x['signal_minutes'])

    # Find next signal
    next_signal = None
    for sig in signals_with_time:
        if sig['signal_minutes'] >= current_minutes:
            next_signal = sig
            break

    # If no future signal, take the first one (next day)
    if not next_signal and signals_with_time:
        next_signal = signals_with_time[0]

    return next_signal


@app.route('/')
def index():
    """Home page route"""
    return render_template('index.html')


@app.route('/api/generate-signal', methods=['POST'])
def generate_signal():
    """
    API endpoint to generate signal
    This contains the hidden logic for delay and API fetching
    """
    try:
        data = request.get_json()
        pair = data.get('pair')

        if not pair:
            return jsonify({
                'status': 'error',
                'message': 'Please select a market pair'
            }), 400

        # HIDDEN LOGIC: Random delay between 6-10 seconds
        # This happens on the server, invisible to client
        delay_time = random.uniform(6, 10)
        time.sleep(delay_time)

        # HIDDEN LOGIC: Fetch from external API
        api_url = f"{QUOTEX_API_BASE}{pair}"

        try:
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            api_data = response.json()

            if api_data.get('status') != 'success' or not api_data.get('signals'):
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid API response'
                }), 500

            # Find next signal
            next_signal = find_next_signal(api_data['signals'])

            if not next_signal:
                return jsonify({
                    'status': 'error',
                    'message': 'No upcoming signals found'
                }), 404

            # Format the response (clean data for frontend)
            return jsonify({
                'status': 'success',
                'signal': {
                    'time': next_signal.get('time', '--:--'),
                    'direction': next_signal.get('direction', 'CALL'),
                    'duration': next_signal.get('duration', 'M1'),
                    'martingale': next_signal.get('martingale', 'MG1'),
                    'accuracy': next_signal.get('accuracy', '--'),
                    'pair': PAIR_MAP.get(pair, pair.replace('_otc', '').replace('_', '/'))
                }
            })

        except requests.RequestException as e:
            return jsonify({
                'status': 'error',
                'message': 'Failed to fetch signal from API'
            }), 500

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Server error occurred'
        }), 500


@app.route('/api/status')
def status():
    """API endpoint to check application status"""
    return jsonify({
        'status': 'running',
        'environment': os.getenv('FLASK_ENV', 'production')
    })


if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])
from flask import Flask, render_template, jsonify, request
import os
import sys

# Agregar el directorio raíz al path de Python
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import config
from models.database import init_db
from models.settings_model import (
    get_settings, update_settings, update_bot_status, 
    get_db_trade_history, get_active_symbols, add_active_symbol, remove_active_symbol,
    update_active_symbol_config, update_all_active_symbols_config
)
from controllers.mt5_controller import MT5Controller
from controllers.main_controller import MainController

# Inicializar la base de datos
init_db()

app = Flask(
    __name__, 
    template_folder=os.path.join(config.BASE_DIR, 'views', 'templates'),
    static_folder=os.path.join(config.BASE_DIR, 'views', 'static')
)
app.config.from_object('config')

# Inicializar controladores de forma global
mt5_ctrl = MT5Controller()
main_ctrl = MainController()

# Si la base de datos dice que el bot debe estar encendido al iniciar, lo encendemos
settings = get_settings()
if settings and settings['run_bot'] == 1:
    main_ctrl.start_bot()

# ==========================================
# RUTAS WEB
# ==========================================

@app.route('/')
def index():
    """Renderiza el dashboard principal."""
    # Obtener configuración actual de la DB
    current_settings = get_settings()
    # Lista de símbolos disponibles
    symbols = mt5_ctrl.get_symbols()
    
    return render_template(
        'dashboard.html', 
        settings=current_settings,
        symbols=symbols
    )

# ==========================================
# ENDPOINTS REST API
# ==========================================

@app.route('/api/status', methods=['GET'])
def get_status():
    """Retorna el estado de la cuenta, posiciones abiertas e historial del bot."""
    # Sincronizar info de cuenta y refrescar precios
    account = mt5_ctrl.get_account_info()
    positions = mt5_ctrl.get_open_positions()
    history = get_db_trade_history(15)
    
    current_settings = get_settings()
    active_symbols = get_active_symbols()
    
    # Enriquecer activos activos con sus precios actuales en vivo
    active_symbols_with_prices = []
    for item in active_symbols:
        item_dict = dict(item)
        item_dict['price'] = mt5_ctrl.get_last_price(item['symbol'])
        # Verificar si hay posiciones abiertas para este símbolo específico
        has_pos = any(p['symbol'] == item['symbol'] for p in positions)
        item_dict['has_position'] = has_pos
        active_symbols_with_prices.append(item_dict)
        
    all_broker_symbols = mt5_ctrl.get_symbols()
    
    # Obtener precio del primer activo activo para el KPI del precio superior o EURUSD por defecto
    default_kpi_symbol = active_symbols[0]['symbol'] if active_symbols else (current_settings['symbol'] if current_settings else 'EURUSD')
    default_kpi_price = mt5_ctrl.get_last_price(default_kpi_symbol)
    
    return jsonify({
        'bot_status': {
            'running': main_ctrl.running,
            'message': main_ctrl.status_message,
            'active_strategy': current_settings['active_strategy'] if current_settings else 'N/A',
            'symbol': default_kpi_symbol,
            'price': default_kpi_price
        },
        'account': account,
        'positions': positions,
        'history': history,
        'active_symbols': active_symbols_with_prices,
        'broker_symbols': all_broker_symbols
    })

@app.route('/api/settings', methods=['POST'])
def save_settings():
    """Guarda la configuración del bot enviada desde el panel."""
    data = request.json
    strategy = data.get('strategy')
    risk_type = data.get('risk_type')
    entry_size = float(data.get('entry_size', 0.01))
    symbol = data.get('symbol')
    
    if not strategy or not risk_type or not symbol:
        return jsonify({'success': False, 'message': 'Faltan parámetros requeridos'}), 400
        
    update_settings(strategy, risk_type, entry_size, symbol)
    
    # Si el bot real está encendido, asegurar que cambie de símbolo en MT5
    if not mt5_ctrl.mock_mode:
        import MetaTrader5 as mt5_lib
        mt5_lib.symbol_select(symbol, True)
        
    return jsonify({
        'success': True, 
        'message': 'Configuración general guardada.',
        'settings': {
            'strategy': strategy,
            'risk_type': risk_type,
            'entry_size': entry_size,
            'symbol': symbol
        }
    })

@app.route('/api/active_symbols/add', methods=['POST'])
def add_symbol_to_trade():
    """Agrega un activo a la lista de operación automática."""
    data = request.json
    symbol = data.get('symbol')
    if not symbol:
        return jsonify({'success': False, 'message': 'Símbolo requerido'}), 400
        
    # Registrar en base de datos
    success = add_active_symbol(symbol)
    
    # Asegurar que esté visible en MT5
    if not mt5_ctrl.mock_mode:
        import MetaTrader5 as mt5_lib
        mt5_lib.symbol_select(symbol, True)
    else:
        # En modo simulación, inicializar si es nuevo
        if symbol not in mt5_ctrl.mock_symbols:
            mt5_ctrl.mock_symbols.append(symbol)
            import random
            mt5_ctrl.mock_prices[symbol] = round(random.uniform(50.0, 1500.0), 4)
            mt5_ctrl.price_histories[symbol] = mt5_ctrl._generate_initial_history(symbol, 100)
            
    if success:
        return jsonify({'success': True, 'message': f'Activo {symbol} configurado para trading.'})
    else:
        return jsonify({'success': False, 'message': f'El activo {symbol} ya está en tu lista de operación.'})

@app.route('/api/active_symbols/remove', methods=['POST'])
def remove_symbol_from_trade():
    """Elimina un activo de la lista de operación automática."""
    data = request.json
    symbol = data.get('symbol')
    if not symbol:
        return jsonify({'success': False, 'message': 'Símbolo requerido'}), 400
        
    success = remove_active_symbol(symbol)
    if success:
        return jsonify({'success': True, 'message': f'Activo {symbol} removido de la lista.'})
    else:
        return jsonify({'success': False, 'message': 'No se pudo remover el activo.'})

@app.route('/api/active_symbols/update', methods=['POST'])
def update_symbol_config_route():
    """Actualiza la estrategia, el ratio de riesgo y la temporalidad de un activo."""
    data = request.json
    symbol = data.get('symbol')
    strategy = data.get('strategy')
    risk_ratio = data.get('risk_ratio')
    timeframe = data.get('timeframe', 'M1')
    
    if not symbol or not strategy or not risk_ratio:
        return jsonify({'success': False, 'message': 'Faltan parámetros'}), 400
        
    success = update_active_symbol_config(symbol, strategy, risk_ratio, timeframe)
    if success:
        return jsonify({'success': True, 'message': f'Configuración de {symbol} actualizada.'})
    else:
        return jsonify({'success': False, 'message': 'No se pudo actualizar la configuración.'})

@app.route('/api/active_symbols/update_all', methods=['POST'])
def update_all_symbols_config_route():
    """Actualiza la estrategia, el ratio de riesgo y la temporalidad de todos los activos de forma masiva."""
    data = request.json
    strategy = data.get('strategy')
    risk_ratio = data.get('risk_ratio')
    timeframe = data.get('timeframe', 'M1')
    
    if not strategy or not risk_ratio or not timeframe:
        return jsonify({'success': False, 'message': 'Faltan parámetros'}), 400
        
    success = update_all_active_symbols_config(strategy, risk_ratio, timeframe)
    if success:
        return jsonify({'success': True, 'message': 'Configuración masiva aplicada a todos los activos.'})
    else:
        return jsonify({'success': False, 'message': 'No se pudo aplicar la configuración masiva.'})

@app.route('/api/toggle_bot', methods=['POST'])
def toggle_bot():
    """Activa o desactiva la ejecución del bot en segundo plano."""
    data = request.json
    run = data.get('run', False)
    
    if run:
        update_bot_status(1)
        main_ctrl.start_bot()
        message = "Bot iniciado exitosamente."
    else:
        update_bot_status(0)
        main_ctrl.stop_bot()
        message = "Bot detenido correctamente."
        
    return jsonify({'success': True, 'running': main_ctrl.running, 'message': message})

@app.route('/api/manual_trade', methods=['POST'])
def manual_trade():
    """Abre una posición de compra o venta manual."""
    data = request.json
    symbol = data.get('symbol')
    order_type = data.get('order_type') # 'BUY' o 'SELL'
    
    # Límite de seguridad estricto para pruebas: Forzar lote mínimo de 0.01
    lot = 0.01
    
    if not symbol or not order_type:
        return jsonify({'success': False, 'message': 'Faltan datos de la orden'}), 400
        
    success, message = mt5_ctrl.open_position(
        symbol=symbol,
        order_type=order_type,
        lot=lot,
        strategy='Manual'
    )
    
    return jsonify({'success': success, 'message': message})

@app.route('/api/close_trade', methods=['POST'])
def close_trade():
    """Cierra una posición abierta mediante su ticket."""
    data = request.json
    ticket = data.get('ticket')
    
    if not ticket:
        return jsonify({'success': False, 'message': 'Ticket requerido'}), 400
        
    success, message = mt5_ctrl.close_position(ticket)
    return jsonify({'success': success, 'message': message})

@app.route('/api/chart_data', methods=['GET'])
def get_chart_data():
    """Retorna las últimas velas del símbolo activo para alimentar Chart.js."""
    symbol = request.args.get('symbol', config.DEFAULT_SYMBOL)
    timeframe = request.args.get('timeframe', config.DEFAULT_TIMEFRAME)
    count = int(request.args.get('count', 60))
    
    rates = mt5_ctrl.get_rates(symbol, timeframe, count)
    return jsonify({
        'symbol': symbol,
        'timeframe': timeframe,
        'rates': rates
    })

@app.route('/api/faucet', methods=['POST'])
def run_faucet():
    """Fondea la cuenta simulada con 10,000 USD."""
    if mt5_ctrl.mock_mode:
        mt5_ctrl.mock_balance += 10000.0
        mt5_ctrl.mock_balance = round(mt5_ctrl.mock_balance, 2)
        return jsonify({
            'success': True, 
            'message': 'Se han añadido $10,000 USD de saldo simulado.',
            'balance': mt5_ctrl.mock_balance
        })
    else:
        return jsonify({
            'success': False, 
            'message': 'El faucet solo está disponible en modo simulador.'
        }), 400

if __name__ == '__main__':
    print("Iniciando Flask Server en el puerto 5000...")
    app.run(host='0.0.0.0', port=config.PORT, debug=config.DEBUG)

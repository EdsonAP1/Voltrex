from models.database import get_db_connection
import datetime

def get_settings():
    """Obtiene la configuración actual del bot de trading."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM settings ORDER BY id DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def update_settings(active_strategy, risk_type, entry_size, symbol):
    """Actualiza la configuración del bot de trading."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE settings 
        SET active_strategy = ?, risk_type = ?, entry_size = ?, symbol = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = (SELECT id FROM settings ORDER BY id DESC LIMIT 1)
    ''', (active_strategy, risk_type, entry_size, symbol))
    conn.commit()
    conn.close()
    return True

def update_bot_status(run_bot):
    """Activa (1) o desactiva (0) la ejecución del bot de trading."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE settings 
        SET run_bot = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = (SELECT id FROM settings ORDER BY id DESC LIMIT 1)
    ''', (run_bot,))
    conn.commit()
    conn.close()
    return True

def add_trade(ticket, symbol, trade_type, open_price, lot, strategy_used):
    """Registra una nueva posición abierta."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO trade_history (ticket, symbol, type, open_price, lot, status, open_time, strategy_used)
        VALUES (?, ?, ?, ?, ?, 'OPEN', CURRENT_TIMESTAMP, ?)
    ''', (str(ticket), symbol, trade_type, open_price, lot, strategy_used))
    conn.commit()
    conn.close()
    return True

def close_trade_in_db(ticket, close_price, profit):
    """Registra el cierre de una posición abierta."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE trade_history
        SET close_price = ?, profit = ?, status = 'CLOSED', close_time = CURRENT_TIMESTAMP
        WHERE ticket = ? AND status = 'OPEN'
    ''', (close_price, profit, str(ticket)))
    conn.commit()
    conn.close()
    return True

def get_db_open_trades():
    """Obtiene las posiciones abiertas registradas en base de datos."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trade_history WHERE status = 'OPEN' ORDER BY open_time DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_db_trade_history(limit=50):
    """Obtiene el historial de trades cerrados."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trade_history WHERE status = 'CLOSED' ORDER BY close_time DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_active_symbols():
    """Retorna una lista de diccionarios de los símbolos configurados para operar."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM active_symbols ORDER BY symbol ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_active_symbol(symbol, strategy='rsi_experto', risk_ratio='1:2', timeframe='M1'):
    """Agrega un símbolo a la lista de operación automática con estrategia, ratio de riesgo y temporalidad."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO active_symbols (symbol, strategy, risk_ratio, timeframe) VALUES (?, ?, ?, ?)", 
            (symbol, strategy, risk_ratio, timeframe)
        )
        conn.commit()
        success = True
    except Exception as e:
        success = False
    conn.close()
    return success

def update_active_symbol_config(symbol, strategy, risk_ratio, timeframe):
    """Actualiza la estrategia, el ratio de riesgo y la temporalidad de un activo."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE active_symbols SET strategy = ?, risk_ratio = ?, timeframe = ? WHERE symbol = ?", 
        (strategy, risk_ratio, timeframe, symbol)
    )
    conn.commit()
    conn.close()
    return True

def update_all_active_symbols_config(strategy, risk_ratio, timeframe):
    """Actualiza la estrategia, el ratio de riesgo y la temporalidad para TODOS los activos de forma masiva."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE active_symbols SET strategy = ?, risk_ratio = ?, timeframe = ?", 
        (strategy, risk_ratio, timeframe)
    )
    conn.commit()
    conn.close()
    return True

def remove_active_symbol(symbol):
    """Elimina un símbolo de la lista de operación automática."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM active_symbols WHERE symbol = ?", (symbol,))
    conn.commit()
    conn.close()
    return True

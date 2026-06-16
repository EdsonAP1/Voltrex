import sqlite3
import os
import sys

# Agregar el directorio raíz al path de Python para poder importar config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

def get_db_connection():
    """Retorna una conexión a la base de datos SQLite."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Permite acceder a las columnas por nombre
    return conn

def init_db():
    """Inicializa las tablas de la base de datos si no existen."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabla para las configuraciones activas del Bot
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            active_strategy TEXT NOT NULL,
            risk_type TEXT NOT NULL,
            entry_size REAL NOT NULL,
            symbol TEXT NOT NULL,
            run_bot INTEGER DEFAULT 0,  -- 0 = Detenido, 1 = Ejecutando
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla para el historial de trades (tanto reales de MT5 como simulados)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket TEXT NOT NULL,
            symbol TEXT NOT NULL,
            type TEXT NOT NULL,  -- 'BUY', 'SELL', 'BUY_LIMIT', 'SELL_LIMIT', etc.
            open_price REAL NOT NULL,
            close_price REAL,
            lot REAL NOT NULL,
            profit REAL DEFAULT 0.0,
            status TEXT NOT NULL,  -- 'OPEN', 'CLOSED', 'CANCELLED'
            open_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            close_time TIMESTAMP,
            strategy_used TEXT
        )
    ''')

    # Tabla para almacenar los activos que el usuario ha seleccionado para operar
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_symbols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            strategy TEXT NOT NULL DEFAULT 'rsi_experto',
            risk_ratio TEXT NOT NULL DEFAULT '1:2',
            timeframe TEXT NOT NULL DEFAULT 'M1',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Intentar agregar la columna timeframe si la tabla ya existía sin ella (migración automática)
    try:
        cursor.execute("ALTER TABLE active_symbols ADD COLUMN timeframe TEXT NOT NULL DEFAULT 'M1'")
    except sqlite3.OperationalError:
        # La columna ya existe, no hay que hacer nada
        pass
    
    # Insertar configuración por defecto si la tabla está vacía
    cursor.execute('SELECT COUNT(*) FROM settings')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO settings (active_strategy, risk_type, entry_size, symbol, run_bot)
            VALUES (?, ?, ?, ?, ?)
        ''', ('rsi_experto', 'lote_fijo', 0.01, config.DEFAULT_SYMBOL, 0))
        
    conn.commit()
    conn.close()

if __name__ == '__main__':
    print("Inicializando base de datos en:", config.DATABASE_PATH)
    init_db()
    print("Base de datos inicializada correctamente.")

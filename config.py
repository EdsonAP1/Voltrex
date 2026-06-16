import os

# Configuración del servidor Flask
SECRET_KEY = os.environ.get('SECRET_KEY', 'trading_bot_super_secret_key_12345')
DEBUG = True
PORT = 5000

# Base de datos SQLite
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'trading_bot.db')

# Configuración predeterminada de MetaTrader 5 (MT5)
# Si las credenciales están vacías o falla la conexión, se activará el modo simulador automáticamente.
MT5_LOGIN = 0  # Reemplazar con el número de cuenta de MT5
MT5_PASSWORD = ""  # Reemplazar con la contraseña de MT5
MT5_SERVER = ""  # Reemplazar con el servidor del broker (ej: "MetaQuotes-Demo")

# Configuración por defecto de Estrategias
DEFAULT_SYMBOL = "EURUSD"
DEFAULT_TIMEFRAME = "M1"  # Temporalidad de las velas por defecto para el bot (M1, M5, M15, M30, H1)

# Parámetros de Indicadores por defecto
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

EMA_PERIODS = [3, 9, 20, 50, 100, 200]

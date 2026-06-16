import time
import random
import sys
import os

# Importar el módulo MetaTrader5 de forma segura
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

# Agregar el directorio raíz al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from models.settings_model import add_trade, close_trade_in_db, get_db_open_trades, get_db_trade_history

class MT5Controller:
    _instance = None

    def __new__(cls, *args, **kwargs):
        """Implementa un patrón Singleton para que todo el bot use la misma instancia."""
        if not cls._instance:
            cls._instance = super(MT5Controller, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.connected = False
        self.mock_mode = False
        
        # Estado del simulador (Mock Mode)
        self.mock_balance = 10000.0
        self.mock_equity = 10000.0
        self.mock_margin = 0.0
        self.mock_free_margin = 10000.0
        self.mock_symbols = [
            'FlipX 1', 'FlipX 2', 'FlipX 3', 'FlipX 4', 'FlipX 5', 
            'FX Vol 20', 'FX Vol 40', 'FX Vol 60', 'FX Vol 80',
            'EURUSD', 'GBPUSD', 'BTCUSD', 'ETHUSD', 'XAUUSD', 'USDCAD'
        ]
        
        # Precios base para la simulación
        self.mock_prices = {
            'FlipX 1': 11850.50,
            'FlipX 2': 11842.20,
            'FlipX 3': 11860.80,
            'FlipX 4': 11835.40,
            'FlipX 5': 11870.10,
            'FX Vol 20': 20.450,
            'FX Vol 40': 40.820,
            'FX Vol 60': 60.150,
            'FX Vol 80': 80.930,
            'EURUSD': 1.08542,
            'GBPUSD': 1.27218,
            'BTCUSD': 67420.50,
            'ETHUSD': 3480.75,
            'XAUUSD': 2322.80,
            'USDCAD': 1.36540
        }
        
        # Historial de precios de simulación (para generar velas coherentes)
        self.price_histories = {}
        for sym in self.mock_symbols:
            self.price_histories[sym] = self._generate_initial_history(sym, 100)
            
        self.initialize_connection()

    def initialize_connection(self):
        """Intenta conectarse a la API de MT5, si falla activa el modo simulador."""
        if not MT5_AVAILABLE:
            print("[MT5] Módulo MetaTrader5 no está instalado en este sistema. Activando modo simulador.")
            self.mock_mode = True
            self.connected = True
            return True
            
        # Intentar conectar
        # Si se especificó credenciales en config, las usamos
        login_success = False
        if config.MT5_LOGIN != 0 and config.MT5_PASSWORD != "":
            print(f"[MT5] Intentando conectar a la cuenta {config.MT5_LOGIN} en {config.MT5_SERVER}...")
            if mt5.initialize(login=config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER):
                login_success = True
        else:
            print("[MT5] Intentando conectar a la terminal local activa...")
            if mt5.initialize():
                login_success = True
                
        if login_success:
            print("[MT5] Conectado exitosamente a MetaTrader 5.")
            self.connected = True
            self.mock_mode = False
            # Activar el símbolo por defecto
            mt5.symbol_select(config.DEFAULT_SYMBOL, True)
            return True
        else:
            print(f"[MT5] Error al conectar a la terminal de MetaTrader 5. Código de error: {mt5.last_error()}")
            print("[MT5] Activando modo simulador automático.")
            self.mock_mode = True
            self.connected = True
            return True

    def _generate_initial_history(self, symbol, count):
        """Genera un historial de precios coherente para simular velas."""
        base_price = self.mock_prices[symbol]
        history = []
        current_time = time.time() - (count * 60)
        
        price = base_price
        for i in range(count):
            change = price * random.uniform(-0.001, 0.001)
            open_p = price
            close_p = price + change
            high_p = max(open_p, close_p) + (abs(change) * random.uniform(0.1, 0.5))
            low_p = min(open_p, close_p) - (abs(change) * random.uniform(0.1, 0.5))
            
            history.append({
                'time': int(current_time + (i * 60)),
                'open': open_p,
                'high': high_p,
                'low': low_p,
                'close': close_p,
                'tick_volume': random.randint(10, 150)
            })
            price = close_p
            
        self.mock_prices[symbol] = price
        return history

    def tick_simulator(self):
        """Actualiza levemente los precios simulados para emular un mercado en vivo."""
        if not self.mock_mode:
            return
            
        for symbol in self.mock_symbols:
            current_price = self.mock_prices[symbol]
            # Cambio aleatorio porcentual
            pct_change = random.uniform(-0.0005, 0.0005)
            new_price = current_price * (1 + pct_change)
            
            # Limitar decimales según el activo
            decimals = 5 if "USD" in symbol and "BTC" not in symbol and "ETH" not in symbol and "XAU" not in symbol else 2
            new_price = round(new_price, decimals)
            self.mock_prices[symbol] = new_price
            
            # Agregar a su historial de velas (actualizar la última o agregar una nueva si ha pasado un minuto)
            history = self.price_histories[symbol]
            now = int(time.time())
            
            # Si pasó más de 60 segundos de la última vela, crear una nueva
            if len(history) == 0 or now - history[-1]['time'] >= 60:
                open_p = history[-1]['close'] if len(history) > 0 else new_price
                history.append({
                    'time': now - (now % 60), # Redondear al minuto
                    'open': open_p,
                    'high': max(open_p, new_price),
                    'low': min(open_p, new_price),
                    'close': new_price,
                    'tick_volume': 1
                })
                # Mantener el historial acotado a 200 velas
                if len(history) > 200:
                    history.pop(0)
            else:
                # Actualizar la vela actual
                last_candle = history[-1]
                last_candle['close'] = new_price
                last_candle['high'] = max(last_candle['high'], new_price)
                last_candle['low'] = min(last_candle['low'], new_price)
                last_candle['tick_volume'] += 1

    def get_account_info(self):
        """Retorna Balance, Equidad, Margen Libre y Beneficio Total en tiempo real."""
        if not self.connected:
            return None
            
        if not self.mock_mode:
            # Conexión real
            info = mt5.account_info()
            if info is not None:
                return {
                    'balance': info.balance,
                    'equity': info.equity,
                    'margin': info.margin,
                    'free_margin': info.margin_free,
                    'profit': info.profit,
                    'currency': info.currency,
                    'mock': False
                }
            return None
        else:
            # Modo simulado
            # Primero actualizamos los precios de los símbolos
            self.tick_simulator()
            
            # Calcular profit dinámico de posiciones abiertas
            open_trades = get_db_open_trades()
            total_profit = 0.0
            total_margin = 0.0
            
            for trade in open_trades:
                symbol = trade['symbol']
                trade_type = trade['type']
                open_price = trade['open_price']
                lot = trade['lot']
                
                curr_price = self.mock_prices.get(symbol, 1.0)
                
                # Cálculo simple de ganancia: lote * multiplicador * diferencia de precio
                multiplier = 100000  # Contrato estándar (1 lote = 100k unidades para Forex)
                if "BTC" in symbol or "ETH" in symbol:
                    multiplier = 1  # Criptos
                elif "XAU" in symbol:
                    multiplier = 100  # Oro
                    
                if trade_type == 'BUY':
                    trade_profit = (curr_price - open_price) * lot * multiplier
                else:
                    trade_profit = (open_price - curr_price) * lot * multiplier
                    
                total_profit += trade_profit
                
                # Margen aproximado (1% de apalancamiento o similar)
                total_margin += (open_price * lot * multiplier) * 0.01
                
            self.mock_equity = self.mock_balance + total_profit
            self.mock_margin = total_margin
            self.mock_free_margin = self.mock_equity - self.mock_margin
            
            return {
                'balance': round(self.mock_balance, 2),
                'equity': round(self.mock_equity, 2),
                'margin': round(self.mock_margin, 2),
                'free_margin': round(self.mock_free_margin, 2),
                'profit': round(total_profit, 2),
                'currency': 'USD',
                'mock': True
            }

    def get_last_price(self, symbol):
        """Retorna el último precio conocido del símbolo (simulado o real)."""
        if not self.connected:
            return 0.0
        if self.mock_mode:
            self.tick_simulator()
            return self.mock_prices.get(symbol, 0.0)
        else:
            # Asegurar que el símbolo esté habilitado
            mt5.symbol_select(symbol, True)
            tick = mt5.symbol_info_tick(symbol)
            if tick is not None:
                # Usar tick.last si existe, o el promedio bid/ask
                if hasattr(tick, 'last') and tick.last > 0:
                    return tick.last
                return (tick.bid + tick.ask) / 2
            else:
                # Fallback: obtener la última vela de 1m
                rates = self.get_rates(symbol, "M1", 1)
                if rates:
                    return rates[0]['close']
            return 0.0

    def get_symbols(self):
        """Retorna una lista de los símbolos disponibles."""
        if not self.connected:
            return []
            
        if not self.mock_mode:
            symbols = mt5.symbols_get()
            if symbols:
                # Retornar los símbolos que están habilitados en observación de mercado
                return [s.name for s in symbols if s.visible]
            return [config.DEFAULT_SYMBOL]
        else:
            return self.mock_symbols

    def get_rates(self, symbol, timeframe_str="M1", count=100):
        """Obtiene datos de velas históricas en un formato estandarizado."""
        if not self.connected:
            return []
            
        if not self.mock_mode:
            # Asegurar que el símbolo esté visible en observación de mercado
            mt5.symbol_select(symbol, True)
            
            # Mapeo de temporalidades
            tf_map = {
                "M1": mt5.TIMEFRAME_M1,
                "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15,
                "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1,
                "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1
            }
            tf = tf_map.get(timeframe_str, mt5.TIMEFRAME_M1)
            
            # Obtener datos de la terminal real
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
            if rates is not None:
                # Convertir a lista de diccionarios
                result = []
                for rate in rates:
                    result.append({
                        'time': int(rate['time']),
                        'open': float(rate['open']),
                        'high': float(rate['high']),
                        'low': float(rate['low']),
                        'close': float(rate['close']),
                        'tick_volume': int(rate['tick_volume'])
                    })
                return result
            return []
        else:
            # Modo simulador: inicialización dinámica si el símbolo no existe
            if symbol not in self.mock_symbols:
                self.mock_symbols.append(symbol)
                self.mock_prices[symbol] = round(random.uniform(50.0, 1500.0), 4)
                self.price_histories[symbol] = self._generate_initial_history(symbol, 100)
                
            self.tick_simulator()
            history = self.price_histories.get(symbol, [])
            # Retornar los últimos `count` elementos
            return history[-count:]

    def open_position(self, symbol, order_type, lot, sl=None, tp=None, strategy=None):
        """Abre una posición en mercado (BUY o SELL)."""
        if not self.connected:
            return False, "MT5 no inicializado"
            
        strategy_name = strategy if strategy else "manual"
        
        if not self.mock_mode:
            # Abrir posición real en MT5
            # Habilitar símbolo por si no está visible
            mt5.symbol_select(symbol, True)
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                return False, f"Símbolo {symbol} no encontrado"
                
            # Obtener el precio actual
            price = mt5.symbol_info_tick(symbol).ask if order_type == 'BUY' else mt5.symbol_info_tick(symbol).bid
            
            action_type = mt5.ORDER_TYPE_BUY if order_type == 'BUY' else mt5.ORDER_TYPE_SELL
            
            # Estructurar la petición
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": float(lot),
                "type": action_type,
                "price": price,
                "deviation": 20,
                "magic": 999912,
                "comment": f"Bot - {strategy_name}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            if sl:
                request["sl"] = float(sl)
            if tp:
                request["tp"] = float(tp)
                
            # Enviar orden
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return False, f"Error al enviar orden: {result.comment} (code: {result.retcode})"
            
            # Registrar en la base de datos local
            add_trade(
                ticket=result.order,
                symbol=symbol,
                trade_type=order_type,
                open_price=price,
                lot=lot,
                strategy_used=strategy_name
            )
            return True, f"Posición abierta correctamente. Ticket: {result.order}"
            
        else:
            # Modo simulado
            self.tick_simulator()
            price = self.mock_prices.get(symbol, 1.0)
            ticket = random.randint(1000000, 9999999)
            
            add_trade(
                ticket=ticket,
                symbol=symbol,
                trade_type=order_type,
                open_price=price,
                lot=lot,
                strategy_used=strategy_name
            )
            return True, f"[MOCK] Posición {order_type} abierta en {symbol} a {price}. Ticket: {ticket}"

    def close_position(self, ticket):
        """Cierra una posición por su ticket."""
        if not self.connected:
            return False, "MT5 no inicializado"
            
        ticket_str = str(ticket)
        
        # Primero buscar la posición abierta en base de datos local
        open_trades = get_db_open_trades()
        target_trade = None
        for trade in open_trades:
            if trade['ticket'] == ticket_str:
                target_trade = trade
                break
                
        if not target_trade:
            return False, "La posición no está registrada como abierta."
            
        symbol = target_trade['symbol']
        order_type = target_trade['type']
        open_price = target_trade['open_price']
        lot = target_trade['lot']
        
        if not self.mock_mode:
            # Cierre real en MT5
            positions = mt5.positions_get(ticket=int(ticket))
            if not positions:
                # Si ya no existe la posición, registrar como cerrada
                close_trade_in_db(ticket, open_price, 0.0)
                return False, "La posición no existe en MT5"
                
            position = positions[0]
            price = mt5.symbol_info_tick(symbol).bid if order_type == 'BUY' else mt5.symbol_info_tick(symbol).ask
            action_type = mt5.ORDER_TYPE_SELL if order_type == 'BUY' else mt5.ORDER_TYPE_BUY
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": float(lot),
                "type": action_type,
                "position": int(ticket),
                "price": price,
                "deviation": 20,
                "magic": 999912,
                "comment": "Cierre Bot",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return False, f"Error al cerrar orden: {result.comment} (code: {result.retcode})"
            
            # Calcular profit final
            profit = float(result.profit) if hasattr(result, 'profit') else 0.0
            close_trade_in_db(ticket, price, profit)
            return True, f"Posición {ticket} cerrada con éxito."
            
        else:
            # Modo simulado
            self.tick_simulator()
            curr_price = self.mock_prices.get(symbol, 1.0)
            
            multiplier = 100000
            if "BTC" in symbol or "ETH" in symbol:
                multiplier = 1
            elif "XAU" in symbol:
                multiplier = 100
                
            if order_type == 'BUY':
                profit = (curr_price - open_price) * lot * multiplier
            else:
                profit = (open_price - curr_price) * lot * multiplier
                
            profit = round(profit, 2)
            
            # Actualizar balance simulado
            self.mock_balance += profit
            self.mock_balance = round(self.mock_balance, 2)
            
            close_trade_in_db(ticket, curr_price, profit)
            return True, f"[MOCK] Posición {ticket} cerrada a {curr_price} con beneficio de {profit} USD."

    def get_open_positions(self):
        """Retorna las posiciones abiertas formateadas para la UI."""
        if not self.connected:
            return []
            
        if not self.mock_mode:
            # Obtener posiciones de MT5 real
            positions = mt5.positions_get()
            result = []
            if positions:
                for pos in positions:
                    result.append({
                        'ticket': str(pos.ticket),
                        'symbol': pos.symbol,
                        'type': 'BUY' if pos.type == mt5.POSITION_TYPE_BUY else 'SELL',
                        'open_price': pos.price_open,
                        'current_price': pos.price_current,
                        'lot': pos.volume,
                        'profit': pos.profit,
                        'open_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(pos.time)),
                        'strategy': 'MT5'
                    })
                return result
            return []
        else:
            # Obtener del simulador
            self.tick_simulator()
            db_trades = get_db_open_trades()
            result = []
            
            for trade in db_trades:
                symbol = trade['symbol']
                trade_type = trade['type']
                open_price = trade['open_price']
                lot = trade['lot']
                
                curr_price = self.mock_prices.get(symbol, 1.0)
                
                multiplier = 100000
                if "BTC" in symbol or "ETH" in symbol:
                    multiplier = 1
                elif "XAU" in symbol:
                    multiplier = 100
                    
                if trade_type == 'BUY':
                    profit = (curr_price - open_price) * lot * multiplier
                else:
                    profit = (open_price - curr_price) * lot * multiplier
                    
                result.append({
                    'ticket': trade['ticket'],
                    'symbol': symbol,
                    'type': trade_type,
                    'open_price': open_price,
                    'current_price': curr_price,
                    'lot': lot,
                    'profit': round(profit, 2),
                    'open_time': trade['open_time'],
                    'strategy': trade.get('strategy_used', 'sim')
                })
                
            return result

    def close_connection(self):
        """Cierra la terminal de MT5."""
        if not self.mock_mode and MT5_AVAILABLE:
            mt5.shutdown()
            print("[MT5] Conexión cerrada.")
            self.connected = False

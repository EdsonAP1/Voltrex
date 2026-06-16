import threading
import time
import random
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from models.settings_model import get_settings, get_db_open_trades, get_db_trade_history, get_active_symbols
from controllers.mt5_controller import MT5Controller
from controllers.strategy_loader import StrategyLoader

class MainController:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MainController, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.mt5_ctrl = MT5Controller()
        self.strategy_loader = StrategyLoader()
        self.running = False
        self.thread = None
        self.status_message = "Bot inicializado. En espera de activación."

    def start_bot(self):
        """Inicia el bucle del bot en un hilo de ejecución en segundo plano."""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._bot_loop, daemon=True)
        self.thread.start()
        self.status_message = "Bot en ejecución y analizando mercados..."
        print("[BOT] Hilo principal iniciado.")

    def stop_bot(self):
        """Detiene el bucle del bot."""
        self.running = False
        self.status_message = "Bot detenido manualmente."
        print("[BOT] Hilo principal detenido.")

    def _calculate_lot_size(self, risk_type, entry_size, symbol, account_info):
        """Calcula el tamaño del lote en base al tipo de gestión de riesgo."""
        # LÍMITE DE SEGURIDAD ESTRICTO PARA PRUEBAS: Forzar lote mínimo de 0.01
        return 0.01

    def _bot_loop(self):
        """Bucle principal de trading."""
        while self.running:
            try:
                # 1. Obtener la configuración actual desde SQLite
                settings = get_settings()
                if not settings:
                    time.sleep(5)
                    continue
                    
                # Si el estado de la DB dice detener, nos detenemos
                if settings['run_bot'] == 0:
                    self.status_message = "Bot en espera (Desactivado desde el panel)."
                    time.sleep(3)
                    continue
                    
                self.status_message = "Analizando condiciones de mercado..."
                
                strategy = settings['active_strategy']
                risk_type = settings['risk_type']
                entry_size = settings['entry_size']
                
                # Obtener la lista de símbolos activos a operar
                symbols_to_trade = get_active_symbols()
                if not symbols_to_trade:
                    # Fallback al símbolo principal configurado
                    symbols_to_trade = [settings['symbol']]
                
                # 2. Actualizar/Simular precios y obtener info de cuenta
                acc_info = self.mt5_ctrl.get_account_info()
                if not acc_info:
                    self.status_message = "Error: No se pudo obtener información de la cuenta MT5."
                    time.sleep(5)
                    continue
                    
                # 3. Simular el TP/SL en modo simulador para cerrar trades automáticamente
                if self.mt5_ctrl.mock_mode:
                    open_trades = get_db_open_trades()
                    for trade in open_trades:
                        ticket = int(trade['ticket'])
                        trade_symbol = trade['symbol']
                        trade_type = trade['type']
                        open_p = trade['open_price']
                        
                        curr_p = self.mt5_ctrl.mock_prices.get(trade_symbol, open_p)
                        
                        close_chance = random.uniform(0, 1)
                        multiplier = 100000
                        if "BTC" in trade_symbol or "ETH" in trade_symbol:
                            multiplier = 1
                        elif "XAU" in trade_symbol:
                            multiplier = 100
                            
                        pips_diff = (curr_p - open_p) if trade_type == 'BUY' else (open_p - curr_p)
                        profit = pips_diff * trade['lot'] * multiplier
                        
                        if profit >= 250.0 or profit <= -150.0 or close_chance < 0.08:
                            self.mt5_ctrl.close_position(ticket)
                            print(f"[BOT] Posición simulada {ticket} cerrada automáticamente. Profit: {profit}")
                
                # 4. Iterar sobre todos los activos seleccionados para operar
                log_messages = []
                for item in symbols_to_trade:
                    # Si viene como string por fallback de settings
                    if isinstance(item, str):
                        symbol = item
                        symbol_strategy = strategy
                        symbol_ratio = '1:2'
                        symbol_timeframe = config.DEFAULT_TIMEFRAME
                    else:
                        symbol = item['symbol']
                        symbol_strategy = item['strategy']
                        symbol_ratio = item['risk_ratio']
                        symbol_timeframe = item.get('timeframe', config.DEFAULT_TIMEFRAME)
                        
                    candles = self.mt5_ctrl.get_rates(symbol, symbol_timeframe, 100)
                    if not candles or len(candles) < 20:
                        continue
                        
                    # Ejecutar análisis de la estrategia específica del activo
                    signal = self.strategy_loader.analyze(symbol_strategy, candles)
                    
                    # Evaluar la señal y ejecutar órdenes
                    if signal in ['BUY', 'SELL']:
                        # Verificar si ya tenemos posiciones abiertas para este símbolo
                        positions = self.mt5_ctrl.get_open_positions()
                        symbol_positions = [p for p in positions if p['symbol'] == symbol]
                        
                        if len(symbol_positions) == 0:
                            lot = self._calculate_lot_size(risk_type, entry_size, symbol, acc_info)
                            
                            # Cálculo dinámico de Stop Loss (0.5% del precio actual) y Take Profit (según ratio)
                            current_price = candles[-1]['close']
                            sl_distance = current_price * 0.005 # 0.5% del precio
                            
                            # Multiplicador del Take Profit según el ratio de riesgo
                            ratio_mult = 2.0
                            if symbol_ratio == '1:1':
                                ratio_mult = 1.0
                            elif symbol_ratio == '1:3':
                                ratio_mult = 3.0
                            
                            tp_distance = sl_distance * ratio_mult
                            
                            if signal == 'BUY':
                                sl_price = current_price - sl_distance
                                tp_price = current_price + tp_distance
                            else:
                                sl_price = current_price + sl_distance
                                tp_price = current_price - tp_distance
                                
                            # Determinar decimales del activo
                            decimals = 5 if current_price < 2.0 else (2 if current_price > 100.0 else 4)
                            sl_price = round(sl_price, decimals)
                            tp_price = round(tp_price, decimals)
                            
                            self.status_message = f"Señal {signal} en {symbol}. Abriendo con SL: {sl_price}, TP: {tp_price}..."
                            success, msg = self.mt5_ctrl.open_position(
                                symbol=symbol,
                                order_type=signal,
                                lot=lot,
                                sl=sl_price,
                                tp=tp_price,
                                strategy=symbol_strategy
                            )
                            print(f"[BOT] Ejecución en {symbol} ({symbol_strategy}): {msg}")
                            log_messages.append(f"{symbol}: {signal}")
                    
                if log_messages:
                    self.status_message = f"Señales ejecutadas: {', '.join(log_messages)}"
                else:
                    active_names = [item['symbol'] if isinstance(item, dict) else item for item in symbols_to_trade]
                    self.status_message = f"Monitoreando {len(active_names)} activos: {', '.join(active_names)}. Sin señales."
                    
            except Exception as e:
                print(f"[BOT ERROR] Error en el bucle principal: {str(e)}")
                self.status_message = f"Error en ejecución: {str(e)}"
                
            # Pausa del bucle principal
            time.sleep(5)
            
        self.status_message = "Bot detenido."

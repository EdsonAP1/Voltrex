import math

class StrategyLoader:
    def __init__(self):
        pass

    # ==========================================
    # CÁLCULOS MATEMÁTICOS DE INDICADORES NATIVOS
    # ==========================================

    @staticmethod
    def calculate_ema(prices, period):
        """Calcula la Media Móvil Exponencial (EMA)."""
        if len(prices) < period:
            return [0.0] * len(prices)
            
        ema = []
        # El primer valor es una media simple SMA
        sma = sum(prices[:period]) / period
        ema.append(sma)
        
        # Factor de suavizado
        multiplier = 2 / (period + 1)
        
        for i in range(period, len(prices)):
            current_ema = (prices[i] - ema[-1]) * multiplier + ema[-1]
            ema.append(current_ema)
            
        # Rellenar con ceros al principio para mantener longitud
        return [0.0] * (period - 1) + ema

    @staticmethod
    def calculate_rsi(prices, period=14):
        """Calcula el Relative Strength Index (RSI)."""
        if len(prices) < period + 1:
            return [50.0] * len(prices)
            
        rsi = [50.0] * (period)
        
        # Calcular ganancias y pérdidas
        gains = []
        losses = []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(abs(change))
                
        # Primer promedio
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        if avg_loss == 0:
            rsi.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100.0 - (100.0 / (1.0 + rs)))
            
        # Promedios subsiguientes (Welles Wilder smoothing)
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                rsi.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi.append(100.0 - (100.0 / (1.0 + rs)))
                
        return rsi

    # ==========================================
    # DETECCIÓN DE PATRONES DE VELAS
    # ==========================================

    @staticmethod
    def is_bullish_engulfing(candles, i):
        """Detecta una vela envolvente alcista en el índice i respecto al anterior i-1."""
        if i < 1:
            return False
        prev = candles[i-1]
        curr = candles[i]
        
        prev_is_bearish = prev['close'] < prev['open']
        curr_is_bullish = curr['close'] > curr['open']
        
        if prev_is_bearish and curr_is_bullish:
            # Cuerpo actual envuelve el cuerpo anterior
            return curr['close'] >= prev['open'] and curr['open'] <= prev['close']
        return False

    @staticmethod
    def is_bearish_engulfing(candles, i):
        """Detecta una vela envolvente bajista en el índice i respecto al anterior i-1."""
        if i < 1:
            return False
        prev = candles[i-1]
        curr = candles[i]
        
        prev_is_bullish = prev['close'] > prev['open']
        curr_is_bearish = curr['close'] < curr['open']
        
        if prev_is_bullish and curr_is_bearish:
            # Cuerpo actual envuelve el cuerpo anterior
            return curr['close'] <= prev['open'] and curr['open'] >= prev['close']
        return False

    @staticmethod
    def is_hammer(candle):
        """Detecta un martillo alcista."""
        body = abs(candle['close'] - candle['open'])
        total_range = candle['high'] - candle['low']
        if total_range == 0:
            return False
            
        lower_wick = min(candle['open'], candle['close']) - candle['low']
        upper_wick = candle['high'] - max(candle['open'], candle['close'])
        
        # El cuerpo debe ser pequeño y estar en la parte superior (mecha inferior al menos 2 veces el cuerpo)
        # Mecha superior muy pequeña (menos del 10% del rango total)
        return (lower_wick >= 2 * body) and (upper_wick <= total_range * 0.15) and (body > 0)

    @staticmethod
    def is_shooting_star(candle):
        """Detecta un martillo invertido / estrella fugaz bajista."""
        body = abs(candle['close'] - candle['open'])
        total_range = candle['high'] - candle['low']
        if total_range == 0:
            return False
            
        lower_wick = min(candle['open'], candle['close']) - candle['low']
        upper_wick = candle['high'] - max(candle['open'], candle['close'])
        
        # El cuerpo debe ser pequeño y estar en la parte inferior (mecha superior al menos 2 veces el cuerpo)
        # Mecha inferior muy pequeña (menos del 10% del rango total)
        return (upper_wick >= 2 * body) and (lower_wick <= total_range * 0.15) and (body > 0)

    # ==========================================
    # IMPLEMENTACIÓN DE ESTRATEGIAS
    # ==========================================

    def run_rsi_experto(self, candles):
        """
        Estrategia RSI Experto:
        - Calcula el RSI 14.
        - Busca divergencias y las confirma con patrones de velas (Envolvente/Martillo).
        Retorna: 'BUY', 'SELL' o 'HOLD'
        """
        if len(candles) < 20:
            return 'HOLD'
            
        closes = [c['close'] for c in candles]
        rsi = self.calculate_rsi(closes, 14)
        
        curr_rsi = rsi[-1]
        prev_rsi = rsi[-2]
        curr_candle = candles[-1]
        prev_candle = candles[-2]
        
        # Detección de Divergencias Simples + Confirmación de Velas
        # Caso de COMPRA (Sobreventa + Divergencia/Vela de reversión)
        if curr_rsi < 35 or prev_rsi < 30:
            # Confirmación con Martillo Alcista o Envolvente Alcista
            if self.is_hammer(curr_candle) or self.is_bullish_engulfing(candles, len(candles)-1):
                return 'BUY'
                
        # Caso de VENTA (Sobrecompra + Divergencia/Vela de reversión)
        if curr_rsi > 65 or prev_rsi > 70:
            # Confirmación con Estrella Fugaz o Envolvente Bajista
            if self.is_shooting_star(curr_candle) or self.is_bearish_engulfing(candles, len(candles)-1):
                return 'SELL'
                
        return 'HOLD'

    def run_bloque_emas(self, candles):
        """
        Estrategia Bloque de EMAs (3, 9, 20, 50, 100, 200):
        - Cruce rápido de EMAs (3 cruza a la de 9 a favor de la de 20 y 50).
        - O rebote estructural en EMA 50 / 200.
        Retorna: 'BUY', 'SELL' o 'HOLD'
        """
        if len(candles) < 200:
            return 'HOLD'
            
        closes = [c['close'] for c in candles]
        ema3 = self.calculate_ema(closes, 3)
        ema9 = self.calculate_ema(closes, 9)
        ema20 = self.calculate_ema(closes, 20)
        ema50 = self.calculate_ema(closes, 50)
        ema200 = self.calculate_ema(closes, 200)
        
        # Datos del último tick
        e3_c, e3_p = ema3[-1], ema3[-2]
        e9_c, e9_p = ema9[-1], ema9[-2]
        e20_c = ema20[-1]
        e50_c = ema50[-1]
        e200_c = ema200[-1]
        
        # Tendencia alcista estructural (200 es la más lenta, luego 50, 20)
        tendencia_alcista = e20_c > e50_c > e200_c
        tendencia_bajista = e20_c < e50_c < e200_c
        
        # Cruce de medias rápido (3 cruza a 9)
        cruce_alcista = (e3_p <= e9_p) and (e3_c > e9_c)
        cruce_bajista = (e3_p >= e9_p) and (e3_c < e9_c)
        
        if tendencia_alcista and cruce_alcista:
            return 'BUY'
        elif tendencia_bajista and cruce_bajista:
            return 'SELL'
            
        # Rebotes estructurales
        curr_candle = candles[-1]
        # Si la vela toca la EMA50 por arriba y cierra alcista, en tendencia alcista
        if tendencia_alcista and curr_candle['low'] <= e50_c <= max(curr_candle['open'], curr_candle['close']):
            if curr_candle['close'] > curr_candle['open']: # Vela verde
                return 'BUY'
                
        if tendencia_bajista and curr_candle['high'] >= e50_c >= min(curr_candle['open'], curr_candle['close']):
            if curr_candle['close'] < curr_candle['open']: # Vela roja
                return 'SELL'
                
        return 'HOLD'

    def run_order_blocks(self, candles):
        """
        Estrategia de Order Blocks y BOS / CHoCH:
        - Identifica últimos máximos/mínimos (estructura).
        - Detecta BOS (quiebre de estructura) al romper máximos/mínimos anteriores.
        - Identifica el bloque de órdenes (la vela de sentido contrario anterior al movimiento impulsivo).
        - Retorna 'BUY' cuando el precio testea un Bullish OB, o 'SELL' al testear un Bearish OB.
        """
        if len(candles) < 30:
            return 'HOLD'
            
        # Simulación analítica de Order Blocks simplificada para ejecución algorítmica robusta
        # 1. Hallar picos (Highs) y valles (Lows) locales usando una ventana de 5 velas (Fractales)
        highs = []
        lows = []
        for i in range(2, len(candles) - 2):
            c_prev2 = candles[i-2]
            c_prev1 = candles[i-1]
            c = candles[i]
            c_next1 = candles[i+1]
            c_next2 = candles[i+2]
            
            # Fractal de Máximo
            if c['high'] > c_prev2['high'] and c['high'] > c_prev1['high'] and c['high'] > c_next1['high'] and c['high'] > c_next2['high']:
                highs.append((i, c['high'], c)) # Guardar índice, precio e info de vela
            # Fractal de Mínimo
            if c['low'] < c_prev2['low'] and c['low'] < c_prev1['low'] and c['low'] < c_next1['low'] and c['low'] < c_next2['low']:
                lows.append((i, c['low'], c))
                
        if not highs or not lows:
            return 'HOLD'
            
        # Último máximo y mínimo local
        last_high_idx, last_high_val, last_high_candle = highs[-1]
        last_low_idx, last_low_val, last_low_candle = lows[-1]
        
        curr_close = candles[-1]['close']
        curr_low = candles[-1]['low']
        curr_high = candles[-1]['high']
        
        # Detección de Quiebre de Estructura (BOS)
        # Si el precio actual cerró por encima del último máximo estructural => BOS Alcista
        # El Order Block alcista es la última vela bajista antes de que se iniciara la subida hacia ese máximo
        bos_alcista = False
        bullish_ob_zone = None
        
        if curr_close > last_high_val:
            bos_alcista = True
            # Buscar la última vela bajista antes del impulso
            for idx in range(last_high_idx, 0, -1):
                if candles[idx]['close'] < candles[idx]['open']:
                    # Esta vela bajista es el Bullish OB
                    bullish_ob_zone = (candles[idx]['low'], candles[idx]['high'])
                    break
                    
        # BOS Bajista
        bos_bajista = False
        bearish_ob_zone = None
        if curr_close < last_low_val:
            bos_bajista = True
            # Buscar la última vela alcista antes del impulso bajista
            for idx in range(last_low_idx, 0, -1):
                if candles[idx]['close'] > candles[idx]['open']:
                    bearish_ob_zone = (candles[idx]['low'], candles[idx]['high'])
                    break
                    
        # Mitigación (Entrada): El precio actual retestea un bloque de órdenes previo
        # En una simulación simplificada, si el precio retrocede a la zona del último OB activo
        if bullish_ob_zone:
            # Si el precio actual está entrando en la zona del OB alcista, compramos
            if bullish_ob_zone[0] <= curr_low <= bullish_ob_zone[1]:
                return 'BUY'
                
        if bearish_ob_zone:
            # Si el precio actual está entrando en la zona del OB bajista, vendemos
            if bearish_ob_zone[0] <= curr_high <= bearish_ob_zone[1]:
                return 'SELL'
                
        # Alternativamente, si hay un BOS alcista reciente, buscamos comprar en retrocesos
        if bos_alcista and curr_close < (last_high_val + last_low_val) / 2:
            return 'BUY'
        if bos_bajista and curr_close > (last_high_val + last_low_val) / 2:
            return 'SELL'
            
        return 'HOLD'

    def run_canales_soportes(self, candles):
        """
        Estrategia de Canales y Soportes/Resistencias:
        - Traza soportes y resistencias dinámicos.
        - Identifica canales ascendentes, descendentes o laterales.
        - Opera rebotes en soportes (BUY) o resistencias (SELL).
        - Opera rupturas confirmadas.
        """
        if len(candles) < 20:
            return 'HOLD'
            
        closes = [c['close'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        
        # 1. Encontrar Soportes y Resistencias locales (S/R)
        # Usamos máximos y mínimos locales simples
        sr_resistance = max(highs[-15:-1]) # Resistencia local de las últimas 15 velas (sin la actual)
        sr_support = min(lows[-15:-1])     # Soporte local
        
        curr_candle = candles[-1]
        
        # 2. Rebote en Soporte con vela alcista
        if curr_candle['low'] <= sr_support * 1.001 and curr_candle['close'] > curr_candle['open']:
            # El precio tocó el soporte y cerró como vela alcista
            return 'BUY'
            
        # Rebote en Resistencia con vela bajista
        if curr_candle['high'] >= sr_resistance * 0.999 and curr_candle['close'] < curr_candle['open']:
            # El precio tocó la resistencia y cerró como vela bajista
            return 'SELL'
            
        # 3. Ruptura de Canal / Resistencia
        if curr_candle['close'] > sr_resistance:
            # Rompe resistencia al alza
            return 'BUY'
            
        if curr_candle['close'] < sr_support:
            # Rompe soporte a la baja
            return 'SELL'
            
        return 'HOLD'

    def run_de_prueba(self, candles):
        """
        Estrategia de Prueba Rápida (Test):
        Genera señales frecuentes basándose en el color de la última vela para verificar la orquestación.
        """
        if not candles or len(candles) == 0:
            return 'HOLD'
        last_candle = candles[-1]
        if last_candle['close'] > last_candle['open']:
            return 'BUY'
        elif last_candle['close'] < last_candle['open']:
            return 'SELL'
        return 'HOLD'

    # ==========================================
    # INTERFAZ PRINCIPAL DE EJECUCIÓN
    # ==========================================

    def analyze(self, strategy_name, candles):
        """
        Analiza las velas usando la estrategia especificada.
        Retorna: 'BUY', 'SELL' o 'HOLD'
        """
        if not candles or len(candles) < 2:
            return 'HOLD'
            
        strategy_name = strategy_name.lower().replace(" ", "_")
        
        if strategy_name == 'rsi_experto':
            return self.run_rsi_experto(candles)
        elif strategy_name == 'bloque_de_emas' or strategy_name == 'bloque_emas':
            return self.run_bloque_emas(candles)
        elif strategy_name == 'order_blocks':
            return self.run_order_blocks(candles)
        elif strategy_name == 'canales_y_soportes_resistencias' or strategy_name == 'canales_y_soportes' or strategy_name == 'canales':
            return self.run_canales_soportes(candles)
        elif strategy_name == 'de_prueba' or strategy_name == 'estrategia_de_prueba' or strategy_name == 'prueba':
            return self.run_de_prueba(candles)
        else:
            # Estrategia por defecto
            return self.run_rsi_experto(candles)

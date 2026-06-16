Actúa como un Ingeniero de Software Principal y Desarrollador Experto en Trading Algorítmico con amplia experiencia en Python y la API de MetaTrader 5 (MT5). 

Quiero que crees un Bot de Trading Automatizado con una interfaz web integrada. Debes estructurar el proyecto de forma rigurosa utilizando la arquitectura Modelo-Vista-Controlador (MVC). 

### 📂 Estructura de Archivos Requerida
Genera el sistema respetando exactamente esta distribución de directorios:
- `config.py`: Variables globales, credenciales y rutas.
- `app.py`: Punto de entrada de Flask.
- `models/database.py` y `settings_model.py`: Manejo de SQLite para guardar las configuraciones de riesgo, entradas y estrategia activa.
- `controllers/mt5_controller.py`: Manejo exclusivo de la API de MetaTrader 5.
- `controllers/strategy_loader.py`: Motor matemático para el cálculo de indicadores y patrones de velas.
- `controllers/main_controller.py`: Orquestador que conecta la interfaz web con el flujo de trading.
- `views/templates/base.html` y `dashboard.html`: Interfaz web (Dashboard).
- `views/static/js/main.js` y `css/style.css`: Control asíncrono para actualizar las posiciones en vivo.

### ⚙️ Especificaciones Técnicas y Funcionales

1. Conexión y Sincronización Automática (MT5):
   - El archivo `mt5_controller.py` debe conectarse a la API de MT5.
   - OBLIGATORIO: Debe leer de forma automática los activos (símbolos) disponibles y habilitados en el bróker conectado (`symbol.visible`). No uses listas estáticas de activos.

2. Dashboard Web (Flask + Jinja2 + JS):
   - Diseña un panel visual profesional con modo oscuro estilo trading.
   - Sección de Monitoreo: Debe mostrar en tiempo real (vía fetch/AJAX en JS) el Balance, Equidad, Margen Libre y una tabla dinámica con las posiciones que actualmente están abiertas en la cuenta.
   - Sección de Control: Formularios interactivos para seleccionar la estrategia activa mediante un dropdown, seleccionar el tipo de gestión de riesgo y configurar el tamaño de la entrada (por ejemplo, "1 dólar" o su equivalente en volumen).

3. Motor de Estrategias (`strategy_loader.py`):
   Define las estructuras y funciones necesarias para analizar los datos de las velas e identificar entradas basadas en:
   - RSI Experto: Detección de divergencias en el oscilador RSI combinadas obligatoriamente con la confirmación de patrones de velas japonesas de alta probabilidad (Vela Envolvente, Martillo, etc.).
   - Bloque de EMAs: Análisis con Medias Móviles Exponenciales de 3, 9, 20, 50, 100 y 200 períodos para cruces o rebotes estructurales.
   - Order Blocks: Identificación de zonas de oferta y demanda institucionales y quiebres de estructura (BOS / CHoCH).
   - Canales y Soportes/Resistencias: Trazado dinámico de canales algorítmicos (ascendentes, descendentes y rangos) para operar rupturas o rebotes confirmados con velas.

4. Gestión y Ejecución de Órdenes:
   - El bot debe ser capaz de colocar posiciones directas a mercado (Market Orders) o programar posiciones pendientes (Limit/Stop Orders) automáticamente cuando una estrategia envíe una señal válida, calculando el lote correcto según el riesgo configurado en el Dashboard.
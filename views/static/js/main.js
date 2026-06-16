/* ==========================================================================
   VOLTREX DYNAMIC CONTROLLER
   Lógica JavaScript para interactividad premium y actualizaciones asíncronas
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    // Configuración inicial del estado
    let activeSymbol = "EURUSD";
    let isBotRunning = false;
    let lastKnownPrices = {};
    
    // Referencias a elementos del DOM
    const navBalance = document.getElementById('nav-balance');
    const mt5StatusBadge = document.getElementById('mt5-status-badge');
    const kpiAssetPrice = document.getElementById('kpi-asset-price');
    const kpiEquity = document.getElementById('kpi-equity');
    const kpiFreeMargin = document.getElementById('kpi-free-margin');
    const kpiBotRunning = document.getElementById('kpi-bot-running');
    const positionsTable = document.getElementById('positions-table').querySelector('tbody');
    const positionsCountBadge = document.getElementById('positions-count-badge');
    const consoleLogs = document.getElementById('console-logs');
    const historyItems = document.getElementById('history-items');
    
    // Elementos del Orquestador Central
    const assetsGridContainer = document.getElementById('assets-grid-container');
    const centralSelectSymbol = document.getElementById('central-select-symbol');
    const btnCentralAddSymbol = document.getElementById('btn-central-add-symbol');
    
    // Formularios y botones
    const settingsForm = document.getElementById('settings-form');
    const btnToggleBot = document.getElementById('btn-toggle-bot');
    const btnFaucet = document.getElementById('btn-faucet');
    const btnManualBuy = document.getElementById('btn-manual-buy');
    const btnManualSell = document.getElementById('btn-manual-sell');
    const manualLotInput = document.getElementById('manual-lot');
    const selectRisk = document.getElementById('select-risk');
    const volumeLabel = document.getElementById('volume-label');
    const volumeInput = document.getElementById('input-volume');

    // Cambiar etiqueta del input según el tipo de riesgo
    if (selectRisk) {
        selectRisk.addEventListener('change', () => {
            if (selectRisk.value === 'lote_fijo') {
                volumeLabel.textContent = "Tamaño Entrada (Lotes)";
            } else {
                volumeLabel.textContent = "Riesgo (% del Balance)";
            }
        });
    }

    // ==========================================
    // LOGS DE CONSOLA DE SIMULACIÓN
    // ==========================================
    
    function logToConsole(message, type = 'info') {
        const now = new Date();
        const timeStr = now.toTimeString().split(' ')[0];
        
        let colorClass = 'text-blue';
        if (type === 'success') colorClass = 'text-green';
        if (type === 'error') colorClass = 'text-red';
        if (type === 'warning') colorClass = 'text-gold';
        
        const line = document.createElement('div');
        line.className = `console-line ${colorClass}`;
        line.innerHTML = `<span class="timestamp">[${timeStr}]</span> ${message}`;
        
        consoleLogs.insertBefore(line, consoleLogs.firstChild);
        
        // Mantener máximo 50 líneas
        if (consoleLogs.children.length > 50) {
            consoleLogs.removeChild(consoleLogs.lastChild);
        }
    }

    // ==========================================
    // ACTUALIZACIÓN GENERAL DEL ESTADO (STATUS POLLING)
    // ==========================================
    
    function updateStatus() {
        fetch('/api/status')
            .then(res => res.json())
            .then(data => {
                // 1. Estatus de conexión MT5/Simulador
                const badge = mt5StatusBadge;
                const dot = badge.querySelector('.pulse-dot');
                const text = badge.querySelector('.status-text');
                
                if (data.account) {
                    if (data.account.mock) {
                        dot.className = 'pulse-dot orange';
                        text.textContent = 'Simulación Activa';
                    } else {
                        dot.className = 'pulse-dot green';
                        text.textContent = 'Conectado a MT5';
                    }
                    
                    // 2. Actualización de Balance e KPIs
                    navBalance.textContent = `${data.account.balance.toLocaleString()} ${data.account.currency}`;
                    kpiEquity.textContent = `${data.account.equity.toLocaleString()} ${data.account.currency}`;
                    kpiFreeMargin.textContent = `${data.account.free_margin.toLocaleString()} ${data.account.currency}`;
                    
                    // Si el beneficio total cambia, aplicar color
                    const profit = data.account.profit;
                    if (profit > 0) {
                        kpiEquity.style.color = '#10b981';
                    } else if (profit < 0) {
                        kpiEquity.style.color = '#ef4444';
                    } else {
                        kpiEquity.style.color = '';
                    }
                } else {
                    dot.className = 'pulse-dot grey';
                    text.textContent = 'Desconectado';
                }
                
                // 3. Estatus del Bot Algorítmico
                isBotRunning = data.bot_status.running;
                if (isBotRunning) {
                    btnToggleBot.className = 'bot-toggle-btn running';
                    btnToggleBot.innerHTML = '<i class="fa-solid fa-power-off"></i> APAGAR';
                    kpiBotRunning.textContent = 'Ejecutando';
                    kpiBotRunning.className = 'epoch-value text-green';
                } else {
                    btnToggleBot.className = 'bot-toggle-btn';
                    btnToggleBot.innerHTML = '<i class="fa-solid fa-power-off"></i> ENCEBER';
                    kpiBotRunning.textContent = 'Detenido';
                    kpiBotRunning.className = 'epoch-value text-red';
                }
                
                // Actualizar log en consola si hay cambios en el mensaje del bot
                const botMsg = data.bot_status.message;
                const lastLine = consoleLogs.firstElementChild ? consoleLogs.firstElementChild.textContent : "";
                if (botMsg && !lastLine.includes(botMsg)) {
                    logToConsole(botMsg, isBotRunning ? 'warning' : 'info');
                }
                
                // 4. Tabla de Posiciones en Vivo
                renderPositions(data.positions);
                
                // 5. Historial de transacciones
                renderHistory(data.history);
                
                // 6. Activos en Operación (Panel Orquestador Central)
                renderActiveSymbolsGrid(data.active_symbols);
                
                // 7. Símbolos del Broker (Sincronizar Dropdown Central)
                updateBrokerSymbolsDropdown(data.broker_symbols);
                
                // 8. Actualizar KPI de Precio del activo principal
                if (data.bot_status.price) {
                    const priceVal = data.bot_status.price;
                    const symbolVal = data.bot_status.symbol;
                    const decimals = (priceVal > 100) ? 2 : 5;
                    kpiAssetPrice.textContent = `$${priceVal.toFixed(decimals)}`;
                    document.getElementById('symbol-price-label').textContent = `Precio ${symbolVal}`;
                    activeSymbol = symbolVal;
                }
            })
            .catch(err => console.error("Error en polling status:", err));
    }
    
    // ==========================================
    // RENDERIZADO DEL PANEL ORQUESTADOR CENTRAL
    // ==========================================
    
    function renderActiveSymbolsGrid(activeSymbols) {
        if (!assetsGridContainer) return;
        
        if (!activeSymbols || activeSymbols.length === 0) {
            assetsGridContainer.innerHTML = `
                <div class="no-assets-state">
                    <i class="fa-solid fa-network-wired text-purple" style="font-size: 36px; margin-bottom: 10px; opacity: 0.7;"></i>
                    <p>No hay activos configurados en el orquestador.</p>
                    <span>Utiliza el selector superior para habilitar los activos que deseas operar automáticamente.</span>
                </div>
            `;
            return;
        }
        
        const existingCards = assetsGridContainer.querySelectorAll('.asset-card');
        
        // Si el número de tarjetas o el orden difieren, reconstruimos la grilla
        let needsRebuild = false;
        if (existingCards.length !== activeSymbols.length) {
            needsRebuild = true;
        } else {
            existingCards.forEach((card, idx) => {
                if (card.dataset.symbol !== activeSymbols[idx].symbol) {
                    needsRebuild = true;
                }
            });
        }
        
        if (needsRebuild) {
            let html = '';
            activeSymbols.forEach(sym => {
                const priceDecimals = (sym.price > 100) ? 2 : 5;
                const formattedPrice = sym.price ? sym.price.toFixed(priceDecimals) : '0.00';
                const statusClass = isBotRunning ? 'running' : '';
                const statusText = isBotRunning ? (sym.has_position ? 'Operando (Pos. Abierta)' : 'Monitoreando') : 'Pausado';
                const runningCardClass = isBotRunning ? 'active-running' : '';
                
                html += `
                    <div class="asset-card ${runningCardClass}" data-symbol="${sym.symbol}">
                        <div class="asset-card-header">
                            <div class="asset-info-left">
                                <span class="asset-name">${sym.symbol}</span>
                                <span class="asset-status-badge ${statusClass}">
                                    <span class="badge-dot"></span> <span class="status-lbl">${statusText}</span>
                                </span>
                            </div>
                            <div class="asset-price-wrapper">
                                <span class="asset-price" id="price-${sym.symbol}">$${formattedPrice}</span>
                            </div>
                            <button class="btn-remove-asset" onclick="removeActiveSymbol('${sym.symbol}')" title="Quitar activo">
                                <i class="fa-solid fa-xmark"></i>
                            </button>
                        </div>
                        
                        <div class="asset-card-selectors">
                            <div class="selector-row">
                                <label>Estrategia</label>
                                <div class="selector-wrapper">
                                    <select id="strat-${sym.symbol}" onchange="updateAssetConfig('${sym.symbol}', this.value, document.getElementById('risk-${sym.symbol}').value, document.getElementById('tf-${sym.symbol}').value)">
                                        <option value="rsi_experto" ${sym.strategy === 'rsi_experto' ? 'selected' : ''}>RSI Experto</option>
                                        <option value="bloque_emas" ${sym.strategy === 'bloque_emas' ? 'selected' : ''}>Bloque de EMAs</option>
                                        <option value="order_blocks" ${sym.strategy === 'order_blocks' ? 'selected' : ''}>Order Blocks</option>
                                        <option value="canales" ${sym.strategy === 'canales' ? 'selected' : ''}>Canales y Soportes</option>
                                        <option value="de_prueba" ${sym.strategy === 'de_prueba' ? 'selected' : ''}>Estrategia de Prueba (Test)</option>
                                    </select>
                                </div>
                            </div>

                            <div class="selector-row">
                                <label>Temporalidad</label>
                                <div class="selector-wrapper">
                                    <select id="tf-${sym.symbol}" onchange="updateAssetConfig('${sym.symbol}', document.getElementById('strat-${sym.symbol}').value, document.getElementById('risk-${sym.symbol}').value, this.value)">
                                        <option value="M1" ${sym.timeframe === 'M1' ? 'selected' : ''}>1m</option>
                                        <option value="M5" ${sym.timeframe === 'M5' ? 'selected' : ''}>5m</option>
                                        <option value="M15" ${sym.timeframe === 'M15' ? 'selected' : ''}>15m</option>
                                        <option value="M30" ${sym.timeframe === 'M30' ? 'selected' : ''}>30m</option>
                                        <option value="H1" ${sym.timeframe === 'H1' ? 'selected' : ''}>1h</option>
                                        <option value="H4" ${sym.timeframe === 'H4' ? 'selected' : ''}>4h</option>
                                        <option value="D1" ${sym.timeframe === 'D1' ? 'selected' : ''}>1d</option>
                                    </select>
                                </div>
                            </div>
                            
                            <div class="selector-row">
                                <label>Gestión Riesgo</label>
                                <div class="selector-wrapper">
                                    <select id="risk-${sym.symbol}" onchange="updateAssetConfig('${sym.symbol}', document.getElementById('strat-${sym.symbol}').value, this.value, document.getElementById('tf-${sym.symbol}').value)">
                                        <option value="1:1" ${sym.risk_ratio === '1:1' ? 'selected' : ''}>R:R 1:1</option>
                                        <option value="1:2" ${sym.risk_ratio === '1:2' ? 'selected' : ''}>R:R 1:2</option>
                                        <option value="1:3" ${sym.risk_ratio === '1:3' ? 'selected' : ''}>R:R 1:3</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });
            assetsGridContainer.innerHTML = html;
        } else {
            // Solo actualizar precios y estados en las tarjetas existentes para evitar lag
            activeSymbols.forEach(sym => {
                const card = assetsGridContainer.querySelector(`.asset-card[data-symbol="${sym.symbol}"]`);
                if (card) {
                    // Actualizar precio con parpadeo
                    const priceElem = card.querySelector('.asset-price');
                    if (priceElem) {
                        const priceDecimals = (sym.price > 100) ? 2 : 5;
                        const formattedPrice = `$${sym.price.toFixed(priceDecimals)}`;
                        const lastPrice = lastKnownPrices[sym.symbol];
                        
                        if (lastPrice && sym.price > lastPrice) {
                            priceElem.className = "asset-price up";
                        } else if (lastPrice && sym.price < lastPrice) {
                            priceElem.className = "asset-price down";
                        }
                        
                        priceElem.textContent = formattedPrice;
                        
                        // Volver al color base después de 800ms
                        setTimeout(() => {
                            priceElem.className = "asset-price";
                        }, 800);
                    }
                    
                    // Actualizar badge de estado
                    const badge = card.querySelector('.asset-status-badge');
                    if (badge) {
                        const statusClass = isBotRunning ? 'running' : '';
                        const statusText = isBotRunning ? (sym.has_position ? 'Operando (Pos. Abierta)' : 'Monitoreando') : 'Pausado';
                        badge.className = `asset-status-badge ${statusClass}`;
                        badge.querySelector('.status-lbl').textContent = statusText;
                    }
                    
                    // Actualizar clase de tarjeta
                    if (isBotRunning) {
                        card.classList.add('active-running');
                    } else {
                        card.classList.remove('active-running');
                    }
                    
                    // Actualizar selectores dinámicamente si no están enfocados
                    const selectStrat = card.querySelector(`#strat-${sym.symbol}`);
                    if (selectStrat && document.activeElement !== selectStrat) {
                        selectStrat.value = sym.strategy;
                    }
                    const selectTf = card.querySelector(`#tf-${sym.symbol}`);
                    if (selectTf && document.activeElement !== selectTf) {
                        selectTf.value = sym.timeframe;
                    }
                    const selectRisk = card.querySelector(`#risk-${sym.symbol}`);
                    if (selectRisk && document.activeElement !== selectRisk) {
                        selectRisk.value = sym.risk_ratio;
                    }
                }
            });
        }
        
        // Guardar precios actuales
        activeSymbols.forEach(sym => {
            lastKnownPrices[sym.symbol] = sym.price;
        });
    }
    
    // Guardar configuración del activo en caliente
    window.updateAssetConfig = function(symbol, strategy, riskRatio, timeframe) {
        console.log(`Guardando configuración para ${symbol}: ${strategy} (${riskRatio}) [${timeframe}]`);
        
        fetch('/api/active_symbols/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol: symbol,
                strategy: strategy,
                risk_ratio: riskRatio,
                timeframe: timeframe
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                logToConsole(`Configuración de ${symbol} actualizada: ${strategy} (${riskRatio}) [${timeframe}]`, 'success');
            } else {
                logToConsole(`Error al actualizar configuración: ${data.message}`, 'error');
            }
        })
        .catch(err => logToConsole(`Error al guardar configuración del activo: ${err}`, 'error'));
    };
    
    let lastBrokerSymbolsHash = "";
    
    function updateBrokerSymbolsDropdown(brokerSymbols) {
        if (!brokerSymbols || brokerSymbols.length === 0) return;
        
        const hash = brokerSymbols.join(",");
        if (hash === lastBrokerSymbolsHash) return;
        lastBrokerSymbolsHash = hash;
        
        if (centralSelectSymbol) {
            const currentVal = centralSelectSymbol.value;
            centralSelectSymbol.innerHTML = '';
            
            brokerSymbols.forEach(sym => {
                const opt = document.createElement('option');
                opt.value = sym;
                opt.textContent = sym;
                centralSelectSymbol.appendChild(opt);
            });
            
            if (brokerSymbols.includes(currentVal)) {
                centralSelectSymbol.value = currentVal;
            }
        }
    }
    
    function renderPositions(positions) {
        positionsCountBadge.textContent = `${positions.length} Posiciones`;
        
        if (positions.length === 0) {
            positionsTable.innerHTML = `
                <tr>
                    <td colspan="10" class="text-center text-muted py-4">No hay posiciones abiertas actualmente.</td>
                </tr>
            `;
            return;
        }
        
        let html = '';
        positions.forEach(pos => {
            const pClass = pos.profit >= 0 ? 'text-green' : 'text-red';
            const typeBadge = pos.type === 'BUY' ? 'badge buy' : 'badge sell';
            
            html += `
                <tr>
                    <td><strong>#${pos.ticket}</strong></td>
                    <td>${pos.symbol}</td>
                    <td><span class="${typeBadge}">${pos.type}</span></td>
                    <td>${pos.lot.toFixed(2)}</td>
                    <td>${pos.open_price.toFixed(5)}</td>
                    <td>${pos.current_price.toFixed(5)}</td>
                    <td><strong class="${pClass}">${pos.profit >= 0 ? '+' : ''}${pos.profit.toFixed(2)} USD</strong></td>
                    <td><span class="chart-timeframe-tag">${pos.strategy}</span></td>
                    <td><span class="text-muted" style="font-size:12px;">${pos.open_time}</span></td>
                    <td>
                        <button class="btn-close-trade" onclick="closePosition(${pos.ticket})">
                            <i class="fa-solid fa-xmark"></i> Cerrar
                        </button>
                    </td>
                </tr>
            `;
        });
        positionsTable.innerHTML = html;
    }
    
    function renderHistory(history) {
        if (!history || history.length === 0) {
            historyItems.innerHTML = '<div class="text-center text-muted py-3">No hay historial cerrado aún.</div>';
            return;
        }
        
        let html = '';
        history.forEach(item => {
            const pClass = item.profit >= 0 ? 'text-green' : 'text-red';
            const icon = item.type === 'BUY' ? 'fa-arrow-trend-up text-green' : 'fa-arrow-trend-down text-red';
            
            html += `
                <div class="history-item">
                    <div class="history-item-left">
                        <span class="history-item-symbol">
                            <i class="fa-solid ${icon}"></i> ${item.symbol}
                        </span>
                        <span class="history-item-time">${item.close_time}</span>
                    </div>
                    <div class="history-item-right">
                        <span class="history-item-profit ${pClass}">
                            ${item.profit >= 0 ? '+' : ''}${item.profit.toFixed(2)} USD
                        </span>
                        <span class="history-item-lot">${item.lot.toFixed(2)} lotes</span>
                    </div>
                </div>
            `;
        });
        historyItems.innerHTML = html;
    }

    // ==========================================
    // FUNCIONES GLOBALES PARA CIERRE Y EVENTOS
    // ==========================================
    
    window.closePosition = function(ticket) {
        logToConsole(`Enviando solicitud de cierre para posición #${ticket}...`, 'warning');
        
        fetch('/api/close_trade', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticket: ticket })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                logToConsole(data.message, 'success');
                updateStatus();
            } else {
                logToConsole(`Error al cerrar: ${data.message}`, 'error');
            }
        })
        .catch(err => logToConsole(`Error de red al cerrar: ${err}`, 'error'));
    };

    // ==========================================
    // MANEJADORES DE EVENTOS DEL USUARIO
    // ==========================================
    
    // Guardar configuraciones del bot general (riesgo)
    if (settingsForm) {
        settingsForm.addEventListener('submit', (e) => {
            e.preventDefault();
            
            const risk_type = selectRisk.value;
            const entry_size = volumeInput.value;
            
            fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    strategy: 'rsi_experto', // Fallback, no utilizado directamente
                    risk_type: risk_type,
                    entry_size: entry_size,
                    symbol: activeSymbol
                })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    logToConsole(`Configuración de riesgo general guardada.`, 'success');
                } else {
                    logToConsole(`Error al guardar configuración: ${data.message}`, 'error');
                }
            })
            .catch(err => logToConsole(`Error al guardar: ${err}`, 'error'));
        });
    }
    
    // Encender / Apagar el Bot
    if (btnToggleBot) {
        btnToggleBot.addEventListener('click', () => {
            const newStatus = !isBotRunning;
            
            fetch('/api/toggle_bot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ run: newStatus })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    isBotRunning = data.running;
                    logToConsole(data.message, isBotRunning ? 'success' : 'info');
                    updateStatus();
                }
            })
            .catch(err => logToConsole(`Error al cambiar estado del bot: ${err}`, 'error'));
        });
    }
    
    // Faucet para simular fondos
    if (btnFaucet) {
        btnFaucet.addEventListener('click', () => {
            fetch('/api/faucet', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        logToConsole(data.message, 'success');
                        updateStatus();
                    } else {
                        logToConsole(data.message, 'error');
                    }
                })
                .catch(err => logToConsole(`El Faucet solo funciona en modo simulado.`, 'error'));
        });
    }
    
    // Ejecución Manual BUY
    if (btnManualBuy) {
        btnManualBuy.addEventListener('click', () => {
            const lot = parseFloat(manualLotInput.value) || 0.01;
            logToConsole(`Enviando orden manual de COMPRA en ${activeSymbol}...`, 'warning');
            
            fetch('/api/manual_trade', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol: activeSymbol,
                    order_type: 'BUY',
                    lot: lot
                })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    logToConsole(data.message, 'success');
                    updateStatus();
                } else {
                    logToConsole(`Error en compra manual: ${data.message}`, 'error');
                }
            })
            .catch(err => logToConsole(`Error de red: ${err}`, 'error'));
        });
    }
    
    // Ejecución Manual SELL
    if (btnManualSell) {
        btnManualSell.addEventListener('click', () => {
            const lot = parseFloat(manualLotInput.value) || 0.01;
            logToConsole(`Enviando orden manual de VENTA en ${activeSymbol}...`, 'warning');
            
            fetch('/api/manual_trade', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol: activeSymbol,
                    order_type: 'SELL',
                    lot: lot
                })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    logToConsole(data.message, 'success');
                    updateStatus();
                } else {
                    logToConsole(`Error en venta manual: ${data.message}`, 'error');
                }
            })
            .catch(err => logToConsole(`Error de red: ${err}`, 'error'));
        });
    }

    // Agregar Símbolo desde el Panel Orquestador Central
    if (btnCentralAddSymbol) {
        btnCentralAddSymbol.addEventListener('click', () => {
            const symbol = centralSelectSymbol.value;
            if (!symbol) return;
            
            logToConsole(`Habilitando ${symbol} en el orquestador automático...`, 'warning');
            
            fetch('/api/active_symbols/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol: symbol })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    logToConsole(data.message, 'success');
                    updateStatus();
                } else {
                    logToConsole(data.message, 'error');
                }
            })
            .catch(err => logToConsole(`Error al habilitar activo: ${err}`, 'error'));
        });
    }
    
    // Quitar Símbolo (Global para poder ser llamado desde onclick de las tarjetas)
    window.removeActiveSymbol = function(symbol) {
        logToConsole(`Removiendo ${symbol} de la lista de operación automática...`, 'warning');
        
        fetch('/api/active_symbols/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol: symbol })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                logToConsole(data.message, 'success');
                updateStatus();
            } else {
                logToConsole(data.message, 'error');
            }
        })
        .catch(err => logToConsole(`Error al remover símbolo: ${err}`, 'error'));
    };

    // Aplicar Configuración Masiva a todos los activos
    const btnApplyGlobalConfig = document.getElementById('btn-apply-global-config');
    if (btnApplyGlobalConfig) {
        btnApplyGlobalConfig.addEventListener('click', () => {
            const strategy = document.getElementById('global-select-strategy').value;
            const timeframe = document.getElementById('global-select-timeframe').value;
            const riskRatio = document.getElementById('global-select-risk').value;
            
            logToConsole(`Aplicando configuración masiva: ${strategy} (${riskRatio}) [${timeframe}] a todos los activos...`, 'warning');
            
            fetch('/api/active_symbols/update_all', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    strategy: strategy,
                    risk_ratio: riskRatio,
                    timeframe: timeframe
                })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    logToConsole(data.message, 'success');
                    updateStatus();
                } else {
                    logToConsole(data.message, 'error');
                }
            })
            .catch(err => logToConsole(`Error al aplicar configuración global: ${err}`, 'error'));
        });
    }

    // Inicializar y sincronizar datos
    updateStatus();
    
    // Configurar temporizadores periódicos (polling cada 2 segundos)
    setInterval(updateStatus, 2000);
});

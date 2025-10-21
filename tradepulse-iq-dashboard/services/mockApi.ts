// FIX: Import enums and types from the dedicated types file.
import {
    TradeDirection,
    BotStatusState,
    PatternStatus,
    TrainingPhase,
    ExchangeConnectionStatus,
} from '../types';
import type {
    PortfolioResponse,
    Trade,
    EquityPoint,
    PerformanceMetrics,
    BotStatus,
    PatternPerformance,
    ActiveTrade,
    TrainedAsset,
    TrainedAssetDetails,
    AssetRanking,
    TrainingStatus,
    TrainingResults,
    RegimePerformance,
    ExchangePerformance,
    PatternParameters,
    PatternImplementation,
    ExchangeConnection,
} from '../types';

// --- MOCK DATA STORE ---

const users = ['user1', 'user2'];
const exchanges = ['Binance', 'Coinbase', 'Bybit', 'Kraken', 'OKX', 'KuCoin'];

const mockData: { [userId: string]: any } = {};

const generateRandomFloat = (min: number, max: number, decimals: number = 2) => {
    return parseFloat((Math.random() * (max - min) + min).toFixed(decimals));
};

const generateRandomInt = (min: number, max: number) => {
    return Math.floor(Math.random() * (max - min + 1)) + min;
};

const generatePatternParameters = (patternName: string): PatternParameters => {
    const primaryTimeframe = (['15m', '1h'] as const)[generateRandomInt(0,1)];
    const macroTimeframe = (['4h', '1d'] as const)[generateRandomInt(0,1)];

    let primarySignal: PatternParameters['primarySignal'] = {};
    if (patternName.includes('Reversal')) {
        primarySignal = {
            rsiPeriod: generateRandomInt(12, 18),
            overbought: generateRandomInt(70, 80),
            oversold: generateRandomInt(20, 30),
        }
    } else {
        primarySignal = {
            lookback: generateRandomInt(20, 50),
            threshold: generateRandomFloat(1.5, 2.5),
        }
    }

    return {
        primaryTimeframe,
        macroTimeframe,
        primarySignal,
        macroConfirmation: {
            trendFilter: (['EMA_200', 'MACD_Cross', 'ADX'] as const)[generateRandomInt(0, 2)],
            requiredState: (['Above', 'Positive', 'Trending'] as const)[generateRandomInt(0, 2)],
        },
        riskManagement: {
            riskRewardRatio: generateRandomFloat(1.5, 3.0),
            stopLossType: (['ATR', 'Percentage'] as const)[generateRandomInt(0, 1)],
            stopLossValue: generateRandomFloat(1, 3),
        }
    }
}

const mockTrainedAssetsList = [
    // TIER 1
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'MATIC/USDT', 'LINK/USDT',
    'UNI/USDT', 'ATOM/USDT', 'LTC/USDT', 'NEAR/USDT', 'TRX/USDT', 'ARB/USDT', 'OP/USDT', 'INJ/USDT', 'TIA/USDT', 'SUI/USDT',
    // TIER 2
    'DOGE/USDT', 'SHIB/USDT', 'TON/USDT', 'APT/USDT', 'STX/USDT', 'FIL/USDT', 'IMX/USDT', 'VET/USDT', 'HBAR/USDT', 'AAVE/USDT',
    'MKR/USDT', 'GRT/USDT', 'ALGO/USDT', 'ICP/USDT', 'ETC/USDT', 'XLM/USDT', 'RUNE/USDT', 'FTM/USDT', 'SAND/USDT', 'MANA/USDT',
    'AXS/USDT', 'CRV/USDT', 'SNX/USDT', 'LDO/USDT', 'THETA/USDT', 'EOS/USDT', 'EGLD/USDT', 'KCS/USDT', 'XMR/USDT', 'FLOW/USDT',
    'APE/USDT', 'CHZ/USDT', 'GMT/USDT', 'QNT/USDT', 'KAVA/USDT', 'ZIL/USDT', 'ENJ/USDT', '1INCH/USDT', 'BAT/USDT', 'COMP/USDT',
    // TIER 3
    'GALA/USDT', 'ROSE/USDT', 'FXS/USDT', 'ZRX/USDT', 'ENS/USDT', 'DASH/USDT', 'ZEC/USDT', 'WAVES/USDT', 'XTZ/USDT', 'ONE/USDT',
    'CELO/USDT', 'IOTX/USDT', 'AR/USDT', 'MINA/USDT', 'KSM/USDT', 'YFI/USDT', 'SUSHI/USDT', 'BAL/USDT', 'UMA/USDT', 'REN/USDT',
    'ANKR/USDT', 'STORJ/USDT', 'SKL/USDT', 'CVC/USDT', 'NMR/USDT', 'LRC/USDT', 'OMG/USDT', 'CELR/USDT', 'BNT/USDT', 'RLC/USDT',
    'AUDIO/USDT', 'DYDX/USDT', 'OCEAN/USDT', 'RSR/USDT', 'FET/USDT', 'AGIX/USDT', 'RNDR/USDT', 'WOO/USDT', 'BLUR/USDT', 'MASK/USDT',
    'JASMY/USDT', 'HIVE/USDT', 'GLM/USDT', 'QTUM/USDT', 'ICX/USDT', 'ONT/USDT', 'LSK/USDT', 'SC/USDT', 'PEOPLE/USDT', 'SPELL/USDT',
    'SYN/USDT', 'PERP/USDT', 'CVX/USDT', 'ALICE/USDT', 'TLM/USDT', 'ILV/USDT', 'HIGH/USDT', 'PAXG/USDT', 'NEXO/USDT', 'HNT/USDT',
    // TIER 4
    'HOT/USDT', 'REQ/USDT', 'MTL/USDT', 'GNO/USDT', 'STG/USDT', 'GMX/USDT', 'RETH/USDT', 'RPL/USDT', 'LOOKS/USDT', 'BETA/USDT',
    'BICO/USDT', 'ACH/USDT', 'MOVR/USDT', 'GLMR/USDT', 'POWR/USDT', 'REP/USDT', 'AST/USDT', 'DIA/USDT', 'PROM/USDT', 'ORN/USDT',
    'TRIBE/USDT', 'FARM/USDT', 'BADGER/USDT', 'DENT/USDT', 'WAN/USDT', 'ARPA/USDT', 'DATA/USDT', 'CTSI/USDT', 'AMP/USDT', 'MLN/USDT',
    'OXT/USDT', 'POLY/USDT', 'FOR/USDT', 'NKN/USDT', 'BAND/USDT', 'SXP/USDT', 'KEY/USDT', 'WIN/USDT', 'STMX/USDT', 'DOCK/USDT',
    'PLA/USDT', 'OM/USDT', 'RAD/USDT', 'QUICK/USDT', 'SUPER/USDT', 'TVK/USDT', 'VOXEL/USDT', 'ERN/USDT', 'RARE/USDT', 'XVG/USDT',
    'BTT/USDT', 'CKB/USDT', 'LINA/USDT', 'CLV/USDT', 'POND/USDT', 'VITE/USDT', 'ADX/USDT', 'SFP/USDT', 'HARD/USDT', 'ALPACA/USDT'
];

const symbols = mockTrainedAssetsList;
const patternNames = ['Liquidity Sweep Reversal', 'Capitulation Reversal', 'Failed Breakdown (Spring)', 'Supply Shock (Macro)'];
const patternInitials = ['LSR', 'CR', 'FB', 'SS'];

const initializeUserData = (userId: string) => {
    if (mockData[userId]) return;

    const equity = generateRandomFloat(100000, 150000);
    const cash = equity * generateRandomFloat(0.1, 0.4);

    mockData[userId] = {
        portfolio: {
            timestamp: new Date().toISOString(),
            equity: equity,
            cash: cash,
        },
        trades: Array.from({ length: 200 }).map((_, i) => ({
            id: i,
            timestamp: new Date(Date.now() - i * 60000 * generateRandomInt(5, 30)).toISOString(),
            symbol: symbols[generateRandomInt(0, symbols.length - 1)],
            direction: Math.random() > 0.5 ? TradeDirection.BUY : TradeDirection.SELL,
            quantity: generateRandomFloat(0.01, 1),
            price: generateRandomFloat(20000, 70000),
            fill_cost: generateRandomFloat(100, 5000),
            pnl: generateRandomFloat(-200, 200),
        })).sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()),
        logs: [
            "INFO: Bot initialized successfully.",
            "DEBUG: Checking for new signals...",
            "INFO: Signal found for BTC/USDT - Liquidity Sweep Reversal.",
            "INFO: Placing BUY order for 0.05 BTC/USDT.",
            "WARN: High market volatility detected.",
            "INFO: Order filled successfully.",
            "ERROR: Failed to connect to exchange API (retrying...).",
            "INFO: Reconnected to exchange API.",
        ],
        history: Array.from({ length: 100 }).map((_, i) => ({
            timestamp: new Date(Date.now() - (100 - i) * 3600000).toISOString(),
            equity: equity * (1 + generateRandomFloat(-0.05, 0.05) + i * 0.0005),
        })),
        performance: {
            totalPL: { value: generateRandomFloat(5000, 15000), percentage: generateRandomFloat(0.05, 0.15) },
            sharpeRatio: generateRandomFloat(1.2, 2.5),
            maxDrawdown: generateRandomFloat(0.05, 0.12),
            winLossRatio: generateRandomFloat(1.5, 2.8),
            avgProfit: generateRandomFloat(80, 150),
            avgLoss: generateRandomFloat(-60, -40),
            totalTrades: 200,
        },
        patterns: patternNames.map((name, i) => ({
            id: `pattern-${i}`,
            name,
            status: Math.random() > 0.2 ? PatternStatus.ACTIVE : PatternStatus.PAUSED,
            totalPL: generateRandomFloat(-500, 5000),
            winLossRatio: generateRandomFloat(0.8, 3.0),
            totalTrades: generateRandomInt(20, 80),
            parameters: { // Simplified for this view
                timeframe: '15m',
                rsi_period: generateRandomInt(10, 20),
                stop_loss_pct: generateRandomFloat(1, 3),
            },
        })),
        activeTrades: Array.from({ length: generateRandomInt(0, 3) }).map((_, i) => {
            const direction = Math.random() > 0.5 ? TradeDirection.BUY : TradeDirection.SELL;
            const entryPrice = generateRandomFloat(30000, 60000);
            const currentPrice = entryPrice + generateRandomFloat(-500, 500);
            const stopLoss = direction === TradeDirection.BUY ? entryPrice * 0.98 : entryPrice * 1.02;
            const takeProfit = direction === TradeDirection.BUY ? entryPrice * 1.05 : entryPrice * 0.95;
            const quantity = generateRandomFloat(0.01, 0.2);

            return {
                id: `active-${i}`,
                symbol: symbols[i],
                direction,
                entryPrice,
                quantity,
                currentPL: (currentPrice - entryPrice) * quantity * (direction === TradeDirection.BUY ? 1 : -1),
                takeProfit,
                stopLoss,
                patternName: patternNames[i],
                startTimestamp: new Date(Date.now() - i * 3600000).toISOString(),
                currentPrice: currentPrice,
            };
        }),
        trainedAssets: symbols.map(symbol => ({
            symbol,
            patterns: patternNames.map((_, i) => ({
                patternId: `pattern-${i}`,
                initials: patternInitials[i],
                totalPL: generateRandomFloat(-1000, 3000),
                status: Math.random() > 0.3 ? PatternStatus.ACTIVE : PatternStatus.PAUSED,
            })),
        })),
        assetDetails: symbols.reduce((acc, symbol) => {
            acc[symbol] = {
                symbol,
                patterns: patternNames.map((name, i) => {
                    const regimes: RegimePerformance[] = (['Bull Market', 'Bear Market', 'Sideways'] as const).map(regimeName => {
                        const exchangePerformance: ExchangePerformance[] = exchanges.map(ex => {
                            let baseWR = 0.55;
                            if(regimeName === 'Bull Market') baseWR = 0.65;
                            if(regimeName === 'Bear Market') baseWR = 0.45;
                            
                            let avgSlippage, avgFees;
                            let latencyRange = [50, 250];

                            // Adjust WR and other metrics based on exchange profile (fees, slippage)
                            switch(ex) {
                                case 'Binance': 
                                    baseWR += 0.05; avgSlippage = generateRandomFloat(0.0005, 0.0015); avgFees = generateRandomFloat(0.00075, 0.001); latencyRange = [50, 150]; break;
                                case 'Coinbase': 
                                    baseWR -= 0.08; avgSlippage = generateRandomFloat(0.0010, 0.0025); avgFees = generateRandomFloat(0.004, 0.006); latencyRange = [100, 300]; break;
                                case 'Bybit': 
                                    baseWR += 0.04; avgSlippage = generateRandomFloat(0.0008, 0.0020); avgFees = generateRandomFloat(0.001, 0.001); latencyRange = [80, 200]; break;
                                case 'Kraken': 
                                    baseWR -= 0.03; avgSlippage = generateRandomFloat(0.0015, 0.0030); avgFees = generateRandomFloat(0.0016, 0.0026); latencyRange = [150, 350]; break;
                                case 'OKX':
                                    baseWR += 0.05; avgSlippage = generateRandomFloat(0.0010, 0.0025); avgFees = generateRandomFloat(0.0008, 0.001); latencyRange = [60, 180]; break;
                                case 'KuCoin':
                                    baseWR -= 0.04; avgSlippage = generateRandomFloat(0.0015, 0.0035); avgFees = generateRandomFloat(0.001, 0.001); latencyRange = [120, 300]; break;
                                default:
                                     avgSlippage = generateRandomFloat(0.001, 0.002); avgFees = generateRandomFloat(0.001, 0.002);
                            }

                            const totalTrades = generateRandomInt(5, 20);
                            // Make winrate more sensitive to costs for realism
                            const winRate = generateRandomFloat(baseWR - 0.05, baseWR + 0.1) * (1 - avgFees * 10); // Higher fees slightly reduce winrate
                            const avgProfit = generateRandomFloat(150, 400);
                            const avgLoss = generateRandomFloat(-90, -140);
                            const grossPL = (totalTrades * winRate * avgProfit) + (totalTrades * (1-winRate) * avgLoss);
                            const totalCost = totalTrades * (avgFees + avgSlippage) * 20000; // Simplified cost model based on avg position
                            
                            return {
                                exchange: ex,
                                status: Math.random() > 0.4 ? PatternStatus.ACTIVE : PatternStatus.PAUSED,
                                winRate,
                                avgProfit,
                                avgLoss,
                                totalTrades,
                                totalPL: grossPL - totalCost,
                                avgSlippage: avgSlippage,
                                avgFees: avgFees,
                                avgLatencyMs: generateRandomInt(latencyRange[0], latencyRange[1]),
                            }
                        });

                        return {
                            regime: regimeName,
                            status: Math.random() > 0.3 ? PatternStatus.ACTIVE : PatternStatus.PAUSED,
                            exchangePerformance
                        }
                    });
                    
                    const allTrades = regimes.flatMap(r => r.exchangePerformance);
                    const totalTrades = allTrades.reduce((sum, t) => sum + t.totalTrades, 0);
                    const totalWinTrades = allTrades.reduce((sum, t) => sum + (t.totalTrades * t.winRate), 0);
                    const totalProfit = allTrades.reduce((sum, t) => sum + (t.totalTrades * t.winRate * t.avgProfit), 0);
                    const totalLoss = allTrades.reduce((sum, t) => sum + (t.totalTrades * (1 - t.winRate) * t.avgLoss), 0);
                    
                    return {
                        id: `pattern-${i}`,
                        name,
                        status: Math.random() > 0.3 ? PatternStatus.ACTIVE : PatternStatus.PAUSED,
                        parameters: generatePatternParameters(name),
                        trainedHistory: `${generateRandomInt(6, 24)} months`,
                        analytics: {
                             winRate: totalTrades > 0 ? totalWinTrades / totalTrades : 0,
                             avgProfit: (totalWinTrades > 0) ? totalProfit / totalWinTrades : 0,
                             avgLoss: (totalTrades - totalWinTrades > 0) ? totalLoss / (totalTrades - totalWinTrades) : 0,
                        },
                        regimePerformance: regimes,
                        recentTrades: Array.from({ length: generateRandomInt(3, 10) }).map((_, j) => ({
                            id: j,
                            timestamp: new Date(Date.now() - j * 86400000).toISOString(),
                            symbol,
                            direction: Math.random() > 0.5 ? TradeDirection.BUY : TradeDirection.SELL,
                            quantity: generateRandomFloat(0.01, 1),
                            price: generateRandomFloat(20000, 70000),
                            fill_cost: generateRandomFloat(100, 5000),
                            pnl: generateRandomFloat(-150, 250),
                        }))
                    };
                })
            };
            return acc;
        }, {} as { [symbol: string]: TrainedAssetDetails }),
        exchangeConnections: userId === 'user1' ? [
            {
                id: 'conn-1',
                exchangeName: 'Binance',
                nickname: 'Main Binance Account',
                apiKey: 'abc...xyz',
                apiSecret: 'sec...ret',
                status: ExchangeConnectionStatus.CONNECTED,
            },
            {
                id: 'conn-2',
                exchangeName: 'Coinbase',
                nickname: 'Coinbase Pro',
                apiKey: '123...789',
                apiSecret: 'p@s...wrd',
                status: ExchangeConnectionStatus.ERROR,
            },
        ] : [],
    };
};

users.forEach(initializeUserData);

// -- DYNAMIC UPDATES --

setInterval(() => {
    users.forEach(userId => {
        if (!mockData[userId]) return;

        // Update portfolio
        const portfolio = mockData[userId].portfolio;
        const change = generateRandomFloat(-500, 500);
        portfolio.equity += change;
        if (Math.random() > 0.5) {
            portfolio.cash += change;
        }
        portfolio.timestamp = new Date().toISOString();

        // Update history
        mockData[userId].history.shift();
        mockData[userId].history.push({
            timestamp: new Date().toISOString(),
            equity: portfolio.equity,
        });

        // Add a log
        const logMessages = [
            "DEBUG: Ping successful.",
            "INFO: Market data updated.",
            "WARN: Slippage detected on last order.",
        ];
        mockData[userId].logs.push(logMessages[generateRandomInt(0, logMessages.length - 1)]);
        if (mockData[userId].logs.length > 100) mockData[userId].logs.shift();
        
        // Add a trade sometimes
        if (Math.random() < 0.05) {
            const newTrade = {
                id: mockData[userId].trades.length,
                timestamp: new Date().toISOString(),
                symbol: symbols[generateRandomInt(0, symbols.length - 1)],
                direction: Math.random() > 0.5 ? TradeDirection.BUY : TradeDirection.SELL,
                quantity: generateRandomFloat(0.01, 1),
                price: generateRandomFloat(20000, 70000),
                fill_cost: generateRandomFloat(100, 5000),
                pnl: generateRandomFloat(-200, 200),
            };
            mockData[userId].trades.unshift(newTrade);
            if (mockData[userId].trades.length > 200) mockData[userId].trades.pop();
            mockData[userId].performance.totalTrades++;
        }

        // Update active trades
        mockData[userId].activeTrades.forEach((trade: ActiveTrade) => {
            const priceChange = generateRandomFloat(-100, 100);
            trade.currentPrice = (trade.currentPrice ?? trade.entryPrice) + priceChange;
            trade.currentPL = (trade.currentPrice - trade.entryPrice) * trade.quantity * (trade.direction === TradeDirection.BUY ? 1 : -1);
        });
        
    });
}, 2000);


// --- API FUNCTIONS ---

const delay = (ms: number) => new Promise(res => setTimeout(res, ms));

export const getPortfolio = async (userId: string): Promise<PortfolioResponse> => {
    await delay(200);
    return { portfolio: mockData[userId].portfolio, holdings: [] };
};

export const getTrades = async (userId: string): Promise<Trade[]> => {
    await delay(200);
    return mockData[userId].trades;
};

export const getLogs = async (userId: string): Promise<string[]> => {
    await delay(100);
    return mockData[userId].logs;
};

export const getPortfolioHistory = async (userId: string): Promise<EquityPoint[]> => {
    await delay(300);
    return mockData[userId].history;
};

export const getPerformance = async (userId: string): Promise<PerformanceMetrics> => {
    await delay(250);
    return mockData[userId].performance;
};

export const getStatus = async (): Promise<BotStatus> => {
    await delay(50);
    // Let status change occasionally
    const rand = Math.random();
    if (rand < 0.95) return { status: BotStatusState.RUNNING };
    if (rand < 0.99) return { status: BotStatusState.STOPPED };
    return { status: BotStatusState.FAILED };
};

export const getPatternsPerformance = async (userId: string): Promise<PatternPerformance[]> => {
    await delay(350);
    return mockData[userId].patterns;
};

export const getActiveTrades = async (userId: string): Promise<ActiveTrade[]> => {
    await delay(150);
    return mockData[userId].activeTrades;
};

export const getTrainedAssets = async (userId: string): Promise<TrainedAsset[]> => {
    await delay(400);
    // Use the full list for the sidebar as well
    return mockData[userId].trainedAssets.filter((asset: TrainedAsset) => symbols.includes(asset.symbol));
}

export const getAssetDetails = async (userId: string, assetSymbol: string): Promise<TrainedAssetDetails> => {
    await delay(500);
    if (!mockData[userId].assetDetails[assetSymbol]) {
        // Fallback for symbols that might not be pre-generated
        return { symbol: assetSymbol, patterns: [] };
    }
    return mockData[userId].assetDetails[assetSymbol];
}


export const togglePatternStatusForAsset = async (userId: string, assetSymbol: string, patternId: string): Promise<void> => {
    await delay(300);
    const asset = mockData[userId].assetDetails[assetSymbol];
    if (asset) {
        const pattern = asset.patterns.find(p => p.id === patternId);
        if (pattern) {
            pattern.status = pattern.status === PatternStatus.ACTIVE ? PatternStatus.PAUSED : PatternStatus.ACTIVE;
        }
    }
     const trainedAsset = mockData[userId].trainedAssets.find((a: TrainedAsset) => a.symbol === assetSymbol);
    if (trainedAsset) {
        const pattern = trainedAsset.patterns.find(p => p.patternId === patternId);
        if (pattern) {
            pattern.status = pattern.status === PatternStatus.ACTIVE ? PatternStatus.PAUSED : PatternStatus.ACTIVE;
        }
    }
    return Promise.resolve();
};

export const togglePatternRegimeStatus = async (userId: string, assetSymbol: string, patternId: string, regimeName: string): Promise<void> => {
    await delay(300);
    const asset = mockData[userId].assetDetails[assetSymbol];
    if (asset) {
        const pattern = asset.patterns.find(p => p.id === patternId);
        if (pattern) {
            const regime = pattern.regimePerformance.find(r => r.regime === regimeName);
            if (regime) {
                const newStatus = regime.status === PatternStatus.ACTIVE ? PatternStatus.PAUSED : PatternStatus.ACTIVE;
                regime.status = newStatus;
                // Also toggle all child exchanges
                regime.exchangePerformance.forEach(ex => ex.status = newStatus);
            }
        }
    }
    return Promise.resolve();
};

export const togglePatternRegimeExchangeStatus = async (userId: string, assetSymbol: string, patternId: string, regimeName: string, exchangeName: string): Promise<void> => {
    await delay(200);
    const asset = mockData[userId].assetDetails[assetSymbol];
    if (asset) {
        const pattern = asset.patterns.find(p => p.id === patternId);
        if (pattern) {
            const regime = pattern.regimePerformance.find(r => r.regime === regimeName);
            if (regime) {
                const exchange = regime.exchangePerformance.find(ex => ex.exchange === exchangeName);
                if(exchange) {
                    exchange.status = exchange.status === PatternStatus.ACTIVE ? PatternStatus.PAUSED : PatternStatus.ACTIVE;
                }
            }
        }
    }
    return Promise.resolve();
};


export const retrainAssetWithFeedback = async (userId: string, assetSymbol: string, feedback: string): Promise<void> => {
    await delay(2500); // Simulate a longer retraining process
    const asset = mockData[userId].assetDetails[assetSymbol];
    if (asset) {
        // Simulate improvement based on feedback
        asset.patterns.forEach(pattern => {
            // Improve overall analytics
            pattern.analytics.winRate *= generateRandomFloat(1.01, 1.08);
            pattern.analytics.avgProfit *= generateRandomFloat(1.0, 1.05);
            pattern.analytics.avgLoss *= generateRandomFloat(0.95, 1.0); // Loss becomes less negative
            
            // Improve regime performance
            pattern.regimePerformance.forEach(regime => {
                regime.exchangePerformance.forEach(ex => {
                    ex.winRate *= generateRandomFloat(1.02, 1.1);
                    ex.avgProfit *= generateRandomFloat(1.01, 1.06);
                    ex.avgLoss *= generateRandomFloat(0.94, 0.99);
                    ex.totalPL *= generateRandomFloat(1.1, 1.3);
                    ex.avgSlippage *= generateRandomFloat(0.85, 0.95); // Reduce slippage
                })
            });

            // Tweak a parameter
            if (pattern.parameters.primarySignal.lookback) {
                 pattern.parameters.primarySignal.lookback = generateRandomInt(
                    (pattern.parameters.primarySignal.lookback as number) * 0.9,
                    (pattern.parameters.primarySignal.lookback as number) * 1.1
                );
            }
            if (pattern.parameters.riskManagement.riskRewardRatio) {
                pattern.parameters.riskManagement.riskRewardRatio *= generateRandomFloat(1.0, 1.1);
            }
        });
    }
    return Promise.resolve();
}


// --- AI TRAINER MOCKS ---

const getTierFromIndex = (index: number) => {
    if (index < 20) return 1; // TIER 1
    if (index < 60) return 2; // TIER 2
    if (index < 120) return 3; // TIER 3
    return 4; // TIER 4
}

const generateReason = (vol: number, liq: number): string => {
    if (liq > 85 && vol > 70) return "Excellent volatility and deep liquidity provide ideal conditions.";
    if (liq > 70 && vol > 60) return "Strong liquidity and consistent patterns make for a reliable candidate.";
    if (liq < 50) return "Lower liquidity suggests caution, but volatility is present.";
    if (vol < 50) return "Moderate volatility may limit opportunities but offers stability.";
    return "Balanced characteristics offer a solid training foundation.";
}

export const getAssetRankings = async (): Promise<AssetRanking[]> => {
    await delay(1000);

    const rankings = mockTrainedAssetsList.map((symbol, index): AssetRanking => {
        const tier = getTierFromIndex(index);
        // FIX: Explicitly type all variables in the declaration. The original code only typed `riskLevel`,
        // leaving the others as `any`, which caused a type inference issue for `dataAvailability`.
        let suitabilityScore: number, volatilityIndex: number, liquidityIndex: number, riskLevel: 'Low' | 'Medium' | 'High';
        
        switch(tier) {
            case 1:
                suitabilityScore = generateRandomInt(85, 98);
                volatilityIndex = generateRandomInt(70, 95);
                liquidityIndex = generateRandomInt(90, 100);
                riskLevel = Math.random() < 0.6 ? 'Medium' : 'Low';
                break;
            case 2:
                suitabilityScore = generateRandomInt(70, 84);
                volatilityIndex = generateRandomInt(60, 90);
                liquidityIndex = generateRandomInt(75, 95);
                riskLevel = Math.random() < 0.7 ? 'Medium' : 'High';
                break;
            case 3:
                suitabilityScore = generateRandomInt(55, 69);
                volatilityIndex = generateRandomInt(50, 80);
                liquidityIndex = generateRandomInt(60, 85);
                riskLevel = Math.random() < 0.5 ? 'Medium' : 'High';
                break;
            case 4:
            default:
                suitabilityScore = generateRandomInt(40, 54);
                volatilityIndex = generateRandomInt(45, 95); // Can be volatile
                liquidityIndex = generateRandomInt(40, 75);
                riskLevel = 'High';
                break;
        }
        
        const temporaryRiskLevel = riskLevel;

        return {
            symbol,
            suitabilityScore,
            volatilityIndex,
            liquidityIndex,
            dataAvailability: liquidityIndex > 80 ? 'Excellent' : liquidityIndex > 60 ? 'Good' : 'Fair',
            reason: generateReason(volatilityIndex, liquidityIndex),
            estimatedTime: `${generateRandomInt(15, 45)} mins`,
            riskLevel: temporaryRiskLevel,
        };
    });

    return rankings.sort((a, b) => b.suitabilityScore - a.suitabilityScore);
}

const trainingJobs: { [jobId: string]: any } = {};

export const startTraining = async (symbol: string): Promise<{ jobId: string }> => {
    await delay(200);
    const jobId = `job_${Date.now()}`;
    trainingJobs[jobId] = {
        symbol,
        phase: TrainingPhase.DATA_COLLECTION,
        progress: 0,
        startTime: Date.now(),
    };
    return { jobId };
};

const phases = [
    { phase: TrainingPhase.DATA_COLLECTION, duration: 4000, message: "Fetching 2+ years of OHLCV data and identifying market regimes..." },
    { phase: TrainingPhase.VIABILITY_ASSESSMENT, duration: 6000, message: "Assessing viability of 4 core patterns on historical data..." },
    { phase: TrainingPhase.TIMEFRAME_TESTING, duration: 8000, message: "Testing viable patterns on 1h, 4h, 1d with hierarchy filters..." },
    { phase: TrainingPhase.OPTIMIZATION, duration: 15000, message: "Running Bayesian optimization (200 iterations) on best timeframe..." },
    { phase: TrainingPhase.VALIDATION, duration: 10000, message: "Performing 4-window walk-forward validation on out-of-sample data..." },
    { phase: TrainingPhase.ROBUSTNESS, duration: 8000, message: "Executing Monte Carlo (1000 runs) and Black Swan simulations..." },
    { phase: TrainingPhase.SCORING, duration: 3000, message: "Calculating final confidence score based on all performance metrics..." },
    { phase: TrainingPhase.COMPLETE, duration: 0, message: "Training process complete." },
];

export const getTrainingStatus = async (jobId: string): Promise<TrainingStatus | null> => {
    await delay(100);
    const job = trainingJobs[jobId];
    if (!job) return null;

    const elapsedTime = Date.now() - job.startTime;
    let cumulativeDuration = 0;
    let currentPhaseIndex = 0;

    for (let i = 0; i < phases.length; i++) {
        cumulativeDuration += phases[i].duration;
        if (elapsedTime < cumulativeDuration) {
            currentPhaseIndex = i;
            break;
        }
        if (i === phases.length - 1) currentPhaseIndex = i; // Complete
    }
    
    if (job.phase !== phases[currentPhaseIndex].phase) {
        job.phase = phases[currentPhaseIndex].phase;
        job.phaseStartTime = Date.now() - (elapsedTime - (cumulativeDuration - phases[currentPhaseIndex].duration));
    }
    
    if (!job.phaseStartTime) job.phaseStartTime = job.startTime;

    const totalDuration = phases.reduce((acc, p) => acc + p.duration, 0);
    const progress = Math.min(100, Math.round((elapsedTime / totalDuration) * 100));
    const eta = Math.max(0, Math.round((totalDuration - elapsedTime) / 1000));
    
    const status: TrainingStatus = {
        jobId,
        assetSymbol: job.symbol,
        phase: job.phase,
        progress,
        message: phases[currentPhaseIndex].message,
        eta: `${Math.floor(eta / 60)}m ${eta % 60}s`,
    };

    if (currentPhaseIndex >= 1) { // After viability assessment
         if (!job.patternAnalysis) {
            const patterns = [
                { name: 'Liquidity Sweep Reversal', winRate: generateRandomFloat(65, 71, 0), signals: generateRandomInt(30, 60) },
                { name: 'Capitulation Reversal', winRate: generateRandomFloat(65, 69, 0), signals: generateRandomInt(15, 30) },
                { name: 'Failed Breakdown (Spring)', winRate: generateRandomFloat(55, 62, 0), signals: generateRandomInt(25, 40) },
                { name: 'Supply Shock (Macro)', winRate: generateRandomFloat(75, 83, 0), signals: generateRandomInt(2, 6) },
            ];

            job.patternAnalysis = patterns.map(p => {
                let status: 'Viable' | 'Marginal' | 'Not Viable';
                if (p.winRate >= 60) {
                    status = 'Viable';
                } else if (p.winRate >= 55) {
                    status = 'Marginal';
                } else {
                    status = 'Not Viable';
                }
                return { ...p, status };
            }).sort(() => 0.5 - Math.random()); // Randomize order
        }
        status.patternAnalysis = job.patternAnalysis;
    }

    if (currentPhaseIndex >= 3) { // During optimization/validation
        status.currentBest = {
            winRate: generateRandomFloat(68, 74, 1),
            rr: generateRandomFloat(2.5, 3.5, 1),
            score: generateRandomFloat(70, 95, 1),
        };
    }

    return status;
};

export const getTrainingResults = async (jobId: string): Promise<TrainingResults | null> => {
    await delay(500);
    const job = trainingJobs[jobId];
    if (!job || job.phase !== TrainingPhase.COMPLETE) return null;
    
    const score = generateRandomFloat(50, 95);
    let recommendation: 'HIGH' | 'MEDIUM' | 'LOW' | 'REJECT';
    if (score > 85) recommendation = 'HIGH';
    else if (score > 70) recommendation = 'MEDIUM';
    else if (score > 55) recommendation = 'LOW';
    else recommendation = 'REJECT';

    const valWR = generateRandomFloat(68, 75, 1);
    
    const patternViabilitySummary: {
        pattern: string;
        status: "Enabled" | "Disabled";
        winRate: number;
        signalsPerYear: number;
        primaryTimeframe: string;
    }[] = [
        { pattern: 'Liquidity Sweep Reversal', status: 'Enabled', winRate: 71, signalsPerYear: 52, primaryTimeframe: '1h' },
        { pattern: 'Capitulation Reversal', status: 'Enabled', winRate: 68, signalsPerYear: 21, primaryTimeframe: '4h' },
        { pattern: 'Failed Breakdown (Spring)', status: 'Disabled', winRate: 61, signalsPerYear: 38, primaryTimeframe: '4h' },
        { pattern: 'Supply Shock (Macro)', status: 'Disabled', winRate: 81, signalsPerYear: 3, primaryTimeframe: '1d' },
    ];
    
    const regimePerformance: {
        regime: 'Bull Market' | 'Bear Market' | 'Sideways';
        winRate: number;
        signals: number;
    }[] = [
        { regime: 'Bull Market', winRate: 75, signals: 45 },
        { regime: 'Bear Market', winRate: 62, signals: 21 },
        { regime: 'Sideways', winRate: 71, signals: 35 },
    ];

    const implementationPlan: PatternImplementation[] = patternViabilitySummary.map(p => ({
        pattern: p.pattern,
        parameters: generatePatternParameters(p.pattern),
        regimes: (['Bull Market', 'Bear Market', 'Sideways'] as const).map(regimeName => ({
            regime: regimeName,
            exchanges: exchanges.map(ex => {
                const isEnabled = p.status === 'Enabled';
                const baseRegime = regimePerformance.find(r => r.regime === regimeName)!;
                const baseWinRate = isEnabled ? baseRegime.winRate : p.winRate - 15;
                
                let winRate = generateRandomInt(baseWinRate - 5, baseWinRate + 2);
                if (['Binance', 'Bybit', 'OKX'].includes(ex)) winRate = Math.min(100, winRate + 3);
                if (ex === 'Kraken') winRate = Math.max(0, winRate - 4);
                if (ex === 'Coinbase') winRate = Math.max(0, winRate - 8);

                const signals = Math.round(baseRegime.signals * generateRandomFloat(0.8, 1.2));
                
                return {
                    exchange: ex,
                    winRate: winRate,
                    signals: signals,
                    totalPL: generateRandomFloat(isEnabled ? 500 : -2000, isEnabled ? 5000 : 500),
                    status: isEnabled && winRate > 58 ? 'ACTIVE' : 'PAPER_TRADING',
                };
            })
        }))
    }));


    return {
        jobId,
        assetSymbol: job.symbol,
        confidenceScore: score,
        recommendation,
        patternViabilitySummary,
        performance: {
            winRate: valWR,
            avgRR: generateRandomFloat(2.8, 3.8, 1),
            signalsPerMonth: generateRandomFloat(5, 10, 1),
            expectedReturn: `${generateRandomFloat(3, 9, 1)}%`,
            maxDrawdown: generateRandomFloat(12, 18, 1),
        },
        aiSummaryReport: `
Initial analysis of ${job.symbol} over the past two years revealed strong trending characteristics, particularly on the 4-hour timeframe. The asset exhibits high volatility during these trends, making it a prime candidate for our 'Liquidity Sweep' and 'Capitulation' patterns. The initial viability scan confirmed this, showing both patterns with a win rate exceeding 65% on default parameters across high-liquidity exchanges like Binance and Bybit. However, performance on Kraken was notably weaker due to higher slippage costs.

The 'Failed Breakdown' pattern, however, showed marginal performance with a 61% win rate. It appeared to generate numerous false signals during choppy, sideways market conditions. Multi-timeframe analysis confirmed that many 1-hour signals were noise; filtering them with 4-hour trend alignment dramatically improved the win rate from 61% to a viable 73%, but reduced signal frequency significantly. The AI ultimately favored the 4-hour timeframe as the optimal balance for this asset.

During Bayesian optimization, we discovered that ${job.symbol} responds better to a slightly tighter RSI threshold of 68 (instead of 70) for overbought conditions, which captured reversals more effectively without a significant drop in win rate. The stop-loss was widened from 0.5% to 0.6% after observing many trades were being stopped out prematurely by minor volatility spikes before reaching their profit target. This adjustment was particularly crucial for Coinbase, which showed wider bid-ask spreads in our data.

A key challenge emerged during walk-forward validation: the 'Failed Breakdown' pattern, despite optimization, failed validation in two out of four windows, indicating it was overfit to the training data. As a result, the AI has disabled this pattern to prioritize consistency and risk management. The remaining two patterns, 'Liquidity Sweep' and 'Capitulation', demonstrated high stability and passed all validation and robustness tests, forming the core of the final deployed model.
`,
        walkForwardValidation: {
            results: [
                { window: 1, trainingPeriod: 'Q1-Q4 23', validationPeriod: 'Q1 24', trainWR: 72, valWR: 71, deviation: '-1%', status: 'Pass' },
                { window: 2, trainingPeriod: 'Q2 23 - Q1 24', validationPeriod: 'Q2 24', trainWR: 71, valWR: 68, deviation: '-3%', status: 'Pass' },
                { window: 3, trainingPeriod: 'Q3 23 - Q2 24', validationPeriod: 'Q3 24', trainWR: 73, valWR: 70, deviation: '-3%', status: 'Pass' },
                { window: 4, trainingPeriod: 'Q4 23 - Q3 24', validationPeriod: 'Q4 24', trainWR: 72, valWR: 69, deviation: '-7%', status: 'Pass' },
            ],
            stabilityScore: 100,
        },
        robustnessTesting: {
            monteCarlo: {
                winRateCI: [66.5, 73.2],
                avgRR_CI: [2.6, 3.5],
                interpretation: "Tight confidence intervals suggest the model is robust to minor changes in execution.",
            },
            regimePerformance: regimePerformance,
        },
        implementationPlan,
        fullReportUrl: '#',
        equityCurveUrl: '#',
    };
};

// --- NEW: Exchange Settings Mocks ---

export const getExchangeConnections = async (userId: string): Promise<ExchangeConnection[]> => {
    await delay(300);
    return mockData[userId].exchangeConnections;
}

export const saveExchangeConnection = async (userId: string, connection: Omit<ExchangeConnection, 'id' | 'status'> & { id?: string }): Promise<ExchangeConnection> => {
    await delay(500); // Simulate API call + connection test
    const connections: ExchangeConnection[] = mockData[userId].exchangeConnections;
    
    const newStatus = Math.random() > 0.2 ? ExchangeConnectionStatus.CONNECTED : ExchangeConnectionStatus.ERROR;

    if (connection.id) { // Update
        const index = connections.findIndex(c => c.id === connection.id);
        if (index !== -1) {
            connections[index] = { ...connections[index], ...connection, status: newStatus };
            return connections[index];
        }
    }
    
    // Add
    const newConnection: ExchangeConnection = {
        ...connection,
        id: `conn-${Date.now()}`,
        status: newStatus,
    };
    connections.push(newConnection);
    return newConnection;
}

export const deleteExchangeConnection = async (userId: string, connectionId: string): Promise<void> => {
    await delay(300);
    mockData[userId].exchangeConnections = mockData[userId].exchangeConnections.filter((c: ExchangeConnection) => c.id !== connectionId);
    return Promise.resolve();
}

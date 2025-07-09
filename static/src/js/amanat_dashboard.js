/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
// import { loadJS } from "@web/core/assets"; // Не используется в коде

export class AmanatDashboard extends Component {
    static template = "amanat.AmanatDashboard";
    static props = {
        action: { type: Object, optional: true },
        actionId: { type: Number, optional: true },
        updateActionState: { type: Function, optional: true },
        className: { type: String, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        
        // Инициализация состояния
        this.state = useState({
            isLoading: true,
            transfers: {
                total: 0,
                active: 0,
                closed: 0,
                amount: 0,
                byStatus: {},
                byCurrency: {},
                byMonth: [],
                byCountry: {},
                byType: {}
            },
            orders: {
                total: 0,
                draft: 0,
                done: 0,
                byStatus: {},
                byMonth: []
            },
            money: {
                total: 0,
                positive: 0,
                debt: 0
            },
            currencies: {
                rub: 0,
                usd: 0,
                usdt: 0,
                euro: 0,
                cny: 0
            },
            // ==================== ЗАЯВКИ ====================
            zayavki: {
                total: 0,
                closed: 0,
                closedAmount: 0,
                usdEquivalent: 0,
                byStatus: {},
                byMonth: [],
                byCurrency: {},
                byDealType: {},
                contragentsByZayavki: [],
                contragentAvgCheck: [],
                agentsByZayavki: [],
                agentAvgAmount: [],
                clientsByZayavki: [],
                clientAvgAmount: [],
                subagentsByZayavki: [],
                payersByZayavki: [],
                managersByZayavki: [],
                managersClosedZayavki: [],
                statusDistribution: [],
                dealCycles: [],
                contragentRewardPercent: [],
                managersEfficiency: []
            },
            contragents: [],
            payers: [],
            managers: [],
            weekdayLoad: {},
            processingTime: [],
            dynamics: {
                transfers: [],
                orders: []
            },
            recent_operations: [],
            // Даты для фильтрации
            dateRange1: {
                start: '',
                end: ''
            },
            dateRange2: {
                start: '',
                end: ''
            },
            comparisonData: null,
            chartComparisonData: null
        });
        
        // Хранилище для графиков
        this.charts = {};
        
        // Инициализация при загрузке компонента
        onMounted(() => {
            this.initializeDashboard();
        });
        
        // Удаление графиков при размонтировании
        onWillUnmount(() => {
            Object.values(this.charts).forEach(chart => {
                if (chart) chart.destroy();
            });
        });
    }

    async initializeDashboard() {
        console.log('Dashboard mounted, initializing...');
        
        // Сначала загружаем Chart.js
        try {
            await this.loadChartJS();
            console.log('Chart.js loaded successfully');
        } catch (error) {
            console.error('Failed to load Chart.js:', error);
            this.state.isLoading = false;
            return;
        }
        
        // Затем загружаем данные
        try {
            await this.loadDashboardData();
            console.log('Dashboard data loaded, state:', this.state);
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            this.state.isLoading = false;
        }
    }

    formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    async loadDashboardData() {
        this.state.isLoading = true;
        try {
            // Подготавливаем параметры для вызова RPC
            const params = {};
            
            // Добавляем даты только если они действительно установлены
            if (this.state.dateRange1.start && this.state.dateRange1.start !== '') {
                params.date_from = this.state.dateRange1.start;
            }
            if (this.state.dateRange1.end && this.state.dateRange1.end !== '') {
                params.date_to = this.state.dateRange1.end;
            }
            
            console.log('Loading dashboard data with params:', params);
            
            // Используем правильный метод для вызова RPC
            const data = await this.orm.call(
                'amanat.dashboard',
                'get_dashboard_data',
                [],
                params
            );
            
            console.log('Dashboard data loaded:', data);
            console.log('Данные эффективности менеджеров от сервера:', data.managers_efficiency_data);
            
            this.updateStateFromData(data);
            
            // Рендерим графики после загрузки данных
            setTimeout(() => this.initializeAllCharts(), 100);
        } catch (error) {
            console.error('Error loading dashboard data:', error);
        } finally {
            this.state.isLoading = false;
        }
    }

    async loadChartJS() {
        if (typeof Chart !== 'undefined') {
            console.log('Chart.js already loaded');
            return Promise.resolve();
        }
        
        console.log('Loading Chart.js from CDN...');
        
        try {
            // Загружаем основную библиотеку Chart.js
            await this.loadScript('https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js');
            
            // Проверяем что Chart действительно доступен
            if (typeof Chart === 'undefined') {
                throw new Error('Chart.js did not load properly');
            }
            
            console.log('Chart.js loaded successfully');
            
            // Пытаемся загрузить плагин (опционально)
            try {
                await this.loadScript('https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js');
                if (typeof ChartDataLabels !== 'undefined') {
                    Chart.register(ChartDataLabels);
                    console.log('Chart.js datalabels plugin registered');
                }
            } catch (error) {
                console.warn('Failed to load Chart.js datalabels plugin, continuing without it');
            }
            
        } catch (error) {
            console.error('Failed to load Chart.js:', error);
            throw error;
        }
    }

    loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = () => resolve();
            script.onerror = (error) => reject(error);
            document.head.appendChild(script);
        });
    }

    initializeAllCharts() {
        // Проверяем, что DOM готов
        const dashboardElement = document.querySelector('.o_amanat_dashboard');
        if (!dashboardElement) {
            console.error('Dashboard element not found');
            setTimeout(() => this.initializeAllCharts(), 100);
            return;
        }
        
        // Проверяем наличие Chart.js
        if (typeof Chart === 'undefined') {
            console.error('Chart.js is not loaded, cannot initialize charts');
            return;
        }
        
        // Проверяем наличие хотя бы одного canvas элемента
        const firstChartElement = document.getElementById('import-export-donut');
        if (!firstChartElement) {
            console.warn('Chart canvas elements not found, retrying...');
            setTimeout(() => this.initializeAllCharts(), 100);
            return;
        }
        
        console.log('Initializing all charts with data:', {
            transfers: this.state.transfers,
            orders: this.state.orders,
            currencies: this.state.currencies,
            hasComparisonData: !!this.state.chartComparisonData,
            comparisonData: this.state.chartComparisonData
        });
        
        // Проверяем все canvas элементы (соответствуют XML шаблону)
        const expectedCanvasIds = [
            'import-export-donut',
            'import-export-donut-2',
            'contragents-by-zayavki-chart',
            'contragent-avg-check-chart',
            'contragent-reward-percent-chart',
            'agents-by-zayavki-chart',
            'agent-avg-amount-chart',
            'clients-by-zayavki-chart',
            'payers-by-zayavki-chart',
            'subagents-by-zayavki-chart',
            'managers-by-zayavki-pie',
            'managers-by-zayavki-pie-2',
            'managers-closed-zayavki-pie',
            'managers-closed-zayavki-pie-2',
            'managers-efficiency-chart',
            'zayavki-status-donut',
            'zayavki-status-donut-2',
            'client-avg-amount-chart',
            'deal-cycles-line'
        ];
        
        const missingCanvasIds = expectedCanvasIds.filter(id => !document.getElementById(id));
        if (missingCanvasIds.length > 0) {
            console.warn('Missing canvas elements:', missingCanvasIds);
        }
        
        try {
                        // 19. Соотношение ИМПОРТ/ЭКСПОРТ (первый график - Период 1)
            if (this.state.chartComparisonData) {
                // Режим сравнения - первый график показывает данные Периода 1
                const period1DealTypes = this.state.chartComparisonData.period1.deal_types || {};
                const period1Data = Object.values(period1DealTypes);
                
                if (this.hasChartData(period1Data)) {
                    this.renderDonutChart('import-export-donut', {
                        labels: Object.keys(period1DealTypes),
                        data: period1Data,
                        title: `Период 1: ${this.state.dateRange1.start} - ${this.state.dateRange1.end}`,
                        colors: ['#5DADE2', '#F7DC6F'], // Одинаковые цвета: синий для импорта, желтый для экспорта
                        legendPosition: 'right',
                        showLegend: !!this.state.comparisonData
                    });
                } else {
                    this.showNoDataMessage('import-export-donut', 'Период 1: Нет данных');
                }
            } else {
                // Обычный режим - используем общие данные
                const dealTypeData = Object.values(this.state.zayavki.byDealType || {});
                if (this.hasChartData(dealTypeData)) {
                    this.renderDonutChart('import-export-donut', {
                        labels: Object.keys(this.state.zayavki.byDealType || {}),
                        data: dealTypeData,
                        title: 'Соотношение ИМПОРТ/ЭКСПОРТ',
                        colors: ['#5DADE2', '#F7DC6F'], // Синий для импорта, желтый для экспорта
                        legendPosition: 'right',
                        showLegend: !!this.state.comparisonData
                    });
                } else {
                    this.showNoDataMessage('import-export-donut', 'Соотношение ИМПОРТ/ЭКСПОРТ');
                }
            }

            // 19.2. Соотношение ИМПОРТ/ЭКСПОРТ (второй график - Период 2)
            if (this.state.chartComparisonData) {
                // Режим сравнения - второй график показывает данные Периода 2
                const period2DealTypes = this.state.chartComparisonData.period2.deal_types || {};
                const period2Data = Object.values(period2DealTypes);
                
                if (this.hasChartData(period2Data)) {
                    this.renderDonutChart('import-export-donut-2', {
                        labels: Object.keys(period2DealTypes),
                        data: period2Data,
                        title: `Период 2: ${this.state.dateRange2.start} - ${this.state.dateRange2.end}`,
                        colors: ['#5DADE2', '#F7DC6F'], // Одинаковые цвета: синий для импорта, желтый для экспорта
                        legendPosition: 'right',
                        showLegend: !!this.state.comparisonData
                    });
                } else {
                    this.showNoDataMessage('import-export-donut-2', 'Период 2: Нет данных');
                }
            } else {
                // Обычный режим - используем общие данные (дублируем первый график)
                const dealTypeData = Object.values(this.state.zayavki.byDealType || {});
                if (this.hasChartData(dealTypeData)) {
                    this.renderDonutChart('import-export-donut-2', {
                        labels: Object.keys(this.state.zayavki.byDealType || {}),
                        data: dealTypeData,
                        title: 'Соотношение ИМПОРТ/ЭКСПОРТ',
                        colors: ['#5DADE2', '#F7DC6F'], // Синий для импорта, желтый для экспорта
                        legendPosition: 'right',
                        showLegend: !!this.state.comparisonData
                    });
                } else {
                    this.showNoDataMessage('import-export-donut-2', 'Соотношение ИМПОРТ/ЭКСПОРТ');
                }
            }

            // 20. Количество заявок под каждого контрагента (горизонтальная столбчатая)
            if (this.state.chartComparisonData) {
                // Режим сравнения - используем данные для двух периодов
                const period1Data = this.state.chartComparisonData.period1.contragents_by_zayavki || [];
                const period2Data = this.state.chartComparisonData.period2.contragents_by_zayavki || [];
                
                // Объединяем все уникальные имена контрагентов из обоих периодов
                const allContragents = [...new Set([
                    ...period1Data.map(c => c.name),
                    ...period2Data.map(c => c.name)
                ])];
                
                if (allContragents.length > 0) {
                    this.renderComparisonHorizontalBarChart('contragents-by-zayavki-chart', {
                        labels: allContragents,
                        period1Data: allContragents.map(name => {
                            const item = period1Data.find(c => c.name === name);
                            return item ? item.count : 0;
                        }),
                        period2Data: allContragents.map(name => {
                            const item = period2Data.find(c => c.name === name);
                            return item ? item.count : 0;
                        }),
                        period1Label: `Период 1 (${this.state.dateRange1.start} - ${this.state.dateRange1.end})`,
                        period2Label: `Период 2 (${this.state.dateRange2.start} - ${this.state.dateRange2.end})`,
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const contragentName = allContragents[index];
                                this.openZayavkiByContragent(contragentName);
                            }
                        }
                    });
                } else {
                    this.showNoDataMessage('contragents-by-zayavki-chart', 'Контрагенты по заявкам');
                }
            } else if (this.hasChartData(this.state.zayavki.contragentsByZayavki)) {
                // Обычный режим - один период
                this.renderHorizontalBarChart('contragents-by-zayavki-chart', {
                    labels: this.state.zayavki.contragentsByZayavki.map(c => c.name),
                    data: this.state.zayavki.contragentsByZayavki.map(c => c.count),
                    title: 'Количество заявок под каждого контрагента',
                    clickable: true,
                    onClick: (event, elements) => {
                        if (elements.length > 0) {
                            const index = elements[0].index;
                            const contragentName = this.state.zayavki.contragentsByZayavki[index].name;
                            this.openZayavkiByContragent(contragentName);
                        }
                    }
                });
            } else {
                this.showNoDataMessage('contragents-by-zayavki-chart', 'Контрагенты по заявкам');
            }

            // 21. Средний чек у Контрагента (горизонтальная столбчатая)
            if (this.state.chartComparisonData) {
                // Режим сравнения - используем данные для двух периодов
                const period1Data = this.state.chartComparisonData.period1.contragent_avg_check || [];
                const period2Data = this.state.chartComparisonData.period2.contragent_avg_check || [];
                
                // Объединяем все уникальные имена контрагентов из обоих периодов
                const allContragents = [...new Set([
                    ...period1Data.map(c => c.name),
                    ...period2Data.map(c => c.name)
                ])];
                
                if (allContragents.length > 0) {
                    this.renderComparisonHorizontalBarChart('contragent-avg-check-chart', {
                        labels: allContragents,
                        period1Data: allContragents.map(name => {
                            const item = period1Data.find(c => c.name === name);
                            return item ? item.avg_amount : 0;
                        }),
                        period2Data: allContragents.map(name => {
                            const item = period2Data.find(c => c.name === name);
                            return item ? item.avg_amount : 0;
                        }),
                        period1Label: `Период 1 (${this.state.dateRange1.start} - ${this.state.dateRange1.end})`,
                        period2Label: `Период 2 (${this.state.dateRange2.start} - ${this.state.dateRange2.end})`,
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const contragentName = allContragents[index];
                                this.openZayavkiByContragent(contragentName);
                            }
                        }
                    });
                } else {
                    this.showNoDataMessage('contragent-avg-check-chart', 'Средний чек у контрагента');
                }
            } else if (this.hasChartData(this.state.zayavki.contragentAvgCheck)) {
                // Обычный режим - один период
                this.renderHorizontalBarChart('contragent-avg-check-chart', {
                    labels: this.state.zayavki.contragentAvgCheck.map(c => c.name),
                    data: this.state.zayavki.contragentAvgCheck.map(c => c.avg_amount),
                    title: 'Средний чек у Контрагента',
                    clickable: true,
                    onClick: (event, elements) => {
                        if (elements.length > 0) {
                            const index = elements[0].index;
                            const contragentName = this.state.zayavki.contragentAvgCheck[index].name;
                            this.openZayavkiByContragent(contragentName);
                        }
                    }
                });
            } else {
                this.showNoDataMessage('contragent-avg-check-chart', 'Средний чек у контрагента');
            }

            // 22. Количество заявок под каждого агента (горизонтальная столбчатая)
            if (this.state.chartComparisonData) {
                // Режим сравнения - используем данные для двух периодов
                const period1Data = this.state.chartComparisonData.period1.agents_by_zayavki || [];
                const period2Data = this.state.chartComparisonData.period2.agents_by_zayavki || [];
                
                // Объединяем все уникальные имена агентов из обоих периодов
                const allAgents = [...new Set([
                    ...period1Data.map(a => a.name),
                    ...period2Data.map(a => a.name)
                ])];
                
                if (allAgents.length > 0) {
                    this.renderComparisonHorizontalBarChart('agents-by-zayavki-chart', {
                        labels: allAgents,
                        period1Data: allAgents.map(name => {
                            const item = period1Data.find(a => a.name === name);
                            return item ? item.count : 0;
                        }),
                        period2Data: allAgents.map(name => {
                            const item = period2Data.find(a => a.name === name);
                            return item ? item.count : 0;
                        }),
                        period1Label: `Период 1 (${this.state.dateRange1.start} - ${this.state.dateRange1.end})`,
                        period2Label: `Период 2 (${this.state.dateRange2.start} - ${this.state.dateRange2.end})`,
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const agentName = allAgents[index];
                                this.openZayavkiByAgent(agentName);
                            }
                        }
                    });
                } else {
                    this.showNoDataMessage('agents-by-zayavki-chart', 'Агенты по заявкам');
                }
            } else if (this.hasChartData(this.state.zayavki.agentsByZayavki)) {
                // Обычный режим - один период
                this.renderHorizontalBarChart('agents-by-zayavki-chart', {
                    labels: this.state.zayavki.agentsByZayavki.map(a => a.name),
                    data: this.state.zayavki.agentsByZayavki.map(a => a.count),
                    title: 'Количество заявок под каждого агента',
                    clickable: true,
                    onClick: (event, elements) => {
                        if (elements.length > 0) {
                            const index = elements[0].index;
                            const agentName = this.state.zayavki.agentsByZayavki[index].name;
                            this.openZayavkiByAgent(agentName);
                        }
                    }
                });
            } else {
                this.showNoDataMessage('agents-by-zayavki-chart', 'Агенты по заявкам');
            }

            // 23. Средняя сумма заявок под каждого агента (горизонтальная столбчатая)
            if (this.state.chartComparisonData) {
                // Режим сравнения - используем данные для двух периодов
                const period1Data = this.state.chartComparisonData.period1.agent_avg_amount || [];
                const period2Data = this.state.chartComparisonData.period2.agent_avg_amount || [];
                
                // Объединяем все уникальные имена агентов из обоих периодов
                const allAgents = [...new Set([
                    ...period1Data.map(a => a.name),
                    ...period2Data.map(a => a.name)
                ])];
                
                if (allAgents.length > 0) {
                    this.renderComparisonHorizontalBarChart('agent-avg-amount-chart', {
                        labels: allAgents,
                        period1Data: allAgents.map(name => {
                            const item = period1Data.find(a => a.name === name);
                            return item ? item.avg_amount : 0;
                        }),
                        period2Data: allAgents.map(name => {
                            const item = period2Data.find(a => a.name === name);
                            return item ? item.avg_amount : 0;
                        }),
                        period1Label: `Период 1 (${this.state.dateRange1.start} - ${this.state.dateRange1.end})`,
                        period2Label: `Период 2 (${this.state.dateRange2.start} - ${this.state.dateRange2.end})`,
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const agentName = allAgents[index];
                                this.openZayavkiByAgent(agentName);
                            }
                        }
                    });
                } else {
                    this.showNoDataMessage('agent-avg-amount-chart', 'Средние суммы по агентам');
                }
            } else if (this.hasChartData(this.state.zayavki.agentAvgAmount)) {
                // Обычный режим - один период
                this.renderHorizontalBarChart('agent-avg-amount-chart', {
                    labels: this.state.zayavki.agentAvgAmount.map(a => a.name),
                    data: this.state.zayavki.agentAvgAmount.map(a => a.avg_amount),
                    title: 'Средняя сумма заявок под каждого агента',
                    clickable: true,
                    onClick: (event, elements) => {
                        if (elements.length > 0) {
                            const index = elements[0].index;
                            const agentName = this.state.zayavki.agentAvgAmount[index].name;
                            this.openZayavkiByAgent(agentName);
                        }
                    }
                });
            } else {
                this.showNoDataMessage('agent-avg-amount-chart', 'Средние суммы по агентам');
            }

            // 24. Количество заявок под каждого клиента (горизонтальная столбчатая)
            if (this.state.chartComparisonData) {
                // Режим сравнения - используем данные для двух периодов
                const period1Data = this.state.chartComparisonData.period1.clients_by_zayavki || [];
                const period2Data = this.state.chartComparisonData.period2.clients_by_zayavki || [];
                
                // Объединяем все уникальные имена клиентов из обоих периодов
                const allClients = [...new Set([
                    ...period1Data.map(c => c.name),
                    ...period2Data.map(c => c.name)
                ])];
                
                if (allClients.length > 0) {
                    this.renderComparisonHorizontalBarChart('clients-by-zayavki-chart', {
                        labels: allClients,
                        period1Data: allClients.map(name => {
                            const item = period1Data.find(c => c.name === name);
                            return item ? item.count : 0;
                        }),
                        period2Data: allClients.map(name => {
                            const item = period2Data.find(c => c.name === name);
                            return item ? item.count : 0;
                        }),
                        period1Label: `Период 1 (${this.state.dateRange1.start} - ${this.state.dateRange1.end})`,
                        period2Label: `Период 2 (${this.state.dateRange2.start} - ${this.state.dateRange2.end})`,
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const clientName = allClients[index];
                                this.openZayavkiByClient(clientName);
                            }
                        }
                    });
                } else {
                    this.showNoDataMessage('clients-by-zayavki-chart', 'Клиенты по заявкам');
                }
            } else if (this.hasChartData(this.state.zayavki.clientsByZayavki)) {
                // Обычный режим - один период
                this.renderHorizontalBarChart('clients-by-zayavki-chart', {
                    labels: this.state.zayavki.clientsByZayavki.map(c => c.name),
                    data: this.state.zayavki.clientsByZayavki.map(c => c.count),
                    title: 'Количество заявок под каждого клиента',
                    clickable: true,
                    onClick: (event, elements) => {
                        if (elements.length > 0) {
                            const index = elements[0].index;
                            const clientName = this.state.zayavki.clientsByZayavki[index].name;
                            this.openZayavkiByClient(clientName);
                        }
                    }
                });
            } else {
                this.showNoDataMessage('clients-by-zayavki-chart', 'Клиенты по заявкам');
            }

            // 25. Вознаграждение средний процент (горизонтальная столбчатая)
            if (this.state.chartComparisonData) {
                // Режим сравнения - используем данные для двух периодов
                const period1Data = this.state.chartComparisonData.period1.contragent_reward_percent || [];
                const period2Data = this.state.chartComparisonData.period2.contragent_reward_percent || [];
                
                // Объединяем все уникальные имена контрагентов из обоих периодов
                const allContragents = [...new Set([
                    ...period1Data.map(c => c.name),
                    ...period2Data.map(c => c.name)
                ])];
                
                if (allContragents.length > 0) {
                    this.renderComparisonHorizontalBarChart('contragent-reward-percent-chart', {
                        labels: allContragents,
                        period1Data: allContragents.map(name => {
                            const item = period1Data.find(c => c.name === name);
                            return item ? item.avg_reward_percent : 0;
                        }),
                        period2Data: allContragents.map(name => {
                            const item = period2Data.find(c => c.name === name);
                            return item ? item.avg_reward_percent : 0;
                        }),
                        period1Label: `Период 1 (${this.state.dateRange1.start} - ${this.state.dateRange1.end})`,
                        period2Label: `Период 2 (${this.state.dateRange2.start} - ${this.state.dateRange2.end})`,
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const contragentName = allContragents[index];
                                this.openZayavkiByContragent(contragentName);
                            }
                        }
                    });
                } else {
                    this.showNoDataMessage('contragent-reward-percent-chart', 'Вознаграждение по контрагентам');
                }
            } else if (this.hasChartData(this.state.zayavki.contragentRewardPercent)) {
                // Обычный режим - один период
                this.renderHorizontalBarChart('contragent-reward-percent-chart', {
                    labels: this.state.zayavki.contragentRewardPercent.map(c => c.name),
                    data: this.state.zayavki.contragentRewardPercent.map(c => c.avg_reward_percent),
                    title: 'Вознаграждение средний процент',
                    clickable: true,
                    onClick: (event, elements) => {
                        if (elements.length > 0) {
                            const index = elements[0].index;
                            const contragentName = this.state.zayavki.contragentRewardPercent[index].name;
                            this.openZayavkiByContragent(contragentName);
                        }
                    }
                });
            } else {
                this.showNoDataMessage('contragent-reward-percent-chart', 'Вознаграждение по контрагентам');
            }

            // 26. Количество заявок по платежщикам субагентов (горизонтальная столбчатая)
            if (this.state.chartComparisonData) {
                // Режим сравнения - используем данные для двух периодов
                const period1Data = this.state.chartComparisonData.period1.payers_by_zayavki || [];
                const period2Data = this.state.chartComparisonData.period2.payers_by_zayavki || [];
                
                // Объединяем все уникальные имена платежщиков из обоих периодов
                const allPayers = [...new Set([
                    ...period1Data.map(p => p.name),
                    ...period2Data.map(p => p.name)
                ])];
                
                if (allPayers.length > 0) {
                    this.renderComparisonHorizontalBarChart('payers-by-zayavki-chart', {
                        labels: allPayers,
                        period1Data: allPayers.map(name => {
                            const item = period1Data.find(p => p.name === name);
                            return item ? item.count : 0;
                        }),
                        period2Data: allPayers.map(name => {
                            const item = period2Data.find(p => p.name === name);
                            return item ? item.count : 0;
                        }),
                        period1Label: `Период 1 (${this.state.dateRange1.start} - ${this.state.dateRange1.end})`,
                        period2Label: `Период 2 (${this.state.dateRange2.start} - ${this.state.dateRange2.end})`,
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const payerName = allPayers[index];
                                this.openZayavkiByPayer(payerName);
                            }
                        }
                    });
                } else {
                    this.showNoDataMessage('payers-by-zayavki-chart', 'Платежщики по заявкам');
                }
            } else if (this.state.zayavki.payersByZayavki && this.state.zayavki.payersByZayavki.length > 0) {
                // Обычный режим - один период
                this.renderHorizontalBarChart('payers-by-zayavki-chart', {
                    labels: this.state.zayavki.payersByZayavki.map(p => p.name),
                    data: this.state.zayavki.payersByZayavki.map(p => p.count),
                    title: 'Количество заявок под каждого платежщика субагента',
                    clickable: true,
                    onClick: (event, elements) => {
                        if (elements.length > 0) {
                            const index = elements[0].index;
                            const payerName = this.state.zayavki.payersByZayavki[index].name;
                            this.openZayavkiByPayer(payerName);
                        }
                    }
                });
            } else {
                this.showNoDataMessage('payers-by-zayavki-chart', 'Платежщики по заявкам');
            }

            // 27. Количество заявок под каждого субагента (горизонтальная столбчатая)
            if (this.state.chartComparisonData) {
                // Режим сравнения - используем данные для двух периодов
                const period1Data = this.state.chartComparisonData.period1.subagents_by_zayavki || [];
                const period2Data = this.state.chartComparisonData.period2.subagents_by_zayavki || [];
                
                // Объединяем все уникальные имена субагентов из обоих периодов
                const allSubagents = [...new Set([
                    ...period1Data.map(s => s.name),
                    ...period2Data.map(s => s.name)
                ])];
                
                if (allSubagents.length > 0) {
                    this.renderComparisonHorizontalBarChart('subagents-by-zayavki-chart', {
                        labels: allSubagents,
                        period1Data: allSubagents.map(name => {
                            const item = period1Data.find(s => s.name === name);
                            return item ? item.count : 0;
                        }),
                        period2Data: allSubagents.map(name => {
                            const item = period2Data.find(s => s.name === name);
                            return item ? item.count : 0;
                        }),
                        period1Label: `Период 1 (${this.state.dateRange1.start} - ${this.state.dateRange1.end})`,
                        period2Label: `Период 2 (${this.state.dateRange2.start} - ${this.state.dateRange2.end})`,
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const subagentName = allSubagents[index];
                                this.openZayavkiBySubagent(subagentName);
                            }
                        }
                    });
                } else {
                    this.showNoDataMessage('subagents-by-zayavki-chart', 'Субагенты по заявкам');
                }
            } else if (this.state.zayavki.subagentsByZayavki && this.state.zayavki.subagentsByZayavki.length > 0) {
                // Обычный режим - один период
                this.renderHorizontalBarChart('subagents-by-zayavki-chart', {
                    labels: this.state.zayavki.subagentsByZayavki.map(s => s.name),
                    data: this.state.zayavki.subagentsByZayavki.map(s => s.count),
                    title: 'Количество заявок под каждого субагента',
                    clickable: true,
                    onClick: (event, elements) => {
                        if (elements.length > 0) {
                            const index = elements[0].index;
                            const subagentName = this.state.zayavki.subagentsByZayavki[index].name;
                            this.openZayavkiBySubagent(subagentName);
                        }
                    }
                });
            } else {
                this.showNoDataMessage('subagents-by-zayavki-chart', 'Субагенты по заявкам');
            }

            // 28. Средняя сумма заявок по клиентам (горизонтальная столбчатая)
            if (this.state.chartComparisonData) {
                // Режим сравнения - используем данные для двух периодов
                const period1Data = this.state.chartComparisonData.period1.client_avg_amount || [];
                const period2Data = this.state.chartComparisonData.period2.client_avg_amount || [];
                
                // Объединяем все уникальные имена клиентов из обоих периодов
                const allClients = [...new Set([
                    ...period1Data.map(c => c.name),
                    ...period2Data.map(c => c.name)
                ])];
                
                if (allClients.length > 0) {
                    this.renderComparisonHorizontalBarChart('client-avg-amount-chart', {
                        labels: allClients,
                        period1Data: allClients.map(name => {
                            const item = period1Data.find(c => c.name === name);
                            return item ? item.avg_amount : 0;
                        }),
                        period2Data: allClients.map(name => {
                            const item = period2Data.find(c => c.name === name);
                            return item ? item.avg_amount : 0;
                        }),
                        period1Label: `Период 1 (${this.state.dateRange1.start} - ${this.state.dateRange1.end})`,
                        period2Label: `Период 2 (${this.state.dateRange2.start} - ${this.state.dateRange2.end})`,
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const clientName = allClients[index];
                                this.openZayavkiByClient(clientName);
                            }
                        }
                    });
                } else {
                    this.showNoDataMessage('client-avg-amount-chart', 'Средние суммы по клиентам');
                }
            } else if (this.state.zayavki.clientAvgAmount && this.state.zayavki.clientAvgAmount.length > 0) {
                // Обычный режим - один период
                this.renderHorizontalBarChart('client-avg-amount-chart', {
                    labels: this.state.zayavki.clientAvgAmount.map(c => c.name),
                    data: this.state.zayavki.clientAvgAmount.map(c => c.avg_amount),
                    title: 'Средняя сумма заявок по клиентам',
                    clickable: true,
                    onClick: (event, elements) => {
                        if (elements.length > 0) {
                            const index = elements[0].index;
                            const clientName = this.state.zayavki.clientAvgAmount[index].name;
                            this.openZayavkiByClient(clientName);
                        }
                    }
                });
            } else {
                this.showNoDataMessage('client-avg-amount-chart', 'Средние суммы по клиентам');
            }

            // 29. Заявок закреплено за менеджером (круговая с процентами)
            const managerColors = [
                '#3498DB',  // Синий - Айгуль (24,5%)
                '#E67E22',  // Оранжевый - Алина (18,2%)  
                '#27AE60',  // Зеленый - Алёна (23,5%)
                '#F39C12',  // Желтый - Гульназ (11,6%)
                '#9B59B6',  // Фиолетовый - Ксения К (8,2%)
                '#E74C3C',  // Красный - Настя (8,4%)
                '#95A5A6'   // Серый - Элина (5,5%)
            ];

            if (this.state.chartComparisonData) {
                // Режим сравнения - первый график показывает данные Периода 1
                const period1Managers = this.state.chartComparisonData.period1.managers_by_zayavki || [];
                const period2Managers = this.state.chartComparisonData.period2.managers_by_zayavki || [];
                
                if (this.hasChartData(period1Managers)) {
                    this.renderPieChartWithPercentage('managers-by-zayavki-pie', {
                        labels: period1Managers.map(m => m.name),
                        data: period1Managers.map(m => m.count),
                        title: `Период 1: Заявок закреплено за менеджером`,
                        colors: managerColors,
                        showLegend: !!this.state.comparisonData,
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const managerName = period1Managers[index].name;
                                this.openZayavkiByManager(managerName);
                            }
                        }
                    });
                } else {
                    this.showNoDataMessage('managers-by-zayavki-pie', 'Заявки по менеджерам (Период 1)');
                }
                
                if (this.hasChartData(period2Managers)) {
                    this.renderPieChartWithPercentage('managers-by-zayavki-pie-2', {
                        labels: period2Managers.map(m => m.name),
                        data: period2Managers.map(m => m.count),
                        title: `Период 2: Заявок закреплено за менеджером`,
                        colors: managerColors,
                        showLegend: !!this.state.comparisonData,
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const managerName = period2Managers[index].name;
                                this.openZayavkiByManager(managerName);
                            }
                        }
                    });
                } else {
                    this.showNoDataMessage('managers-by-zayavki-pie-2', 'Заявки по менеджерам (Период 2)');
                }
            } else {
                // Обычный режим - оба графика показывают одинаковые данные
                if (this.hasChartData(this.state.zayavki.managersByZayavki)) {
                    // Первый график
                    this.renderPieChartWithPercentage('managers-by-zayavki-pie', {
                        labels: this.state.zayavki.managersByZayavki.map(m => m.name),
                        data: this.state.zayavki.managersByZayavki.map(m => m.count),
                        title: 'Заявок закреплено за менеджером',
                        colors: managerColors,
                        showLegend: !!this.state.comparisonData,
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const managerName = this.state.zayavki.managersByZayavki[index].name;
                                this.openZayavkiByManager(managerName);
                            }
                        }
                    });

                    // Второй график (дубликат)
                    this.renderPieChartWithPercentage('managers-by-zayavki-pie-2', {
                        labels: this.state.zayavki.managersByZayavki.map(m => m.name),
                        data: this.state.zayavki.managersByZayavki.map(m => m.count),
                        title: 'Заявок закреплено за менеджером',
                        colors: managerColors,
                        showLegend: !!this.state.comparisonData,
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const managerName = this.state.zayavki.managersByZayavki[index].name;
                                this.openZayavkiByManager(managerName);
                            }
                        }
                    });
                } else {
                    this.showNoDataMessage('managers-by-zayavki-pie', 'Заявки по менеджерам');
                    this.showNoDataMessage('managers-by-zayavki-pie-2', 'Заявки по менеджерам');
                }
            }

            // 30. Заявок закрыто менеджером (круговая с процентами)
            const managerClosedColors = [
                '#3498DB',  // Синий - Айгуль (19,2%)
                '#E67E22',  // Оранжевый - Алина (17,3%)  
                '#27AE60',  // Зеленый - Алёна (22,5%)
                '#F39C12',  // Желтый - Гульназ (10,1%)
                '#9B59B6',  // Фиолетовый - Ксения К (13,7%)
                '#E74C3C',  // Красный - Настя (6,1%)
                '#95A5A6'   // Серый - Элина (11,5%)
            ];

            if (this.state.chartComparisonData) {
                // Режим сравнения - первый график показывает данные Периода 1
                const period1ManagersClosed = this.state.chartComparisonData.period1.managers_closed_zayavki || [];
                const period2ManagersClosed = this.state.chartComparisonData.period2.managers_closed_zayavki || [];
                
                if (this.hasChartData(period1ManagersClosed)) {
                    this.renderPieChartWithPercentage('managers-closed-zayavki-pie', {
                        labels: period1ManagersClosed.map(m => m.name),
                        data: period1ManagersClosed.map(m => m.count),
                        title: `Период 1: Заявок закрыто менеджером`,
                        colors: managerClosedColors,
                        showLegend: !!this.state.comparisonData,
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const managerName = period1ManagersClosed[index].name;
                                this.openZayavkiByManagerClosed(managerName);
                            }
                        }
                    });
                } else {
                    this.showNoDataMessage('managers-closed-zayavki-pie', 'Закрытые заявки по менеджерам (Период 1)');
                }
                
                if (this.hasChartData(period2ManagersClosed)) {
                    this.renderPieChartWithPercentage('managers-closed-zayavki-pie-2', {
                        labels: period2ManagersClosed.map(m => m.name),
                        data: period2ManagersClosed.map(m => m.count),
                        title: `Период 2: Заявок закрыто менеджером`,
                        colors: managerClosedColors,
                        showLegend: !!this.state.comparisonData,
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const managerName = period2ManagersClosed[index].name;
                                this.openZayavkiByManagerClosed(managerName);
                            }
                        }
                    });
                } else {
                    this.showNoDataMessage('managers-closed-zayavki-pie-2', 'Закрытые заявки по менеджерам (Период 2)');
                }
            } else {
                // Обычный режим - оба графика показывают одинаковые данные
                if (this.hasChartData(this.state.zayavki.managersClosedZayavki)) {
                    this.renderPieChartWithPercentage('managers-closed-zayavki-pie', {
                        labels: this.state.zayavki.managersClosedZayavki.map(m => m.name),
                        data: this.state.zayavki.managersClosedZayavki.map(m => m.count),
                        title: 'Заявок закрыто менеджером',
                        colors: managerClosedColors,
                        showLegend: !!this.state.comparisonData,
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const managerName = this.state.zayavki.managersClosedZayavki[index].name;
                                this.openZayavkiByManagerClosed(managerName);
                            }
                        }
                    });

                    // Второй график (дубликат)
                    this.renderPieChartWithPercentage('managers-closed-zayavki-pie-2', {
                        labels: this.state.zayavki.managersClosedZayavki.map(m => m.name),
                        data: this.state.zayavki.managersClosedZayavki.map(m => m.count),
                        title: 'Заявок закрыто менеджером',
                        colors: managerClosedColors,
                        showLegend: !!this.state.comparisonData,
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const managerName = this.state.zayavki.managersClosedZayavki[index].name;
                                this.openZayavkiByManagerClosed(managerName);
                            }
                        }
                    });
                } else {
                    this.showNoDataMessage('managers-closed-zayavki-pie', 'Закрытые заявки по менеджерам');
                    this.showNoDataMessage('managers-closed-zayavki-pie-2', 'Закрытые заявки по менеджерам');
                }
            }

            // 31. Эффективность менеджеров (вертикальная столбчатая диаграмма)
            console.log('Данные эффективности менеджеров:', this.state.zayavki.managersEfficiency);
            console.log('Проверка данных через hasChartData:', this.hasChartData(this.state.zayavki.managersEfficiency));
            if (this.hasChartData(this.state.zayavki.managersEfficiency)) {
                this.renderBarChart('managers-efficiency-chart', {
                    labels: this.state.zayavki.managersEfficiency.map(m => m.name),
                    data: this.state.zayavki.managersEfficiency.map(m => m.efficiency),
                    title: 'Эффективность менеджеров',
                    clickable: true,
                    onClick: (event, elements) => {
                        console.log('График эффективности менеджеров: клик зарегистрирован', elements);
                        if (elements.length > 0) {
                            const index = elements[0].index;
                            const managerName = this.state.zayavki.managersEfficiency[index].name;
                            console.log('Открываем информацию о менеджере:', managerName);
                            this.openManagerInfo(managerName);
                        }
                    }
                });
            } else {
                console.log('Нет данных для графика эффективности менеджеров');
                this.showNoDataMessage('managers-efficiency-chart', 'Эффективность менеджеров');
            }

            // 32. Статусы заявок (donut chart)
            if (this.hasChartData(this.state.zayavki.statusDistribution)) {
                const statusColors = [
                    '#3498DB',  // Синий - заявка закрыта (97.1%)
                    '#E67E22',  // Оранжевый - отменено клиентом
                    '#95A5A6'   // Серый - 15. возврат
                ];

                this.renderDonutChart('zayavki-status-donut', {
                    labels: this.state.zayavki.statusDistribution.map(s => s.name),
                    data: this.state.zayavki.statusDistribution.map(s => s.count),
                    title: 'Статусы заявок',
                    colors: statusColors,
                    legendPosition: 'left',
                    showLegend: !!this.state.comparisonData,
                    clickable: true,
                    onClick: (event, elements) => {
                        console.log('График статусов заявок: клик зарегистрирован', elements);
                        if (elements.length > 0) {
                            const index = elements[0].index;
                            const statusName = this.state.zayavki.statusDistribution[index].name;
                            console.log('Открываем заявки со статусом:', statusName);
                            this.openZayavkiByStatus(statusName);
                        }
                    }
                });

                // Второй график статусов заявок для сравнения диапазонов
                this.renderDonutChart('zayavki-status-donut-2', {
                    labels: this.state.zayavki.statusDistribution.map(s => s.name),
                    data: this.state.zayavki.statusDistribution.map(s => s.count),
                    title: 'Статусы заявок',
                    colors: [
                        '#2ECC71',  // Зеленый - заявка закрыта
                        '#E74C3C',  // Красный - отменено клиентом
                        '#F39C12',  // Оранжевый - возврат
                        '#9B59B6',  // Фиолетовый - в работе
                        '#1ABC9C'   // Бирюзовый - ожидание
                    ],
                    legendPosition: 'right',
                    showLegend: !!this.state.comparisonData,
                    clickable: true,
                    onClick: (event, elements) => {
                        console.log('График статусов заявок (2): клик зарегистрирован', elements);
                        if (elements.length > 0) {
                            const index = elements[0].index;
                            const statusName = this.state.zayavki.statusDistribution[index].name;
                            console.log('Открываем заявки со статусом:', statusName);
                            this.openZayavkiByStatus(statusName);
                        }
                    }
                });
            } else {
                this.showNoDataMessage('zayavki-status-donut', 'Статусы заявок');
                this.showNoDataMessage('zayavki-status-donut-2', 'Статусы заявок');
            }

            // 33. Циклы сделок (линейный график)
            if (this.state.chartComparisonData) {
                // Режим сравнения - используем данные для двух периодов
                const period1Data = this.state.chartComparisonData.period1.deal_cycles || [];
                const period2Data = this.state.chartComparisonData.period2.deal_cycles || [];
                
                // Объединяем все уникальные дни циклов из обоих периодов и сортируем
                const allCycleDays = [...new Set([
                    ...period1Data.map(c => c.cycle_days),
                    ...period2Data.map(c => c.cycle_days)
                ])].sort((a, b) => a - b);
                
                if (allCycleDays.length > 0) {
                    this.renderComparisonSmoothLineChart('deal-cycles-line', {
                        labels: allCycleDays,
                        period1Data: allCycleDays.map(days => {
                            const item = period1Data.find(c => c.cycle_days === days);
                            return item ? item.count : 0;
                        }),
                        period2Data: allCycleDays.map(days => {
                            const item = period2Data.find(c => c.cycle_days === days);
                            return item ? item.count : 0;
                        }),
                        period1Label: `Период 1 (${this.state.dateRange1.start} - ${this.state.dateRange1.end})`,
                        period2Label: `Период 2 (${this.state.dateRange2.start} - ${this.state.dateRange2.end})`,
                        xAxisLabel: 'Цикл сделки, дн',
                        yAxisLabel: 'Количество заявок',
                        tension: 0.3,
                        pointStyle: 'circle',
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const cycleDays = allCycleDays[index];
                                this.openZayavkiByCycle(cycleDays);
                            }
                        }
                    });
                } else {
                    this.showNoDataMessage('deal-cycles-line', 'Циклы сделок');
                }
            } else if (this.state.zayavki.dealCycles && this.state.zayavki.dealCycles.length > 0) {
                // Обычный режим - один период
                this.renderSmoothLineChart('deal-cycles-line', {
                    labels: this.state.zayavki.dealCycles.map(c => c.cycle_days),
                    data: this.state.zayavki.dealCycles.map(c => c.count),
                    title: 'Циклы сделок',
                    xAxisLabel: 'Цикл сделки, дн',
                    yAxisLabel: 'Number of records',
                    color: '#3498DB',
                    clickable: true,
                    startAtZero: true,
                    tension: 0.3,
                    pointStyle: 'circle',
                    onClick: (event, elements) => {
                        console.log('График циклов сделок: клик зарегистрирован', elements);
                        if (elements.length > 0) {
                            const index = elements[0].index;
                            const cycleDays = this.state.zayavki.dealCycles[index].cycle_days;
                            console.log('Открываем заявки с циклом:', cycleDays, 'дней');
                            this.openZayavkiByCycle(cycleDays);
                        }
                    }
                });
            } else {
                this.showNoDataMessage('deal-cycles-line', 'Циклы сделок');
            }

            
        } catch (error) {
            console.error('Error initializing charts:', error);
        }
    }

    renderLineChart(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        // Уничтожаем предыдущий график если он существует
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }
        
        const chartConfig = {
            type: 'line',
            data: {
                labels: config.labels,
                datasets: [{
                    label: config.title,
                    data: config.data,
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true,
                        text: config.title
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        };
        
        // Отключаем datalabels для линейных графиков
        if (typeof ChartDataLabels !== 'undefined') {
            chartConfig.options.plugins.datalabels = {
                display: false
            };
        }
        
        this.charts[canvasId] = new Chart(canvas, chartConfig);
    }

    renderBarChart(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        // Уничтожаем предыдущий график если он существует
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }
        
        const chartConfig = {
            type: 'bar',
            data: {
                labels: config.labels,
                datasets: [{
                    label: config.title,
                    data: config.data,
                    backgroundColor: 'rgba(54, 162, 235, 0.8)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true,
                        text: config.title
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        };
        
        // Добавляем обработчик кликов если он указан
        if (config.clickable && config.onClick) {
            chartConfig.options.onClick = config.onClick;
        }
        
        // Отключаем datalabels для столбчатых графиков
        if (typeof ChartDataLabels !== 'undefined') {
            chartConfig.options.plugins.datalabels = {
                display: false
            };
        }
        
        this.charts[canvasId] = new Chart(canvas, chartConfig);
    }

    renderHorizontalBarChart(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        // Уничтожаем предыдущий график если он существует
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }
        
        // Создаем градиентный синий цвет как на скриншоте
        const ctx = canvas.getContext('2d');
        const gradient = ctx.createLinearGradient(0, 0, canvas.width, 0);
        gradient.addColorStop(0, '#1e3a8a');    // Темно-синий
        gradient.addColorStop(0.5, '#3b82f6');  // Средний синий  
        gradient.addColorStop(1, '#60a5fa');    // Светло-синий
        
        const chartConfig = {
            type: 'bar',
            data: {
                labels: config.labels,
                datasets: [{
                    label: config.title,
                    data: config.data,
                    backgroundColor: gradient,
                    borderColor: 'transparent',
                    borderWidth: 0,
                    borderRadius: 8,        // Закругленные края как на скриншоте
                    borderSkipped: false,   // Закругляем все углы
                    barThickness: 35,       // Толщина полосок (увеличено)
                    maxBarThickness: 40,    // Максимальная толщина (увеличено)
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: true,
                layout: {
                    padding: {
                        left: 10,
                        right: 20,
                        top: 10,
                        bottom: 10
                    }
                },
                plugins: {
                    title: {
                        display: false // Заголовок уже есть в HTML
                    },
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#3b82f6',
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: false,
                        position: 'nearest',
                        yAlign: 'center',
                        xAlign: 'left',
                        caretPadding: 15,
                        bodySpacing: 4,
                        titleSpacing: 4,
                        footerSpacing: 4,
                        padding: 12,
                        mode: 'nearest',
                        intersect: false,
                        callbacks: {
                            title: function(context) {
                                return context[0].label;
                            },
                            label: function(context) {
                                return `Количество: ${context.parsed.x}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.1)',
                            lineWidth: 1,
                            drawBorder: false
                        },
                        ticks: {
                            color: '#6b7280',
                            font: {
                                size: 12,
                                family: 'Inter, system-ui, sans-serif'
                            },
                            padding: 8
                        },
                        border: {
                            display: false
                        }
                    },
                    y: {
                        grid: {
                            display: false  // Убираем горизонтальные линии
                        },
                        ticks: {
                            color: '#374151',
                            font: {
                                size: 13,
                                family: 'Inter, system-ui, sans-serif',
                                weight: '500'
                            },
                            padding: 15,
                            crossAlign: 'far' // Выравнивание подписей
                        },
                        border: {
                            display: false
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                animation: {
                    duration: 800,
                    easing: 'easeOutQuart'
                },
                elements: {
                    bar: {
                        borderRadius: 8
                    }
                }
            }
        };
        
        // Добавляем обработчик кликов если он указан
        if (config.clickable && config.onClick) {
            chartConfig.options.onClick = config.onClick;
            // Добавляем курсор pointer при hover
            chartConfig.options.onHover = (event, activeElements) => {
                event.native.target.style.cursor = activeElements.length > 0 ? 'pointer' : 'default';
            };
        }
        
        // Отключаем datalabels для горизонтальных столбчатых графиков
        if (typeof ChartDataLabels !== 'undefined') {
            chartConfig.options.plugins.datalabels = {
                display: false
            };
        }
        
        this.charts[canvasId] = new Chart(canvas, chartConfig);
    }

    renderDonutChart(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        // Уничтожаем предыдущий график если он существует
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }
        
        const total = config.data.reduce((sum, value) => sum + value, 0);
        
        const chartConfig = {
            type: 'doughnut',
            data: {
                labels: config.labels,
                datasets: [{
                    data: config.data,
                    backgroundColor: config.colors || [
                        '#5DADE2', '#F7DC6F', '#85C1E9', '#F8C471', '#AED6F1'
                    ],
                    borderColor: [
                        '#3498DB', '#F1C40F', '#5DADE2', '#F39C12', '#85C1E9'
                    ],
                    borderWidth: 2,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                cutout: '50%', // Делает из pie chart donut chart
                plugins: {
                    title: {
                        display: false // Заголовок уже есть в HTML
                    },
                    legend: {
                        display: config.showLegend !== false, // Показываем легенду по умолчанию, скрываем только если явно указано false
                        position: config.legendPosition || 'right',
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed;
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                },
                layout: {
                    padding: {
                        left: 10,
                        right: 10,
                        top: 10,
                        bottom: 10
                    }
                }
            }
        };
        
        // Добавляем обработчик кликов если он указан
        if (config.clickable && config.onClick) {
            chartConfig.options.onClick = config.onClick;
        }
        
        // Добавляем настройки datalabels для отображения процентов на диаграмме
        if (typeof ChartDataLabels !== 'undefined') {
            chartConfig.options.plugins.datalabels = {
                display: true,
                formatter: (value, ctx) => {
                    const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                    return percentage > 2 ? `${percentage}%` : ''; // Показываем только если больше 2%
                },
                color: '#ffffff',
                font: {
                    weight: 'bold',
                    size: 14
                },
                anchor: 'center',
                align: 'center'
            };
        }
        
        this.charts[canvasId] = new Chart(canvas, chartConfig);
    }

    updateChartsDisplay() {
        // Обновляем отображение данных в таблице последних операций
        const tbody = document.querySelector('.o_amanat_dashboard .table tbody');
        if (tbody && this.state.recent_operations.length > 0) {
            tbody.innerHTML = this.state.recent_operations.map(op => `
                <tr>
                    <td>${op.type}</td>
                    <td>${op.date}</td>
                    <td>${this.formatCurrency(op.amount, op.currency)}</td>
                    <td>
                        <span class="badge ${op.status === 'Активен' ? 'bg-success' : 'bg-secondary'}">
                            ${op.status}
                        </span>
                    </td>
                </tr>
            `).join('');
        }
    }

    // Действия для открытия представлений
    async openTransfers() {
        // Подготавливаем домен для фильтрации если указаны даты
        let domain = [];
        if (this.state.dateRange1.start && this.state.dateRange1.end) {
            domain = [
                '&',
                ['create_date', '>=', this.state.dateRange1.start],
                ['create_date', '<=', this.state.dateRange1.end]
            ];
        }
        
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Переводы",
            res_model: "amanat.transfer",
            view_mode: "list,form,kanban",
            views: [[false, "list"], [false, "form"], [false, "kanban"]],
            target: "current",
            domain: domain,
            context: {
                search_default_active: 1,  // Активный фильтр по умолчанию
                group_by: ['state']  // Группировка по статусу
            }
        });
    }

    async openOrders() {
        // Подготавливаем домен для фильтрации если указаны даты
        let domain = [];
        if (this.state.dateRange1.start && this.state.dateRange1.end) {
            domain = [
                '&',
                ['create_date', '>=', this.state.dateRange1.start],
                ['create_date', '<=', this.state.dateRange1.end]
            ];
        }
        
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Ордера",
            res_model: "amanat.order",
            view_mode: "list,form,kanban",
            views: [[false, "list"], [false, "form"], [false, "kanban"]],
            target: "current",
            domain: domain,
            context: {
                group_by: ['state']  // Группировка по статусу
            }
        });
    }

    async openMoneyContainers() {
        // Для денежных контейнеров показываем сначала активные (с положительным балансом)
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Денежные контейнеры",
            res_model: "amanat.money",
            view_mode: "list,form,kanban",
            views: [[false, "list"], [false, "form"], [false, "kanban"]],
            target: "current",
            context: {
                search_default_positive: 1,  // Фильтр на положительные балансы
                group_by: ['currency']  // Группировка по валюте
            }
        });
    }

    async openMoneyContainersByCurrency(currency) {
        // Открываем денежные контейнеры с фильтром по конкретной валюте
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: `Денежные контейнеры - ${currency}`,
            res_model: "amanat.money",
            view_mode: "list,form,kanban",
            views: [[false, "list"], [false, "form"], [false, "kanban"]],
            target: "current",
            domain: [['currency', '=', currency]],
            context: {
                default_currency: currency,
                group_by: ['balance:sum']  // Группировка по сумме баланса
            }
        });
    }

    async openZayavki() {
        // Открываем заявки
        const action = {
            type: "ir.actions.act_window",
            name: "Заявки",
            res_model: "amanat.zayavka",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: []
        };
        
        // Добавляем фильтр по дате если установлен диапазон
        if (this.state.dateRange1.start && this.state.dateRange1.end) {
            action.domain = [
                ['date_placement', '>=', this.state.dateRange1.start],
                ['date_placement', '<=', this.state.dateRange1.end]
            ];
        }
        
        this.actionService.doAction(action);
    }

    async openZayavkiByContragent(contragentName) {
        // Открываем заявки с фильтром по контрагенту
        const action = {
            type: "ir.actions.act_window",
            name: `Заявки контрагента: ${contragentName}`,
            res_model: "amanat.zayavka",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [['contragent_id.name', '=', contragentName]]
        };
        
        // Добавляем фильтр по дате если установлен диапазон
        if (this.state.dateRange1.start && this.state.dateRange1.end) {
            action.domain = [
                '&',
                ['contragent_id.name', '=', contragentName],
                '&',
                ['date_placement', '>=', this.state.dateRange1.start],
                ['date_placement', '<=', this.state.dateRange1.end]
            ];
        }
        
        this.actionService.doAction(action);
    }

    async openZayavkiByAgent(agentName) {
        // Открываем заявки с фильтром по агенту
        const action = {
            type: "ir.actions.act_window",
            name: `Заявки агента: ${agentName}`,
            res_model: "amanat.zayavka",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [['agent_id.name', '=', agentName]]
        };
        
        // Добавляем фильтр по дате если установлен диапазон
        if (this.state.dateRange1.start && this.state.dateRange1.end) {
            action.domain = [
                '&',
                ['agent_id.name', '=', agentName],
                '&',
                ['date_placement', '>=', this.state.dateRange1.start],
                ['date_placement', '<=', this.state.dateRange1.end]
            ];
        }
        
        this.actionService.doAction(action);
    }

    async openZayavkiByClient(clientName) {
        // Открываем заявки с фильтром по клиенту
        const action = {
            type: "ir.actions.act_window",
            name: `Заявки клиента: ${clientName}`,
            res_model: "amanat.zayavka",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [['client_id.name', '=', clientName]]
        };
        
        // Добавляем фильтр по дате если установлен диапазон
        if (this.state.dateRange1.start && this.state.dateRange1.end) {
            action.domain = [
                '&',
                ['client_id.name', '=', clientName],
                '&',
                ['date_placement', '>=', this.state.dateRange1.start],
                ['date_placement', '<=', this.state.dateRange1.end]
            ];
        }
        
        this.actionService.doAction(action);
    }

    async refreshDashboard() {
        this.state.isLoading = true;
        await this.loadDashboardData();
    }

    // Форматирование чисел
    formatNumber(value) {
        return new Intl.NumberFormat('ru-RU').format(value || 0);
    }

    formatCurrency(amount, currency) {
        if (!amount) return '0';
        
        const cryptoCurrencies = ['USDT', 'BTC', 'ETH'];
        if (cryptoCurrencies.includes(currency?.toUpperCase())) {
            return `${this.formatNumber(amount)} ${currency}`;
        }
        
        try {
            return new Intl.NumberFormat('ru-RU', {
                style: 'currency',
                currency: currency || 'RUB',
                minimumFractionDigits: 0,
                maximumFractionDigits: 0
            }).format(amount);
        } catch (e) {
            return `${this.formatNumber(amount)} ${currency || ''}`;
        }
    }

    // Расчет процентов
    getPercentage(value, total) {
        if (!total || total === 0) return 0;
        return Math.round((value / total) * 100);
    }

    onDateRange1Change(ev) {
        // Обработка изменения первого диапазона
        // Автоматически применяем фильтры если выбраны обе даты
        if (this.state.dateRange1.start && this.state.dateRange1.end) {
            this.applyDateRanges();
        }
    }
    
    onDateRange2Change(ev) {
        // Обработка изменения второго диапазона
        // Автоматически применяем фильтры если выбраны обе даты
        if (this.state.dateRange2.start && this.state.dateRange2.end) {
            this.applyDateRanges();
        }
    }
    
    async applyDateRanges() {
        this.state.isLoading = true;
        try {
            console.log('applyDateRanges called with ranges:', {
                range1: this.state.dateRange1,
                range2: this.state.dateRange2
            });
            
            // Если указаны оба диапазона, используем метод сравнения
            if (this.state.dateRange1.start && this.state.dateRange1.end && 
                this.state.dateRange2.start && this.state.dateRange2.end) {
                
                console.log('Loading comparison data for both periods...');
                
                // Используем специальный метод для сравнения заявок
                const comparisonData = await this.orm.call('amanat.dashboard', 'get_zayavki_comparison_data', [], {
                    date_from1: this.state.dateRange1.start,
                    date_to1: this.state.dateRange1.end,
                    date_from2: this.state.dateRange2.start,
                    date_to2: this.state.dateRange2.end
                });
                
                // Получаем данные сравнения для графиков
                const chartComparisonData = await this.orm.call('amanat.dashboard', 'get_comparison_chart_data', [], {
                    date_from1: this.state.dateRange1.start,
                    date_to1: this.state.dateRange1.end,
                    date_from2: this.state.dateRange2.start,
                    date_to2: this.state.dateRange2.end
                });
                
                // Также загружаем полные данные для первого диапазона
                const data1 = await this.orm.call('amanat.dashboard', 'get_dashboard_data', [], {
                    date_from: this.state.dateRange1.start,
                    date_to: this.state.dateRange1.end
                });
                
                console.log('Comparison data loaded:', {
                    comparisonData,
                    chartComparisonData,
                    data1
                });
                
                this.state.comparisonData = comparisonData;
                this.state.chartComparisonData = chartComparisonData;
                this.updateStateFromData(data1);
                
            } else {
                console.log('Loading data for single period...');
                
                // Загружаем данные только для первого диапазона
                const data1 = await this.orm.call('amanat.dashboard', 'get_dashboard_data', [], {
                    date_from: this.state.dateRange1.start || undefined,
                    date_to: this.state.dateRange1.end || undefined
                });
                
                console.log('Single period data loaded:', data1);
                
                this.state.comparisonData = null;
                this.state.chartComparisonData = null;
                this.updateStateFromData(data1);
            }
            
            // Перерисовываем графики
            setTimeout(() => {
                console.log('Reinitializing charts with state:', {
                    hasComparisonData: !!this.state.chartComparisonData,
                    zayavkiData: this.state.zayavki
                });
                this.initializeAllCharts();
            }, 100);
            
        } catch (error) {
            console.error('Error loading comparison data:', error);
        } finally {
            this.state.isLoading = false;
        }
    }
    
    async resetDateRanges() {
        // Сбрасываем диапазоны на значения по умолчанию
        this.state.dateRange1.start = '';
        this.state.dateRange1.end = '';
        this.state.dateRange2.start = '';
        this.state.dateRange2.end = '';
        
        // Сбрасываем данные сравнения
        this.state.comparisonData = null;
        this.state.chartComparisonData = null;
        
        // Перезагружаем данные без фильтров
        await this.loadDashboardData();
    }
    
    updateStateFromData(data) {
        if (data) {
            // Основные показатели
            this.state.transfers = {
                total: data.transfers_count || 0,
                active: data.transfers_active || 0,
                closed: data.transfers_closed || 0,
                amount: data.transfers_amount || 0,
                byStatus: data.transfers_by_status || {},
                byCurrency: data.transfers_by_currency || {},
                byMonth: data.transfers_by_month || [],
                byCountry: data.transfers_by_country || {},
                byType: data.transfers_by_type || {}
            };
            
            this.state.orders = {
                total: data.orders_count || 0,
                draft: data.orders_draft || 0,
                done: data.orders_done || 0,
                byStatus: data.orders_by_status || {},
                byMonth: data.orders_by_month || []
            };
            
            this.state.money = {
                total: data.money_containers_count || 0,
                positive: data.money_containers_positive || 0,
                debt: data.money_containers_debt || 0
            };
            
            this.state.currencies = {
                rub: data.currency_rub || 0,
                usd: data.currency_usd || 0,
                usdt: data.currency_usdt || 0,
                euro: data.currency_euro || 0,
                cny: data.currency_cny || 0
            };
            
            // ==================== ЗАЯВКИ ====================
            this.state.zayavki = {
                total: data.zayavki_count || 0,
                closed: data.zayavki_closed || 0,
                closedAmount: data.zayavki_closed_amount || 0,
                usdEquivalent: data.zayavki_usd_equivalent || 0,
                byStatus: data.zayavki_by_status || {},
                byMonth: data.zayavki_by_month || [],
                byCurrency: data.zayavki_by_currency || {},
                byDealType: data.zayavki_by_deal_type || {},
                contragentsByZayavki: data.top_contragents_by_zayavki || [],
                contragentAvgCheck: data.contragent_avg_check || [],
                agentsByZayavki: data.agent_zayavki_list || [],
                agentAvgAmount: data.agent_avg_amount_list || [],
                clientsByZayavki: data.client_zayavki_list || [],
                clientAvgAmount: data.client_avg_amount_list || [],
                subagentsByZayavki: data.subagent_zayavki_list || [],
                payersByZayavki: data.payer_zayavki_list || [],
                managersByZayavki: data.managers_by_zayavki || [],
                managersClosedZayavki: data.managers_closed_zayavki || [],
                statusDistribution: data.zayavki_status_distribution || [],
                dealCycles: data.zayavki_deal_cycles || [],
                contragentRewardPercent: data.contragent_avg_reward_percent || [],
                managersEfficiency: data.managers_efficiency_data || []
            };
            
            console.log('После updateStateFromData - managersEfficiency:', this.state.zayavki.managersEfficiency);
            
            // Дополнительные данные для графиков
            this.state.contragents = data.top_contragents || [];
            this.state.payers = data.top_payers || [];
            this.state.managers = data.managers_efficiency || [];
            this.state.weekdayLoad = data.weekday_load || {};
            this.state.processingTime = data.processing_time || [];
            this.state.dynamics = {
                transfers: data.transfers_dynamics || [],
                orders: data.orders_dynamics || []
            };
            this.state.recent_operations = data.recent_operations || [];
        }
    }


    
    renderPieChartWithPercentage(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        // Уничтожаем предыдущий график если он существует
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }
        
        const total = config.data.reduce((sum, value) => sum + value, 0);
        
        const chartConfig = {
            type: 'pie',
            data: {
                labels: config.labels,
                datasets: [{
                    data: config.data,
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 206, 86, 0.8)',
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(153, 102, 255, 0.8)'
                    ],
                    borderColor: [
                        'rgba(255, 99, 132, 1)',
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 206, 86, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(153, 102, 255, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true,
                        text: config.title
                    },
                    legend: {
                        display: config.showLegend !== false, // Показываем легенду по умолчанию, скрываем только если явно указано false
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed;
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        };
        
        // Добавляем обработчик кликов если он указан
        if (config.clickable && config.onClick) {
            chartConfig.options.onClick = config.onClick;
        }
        
        // Используем переданные цвета если они есть
        if (config.colors) {
            chartConfig.data.datasets[0].backgroundColor = config.colors;
            chartConfig.data.datasets[0].borderColor = config.colors.map(c => c.replace('0.8', '1'));
        }
        
        // Добавляем настройки datalabels только если плагин загружен
        if (typeof ChartDataLabels !== 'undefined') {
            chartConfig.options.plugins.datalabels = {
                formatter: (value, ctx) => {
                    const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                    return percentage > 5 ? `${percentage}%` : ''; // Показываем только если больше 5%
                },
                color: '#fff',
                font: {
                    weight: 'bold',
                    size: 12
                }
            };
        }
        
        this.charts[canvasId] = new Chart(canvas, chartConfig);
    }
    
    renderComparisonLineChart(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        // Уничтожаем предыдущий график если он существует
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }
        
        // Подготавливаем datasets для наложения
        const datasets = [];
        
        // Период 1 (синий)
        if (config.period1Data && config.period1Data.length > 0) {
            datasets.push({
                label: config.period1Label || 'Период 1',
                data: config.period1Data,
                borderColor: '#3b82f6',  // Синий
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: config.tension || 0.3,
                pointStyle: 'circle',
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: '#3b82f6',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                fill: false,
                order: 2  // Задний план
            });
        }
        
        // Период 2 (красный)
        if (config.period2Data && config.period2Data.length > 0) {
            datasets.push({
                label: config.period2Label || 'Период 2',
                data: config.period2Data,
                borderColor: '#ef4444',  // Красный
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                tension: config.tension || 0.3,
                pointStyle: 'circle',
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: '#ef4444',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                fill: false,
                order: 1  // Передний план
            });
        }
        
        const chartConfig = {
            type: 'line',
            data: {
                labels: config.labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    title: {
                        display: false
                    },
                    legend: {
                        display: config.showLegend !== false, // Показываем легенду по умолчанию, скрываем только если явно указано false
                        position: 'top',
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            font: {
                                size: 12,
                                family: 'Inter, system-ui, sans-serif'
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#3b82f6',
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: true,
                        position: 'nearest',
                        callbacks: {
                            title: function(context) {
                                return `${config.xAxisLabel || 'X'}: ${context[0].label}`;
                            },
                            label: function(context) {
                                const datasetLabel = context.dataset.label;
                                const value = context.parsed.y;
                                return `${datasetLabel}: ${value}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: config.xAxisLabel || '',
                            font: {
                                size: 14,
                                family: 'Inter, system-ui, sans-serif',
                                weight: '500'
                            }
                        },
                        grid: {
                            display: true,
                            color: 'rgba(0,0,0,0.1)'
                        },
                        ticks: {
                            color: '#6b7280',
                            font: {
                                size: 12,
                                family: 'Inter, system-ui, sans-serif'
                            }
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: config.yAxisLabel || '',
                            font: {
                                size: 14,
                                family: 'Inter, system-ui, sans-serif',
                                weight: '500'
                            }
                        },
                        beginAtZero: config.startAtZero !== false,
                        grid: {
                            display: true,
                            color: 'rgba(0,0,0,0.1)'
                        },
                        ticks: {
                            color: '#6b7280',
                            font: {
                                size: 12,
                                family: 'Inter, system-ui, sans-serif'
                            }
                        }
                    }
                },
                animation: {
                    duration: 800,
                    easing: 'easeOutQuart'
                }
            }
        };
        
        // Добавляем обработчик кликов если он указан
        if (config.clickable && config.onClick) {
            chartConfig.options.onClick = config.onClick;
        }
        
        // Отключаем datalabels для линейных сравнительных графиков
        if (typeof ChartDataLabels !== 'undefined') {
            chartConfig.options.plugins.datalabels = {
                display: false
            };
        }
        
        this.charts[canvasId] = new Chart(canvas, chartConfig);
    }

    getDateRangeLabel(period) {
        const { dateRange1, dateRange2 } = this.state;
        if (period === 'period1') {
            return `${dateRange1.start} - ${dateRange1.end}`;
        } else if (period === 'period2') {
            return `${dateRange2.start} - ${dateRange2.end}`;
        }
        return '';
    }

    renderSmoothLineChart(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        // Уничтожаем предыдущий график если он существует
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }
        
        const chartConfig = {
            type: 'line',
            data: {
                labels: config.labels,
                datasets: [{
                    label: config.title,
                    data: config.data,
                    borderColor: config.color || '#3498DB',
                    backgroundColor: (config.color || '#3498DB').replace('1)', '0.1)'),
                    tension: config.tension || 0.3, // Smooth lines
                    pointStyle: config.pointStyle || 'circle', // Plot dots on lines
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: config.color || '#3498DB',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    title: {
                        display: false // Заголовок в HTML
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: config.xAxisLabel || ''
                        },
                        grid: {
                            display: true,
                            color: 'rgba(0,0,0,0.1)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: config.yAxisLabel || ''
                        },
                        beginAtZero: config.startAtZero !== false,
                        grid: {
                            display: true,
                            color: 'rgba(0,0,0,0.1)'
                        }
                    }
                }
            }
        };
        
        // Добавляем обработчик кликов если он указан
        if (config.clickable && config.onClick) {
            chartConfig.options.onClick = config.onClick;
        }
        
        // Отключаем datalabels для линейных графиков
        if (typeof ChartDataLabels !== 'undefined') {
            chartConfig.options.plugins.datalabels = {
                display: false
            };
        }
        
        this.charts[canvasId] = new Chart(canvas, chartConfig);
    }

    renderComparisonSmoothLineChart(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        // Уничтожаем предыдущий график если он существует
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }
        
        // Подготавливаем datasets для наложения
        const datasets = [];
        
        // Период 1 (синий)
        if (config.period1Data && config.period1Data.length > 0) {
            datasets.push({
                label: config.period1Label || 'Период 1',
                data: config.period1Data,
                borderColor: '#3b82f6',  // Синий
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: config.tension || 0.3,
                pointStyle: 'circle',
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: '#3b82f6',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                fill: false,
                order: 2  // Задний план
            });
        }
        
        // Период 2 (красный)
        if (config.period2Data && config.period2Data.length > 0) {
            datasets.push({
                label: config.period2Label || 'Период 2',
                data: config.period2Data,
                borderColor: '#ef4444',  // Красный
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                tension: config.tension || 0.3,
                pointStyle: 'circle',
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: '#ef4444',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                fill: false,
                order: 1  // Передний план
            });
        }
        
        const chartConfig = {
            type: 'line',
            data: {
                labels: config.labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    title: {
                        display: false
                    },
                    legend: {
                        display: config.showLegend !== false, // Показываем легенду по умолчанию, скрываем только если явно указано false
                        position: 'top',
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            font: {
                                size: 12,
                                family: 'Inter, system-ui, sans-serif'
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#3b82f6',
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: true,
                        position: 'nearest',
                        callbacks: {
                            title: function(context) {
                                return `${config.xAxisLabel || 'X'}: ${context[0].label}`;
                            },
                            label: function(context) {
                                const datasetLabel = context.dataset.label;
                                const value = context.parsed.y;
                                return `${datasetLabel}: ${value}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: config.xAxisLabel || '',
                            font: {
                                size: 14,
                                family: 'Inter, system-ui, sans-serif',
                                weight: '500'
                            }
                        },
                        grid: {
                            display: true,
                            color: 'rgba(0,0,0,0.1)'
                        },
                        ticks: {
                            color: '#6b7280',
                            font: {
                                size: 12,
                                family: 'Inter, system-ui, sans-serif'
                            }
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: config.yAxisLabel || '',
                            font: {
                                size: 14,
                                family: 'Inter, system-ui, sans-serif',
                                weight: '500'
                            }
                        },
                        beginAtZero: config.startAtZero !== false,
                        grid: {
                            display: true,
                            color: 'rgba(0,0,0,0.1)'
                        },
                        ticks: {
                            color: '#6b7280',
                            font: {
                                size: 12,
                                family: 'Inter, system-ui, sans-serif'
                            }
                        }
                    }
                },
                animation: {
                    duration: 800,
                    easing: 'easeOutQuart'
                }
            }
        };
        
        // Добавляем обработчик кликов если он указан
        if (config.clickable && config.onClick) {
            chartConfig.options.onClick = config.onClick;
        }
        
        // Отключаем datalabels для линейных сравнительных графиков
        if (typeof ChartDataLabels !== 'undefined') {
            chartConfig.options.plugins.datalabels = {
                display: false
            };
        }
        
        this.charts[canvasId] = new Chart(canvas, chartConfig);
    }

    async openZayavkiBySubagent(subagentName) {
        // Открываем заявки с фильтром по субагенту
        const action = {
            type: "ir.actions.act_window",
            name: `Заявки субагента: ${subagentName}`,
            res_model: "amanat.zayavka",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [['subagent_ids.name', '=', subagentName]]
        };
        
        // Добавляем фильтр по дате если установлен диапазон
        if (this.state.dateRange1.start && this.state.dateRange1.end) {
            action.domain = [
                '&',
                ['subagent_ids.name', '=', subagentName],
                '&',
                ['date_placement', '>=', this.state.dateRange1.start],
                ['date_placement', '<=', this.state.dateRange1.end]
            ];
        }
        
        this.actionService.doAction(action);
    }

    async openZayavkiByPayer(payerName) {
        // Открываем заявки с фильтром по платежщику субагента
        const action = {
            type: "ir.actions.act_window",
            name: `Заявки платежщика: ${payerName}`,
            res_model: "amanat.zayavka",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [['subagent_payer_ids.name', '=', payerName]]
        };
        
        // Добавляем фильтр по дате если установлен диапазон
        if (this.state.dateRange1.start && this.state.dateRange1.end) {
            action.domain = [
                '&',
                ['subagent_payer_ids.name', '=', payerName],
                '&',
                ['date_placement', '>=', this.state.dateRange1.start],
                ['date_placement', '<=', this.state.dateRange1.end]
            ];
        }
        
        this.actionService.doAction(action);
    }

    async openZayavkiByManager(managerName) {
        // Открываем заявки с фильтром по менеджеру
        const action = {
            type: "ir.actions.act_window",
            name: `Заявки менеджера: ${managerName}`,
            res_model: "amanat.zayavka",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [
                '&',
                ['manager_ids.name', '=', managerName],
                '&',
                ['hide_in_dashboard', '!=', true],
                ['status', '!=', 'cancel']
            ]
        };
        
        // Добавляем фильтр по дате если установлен диапазон
        if (this.state.dateRange1.start && this.state.dateRange1.end) {
            action.domain = [
                '&',
                ['manager_ids.name', '=', managerName],
                '&',
                ['hide_in_dashboard', '!=', true],
                '&',
                ['status', '!=', 'cancel'],
                '&',
                ['date_placement', '>=', this.state.dateRange1.start],
                ['date_placement', '<=', this.state.dateRange1.end]
            ];
        }
        
        this.actionService.doAction(action);
    }

    async openZayavkiByManagerClosed(managerName) {
        // Открываем заявки с фильтром по менеджеру для ЗАКРЫТЫХ заявок
        const action = {
            type: "ir.actions.act_window",
            name: `Закрытые заявки менеджера: ${managerName}`,
            res_model: "amanat.zayavka",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [
                '&',
                ['manager_ids.name', '=', managerName],
                '&',
                ['hide_in_dashboard', '!=', true],
                ['status', '=', 'close']  // Только закрытые заявки
            ]
        };
        
        // Добавляем фильтр по дате если установлен диапазон
        if (this.state.dateRange1.start && this.state.dateRange1.end) {
            action.domain = [
                '&',
                ['manager_ids.name', '=', managerName],
                '&',
                ['hide_in_dashboard', '!=', true],
                '&',
                ['status', '=', 'close'],
                '&',
                ['date_placement', '>=', this.state.dateRange1.start],
                ['date_placement', '<=', this.state.dateRange1.end]
            ];
        }
        
        this.actionService.doAction(action);
    }

    async openZayavkiByStatus(statusName) {
        // Открываем заявки с фильтром по статусу
        let statusValue = statusName;
        
        // Мапим отображаемые имена обратно в значения базы данных
        if (statusName === 'заявка закрыта') {
            statusValue = 'close';
        } else if (statusName === 'отменено клиентом') {
            statusValue = 'cancel';
        } else if (statusName === '15. возврат') {
            statusValue = 'return';
        }
        
        const action = {
            type: "ir.actions.act_window",
            name: `Заявки со статусом: ${statusName}`,
            res_model: "amanat.zayavka",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [
                '&',
                ['status', '=', statusValue],
                ['hide_in_dashboard', '!=', true]
            ]
        };
        
        // Добавляем фильтр по дате если установлен диапазон
        if (this.state.dateRange1.start && this.state.dateRange1.end) {
            action.domain = [
                '&',
                ['status', '=', statusValue],
                '&',
                ['hide_in_dashboard', '!=', true],
                '&',
                ['date_placement', '>=', this.state.dateRange1.start],
                ['date_placement', '<=', this.state.dateRange1.end]
            ];
        }
        
        this.actionService.doAction(action);
    }

    async openZayavkiByCycle(cycleDays) {
        // Открываем заявки с фильтром по циклу сделки
        const action = {
            type: "ir.actions.act_window",
            name: `Заявки с циклом сделки: ${cycleDays} дней`,
            res_model: "amanat.zayavka",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [
                '&',
                ['hide_in_dashboard', '!=', true],
                ['status', '!=', 'cancel']
                // TODO: добавить фильтр по реальному полю цикла сделки
                // Пока открываем все заявки с базовыми фильтрами
            ]
        };
        
        // Добавляем фильтр по дате если установлен диапазон
        if (this.state.dateRange1.start && this.state.dateRange1.end) {
            action.domain = [
                '&',
                ['hide_in_dashboard', '!=', true],
                '&',
                ['status', '!=', 'cancel'],
                '&',
                ['date_placement', '>=', this.state.dateRange1.start],
                ['date_placement', '<=', this.state.dateRange1.end]
            ];
        }
        
        this.actionService.doAction(action);
    }

    /**
     * Проверить, есть ли данные для отображения графика
     * @param {Array} data - массив данных
     * @returns {boolean} true если есть данные для отображения
     */
    hasChartData(data) {
        return data && Array.isArray(data) && data.length > 0;
    }

    /**
     * Показать сообщение "Нет данных" вместо графика
     * @param {string} canvasId - ID canvas элемента
     * @param {string} title - заголовок графика
     */
    showNoDataMessage(canvasId, title = 'График') {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        // Очищаем canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Настройки текста
        ctx.fillStyle = '#6c757d';
        ctx.font = '16px system-ui, -apple-system, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        // Рисуем сообщение в центре
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        
        ctx.fillText('📊 Нет данных по этому диапазону', centerX, centerY - 10);
        ctx.font = '14px system-ui, -apple-system, sans-serif';
        ctx.fillStyle = '#9ca3af';
        ctx.fillText('Попробуйте выбрать другой период', centerX, centerY + 15);
    }

    async openManagerInfo(managerName) {
        // Открываем карточку менеджера
        const action = {
            type: "ir.actions.act_window",
            name: `Менеджер: ${managerName}`,
            res_model: "amanat.manager",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            domain: [['name', '=', managerName]]
        };
        
        this.actionService.doAction(action);
    }

    renderComparisonHorizontalBarChart(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        // Уничтожаем предыдущий график если он существует
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }
        
        // Создаем градиенты для обоих периодов
        const ctx = canvas.getContext('2d');
        
        // Градиент для периода 1 (синий)
        const gradient1 = ctx.createLinearGradient(0, 0, canvas.width, 0);
        gradient1.addColorStop(0, '#1e3a8a');    // Темно-синий
        gradient1.addColorStop(0.5, '#3b82f6');  // Средний синий  
        gradient1.addColorStop(1, '#60a5fa');    // Светло-синий
        
        // Градиент для периода 2 (красный)
        const gradient2 = ctx.createLinearGradient(0, 0, canvas.width, 0);
        gradient2.addColorStop(0, '#dc2626');    // Темно-красный
        gradient2.addColorStop(0.5, '#ef4444');  // Средний красный  
        gradient2.addColorStop(1, '#f87171');    // Светло-красный
        
        // Подготавливаем datasets для наложения
        const datasets = [];
        
        // Период 1 (синий, на заднем плане)
        if (config.period1Data && config.period1Data.length > 0) {
            datasets.push({
                label: config.period1Label || 'Период 1',
                data: config.period1Data,
                backgroundColor: gradient1,
                borderColor: 'transparent',
                borderWidth: 0,
                borderRadius: 8,
                borderSkipped: false,
                barThickness: 45,
                maxBarThickness: 50,
                order: 2  // Задний план
            });
        }
        
        // Период 2 (красный, на переднем плане, немного тоньше)
        if (config.period2Data && config.period2Data.length > 0) {
            datasets.push({
                label: config.period2Label || 'Период 2',
                data: config.period2Data,
                backgroundColor: gradient2,
                borderColor: 'transparent',
                borderWidth: 0,
                borderRadius: 8,
                borderSkipped: false,
                barThickness: 30,   // Меньше чем период 1
                maxBarThickness: 35,
                order: 1  // Передний план
            });
        }
        
        const chartConfig = {
            type: 'bar',
            data: {
                labels: config.labels,
                datasets: datasets
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: true,
                layout: {
                    padding: {
                        left: 10,
                        right: 20,
                        top: 10,
                        bottom: 10
                    }
                },
                plugins: {
                    title: {
                        display: false
                    },
                    legend: {
                        display: config.showLegend !== false, // Показываем легенду по умолчанию, скрываем только если явно указано false
                        position: 'top',
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            pointStyle: 'rect',
                            font: {
                                size: 12,
                                family: 'Inter, system-ui, sans-serif'
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#3b82f6',
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: true,
                        position: 'nearest',
                        yAlign: 'center',
                        xAlign: 'left',
                        caretPadding: 15,
                        bodySpacing: 4,
                        titleSpacing: 4,
                        footerSpacing: 4,
                        padding: 12,
                        mode: 'nearest',
                        intersect: false,
                        callbacks: {
                            title: function(context) {
                                return context[0].label;
                            },
                            label: function(context) {
                                const datasetLabel = context.dataset.label;
                                const value = context.parsed.x;
                                return `${datasetLabel}: ${value}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        stacked: false,  // Не стекаем, а накладываем
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.1)',
                            lineWidth: 1,
                            drawBorder: false
                        },
                        ticks: {
                            color: '#6b7280',
                            font: {
                                size: 12,
                                family: 'Inter, system-ui, sans-serif'
                            },
                            padding: 8
                        },
                        border: {
                            display: false
                        }
                    },
                    y: {
                        stacked: false,  // Не стекаем, а накладываем
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#374151',
                            font: {
                                size: 13,
                                family: 'Inter, system-ui, sans-serif',
                                weight: '500'
                            },
                            padding: 15,
                            crossAlign: 'far'
                        },
                        border: {
                            display: false
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                animation: {
                    duration: 800,
                    easing: 'easeOutQuart'
                },
                elements: {
                    bar: {
                        borderRadius: 8
                    }
                }
            }
        };
        
        // Добавляем обработчик кликов если он указан
        if (config.clickable && config.onClick) {
            chartConfig.options.onClick = config.onClick;
            // Добавляем курсор pointer при hover
            chartConfig.options.onHover = (event, activeElements) => {
                event.native.target.style.cursor = activeElements.length > 0 ? 'pointer' : 'default';
            };
        }
        
        // Отключаем datalabels для сравнительных графиков
        if (typeof ChartDataLabels !== 'undefined') {
            chartConfig.options.plugins.datalabels = {
                display: false
            };
        }
        
        this.charts[canvasId] = new Chart(canvas, chartConfig);
    }
}

registry.category("actions").add("amanat_dashboard", AmanatDashboard); 
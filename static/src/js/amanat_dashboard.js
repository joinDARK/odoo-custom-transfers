/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { loadJS } from "@web/core/assets";

export class AmanatDashboard extends Component {
    static template = "amanat.AmanatDashboard";
    static props = {};

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
                clientsByZayavki: [],
                clientAvgAmount: [],
                subagentPayersByZayavki: []
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
            comparisonData: null
        });
        
        // Хранилище для графиков
        this.charts = {};
        
        // Инициализация при загрузке компонента
        onMounted(async () => {
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
        });
        
        // Удаление графиков при размонтировании
        onWillUnmount(() => {
            Object.values(this.charts).forEach(chart => {
                if (chart) chart.destroy();
            });
        });
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
        return new Promise((resolve, reject) => {
            if (typeof Chart !== 'undefined') {
                console.log('Chart.js already loaded');
                resolve();
                return;
            }
            
            console.log('Loading Chart.js from CDN...');
            
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js';
            script.onload = () => {
                console.log('Chart.js loaded successfully');
                
                // Проверяем что Chart действительно доступен
                if (typeof Chart === 'undefined') {
                    console.error('Chart.js loaded but Chart is still undefined');
                    reject(new Error('Chart.js did not load properly'));
                    return;
                }
                
                // Плагин для отображения процентов - опционально
                const datalabelsScript = document.createElement('script');
                datalabelsScript.src = 'https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js';
                datalabelsScript.onload = () => {
                    if (typeof ChartDataLabels !== 'undefined') {
                        Chart.register(ChartDataLabels);
                        console.log('Chart.js datalabels plugin registered');
                    }
                    resolve();
                };
                datalabelsScript.onerror = () => {
                    console.warn('Failed to load Chart.js datalabels plugin, continuing without it');
                    resolve(); // Продолжаем без плагина
                };
                document.head.appendChild(datalabelsScript);
            };
            script.onerror = (error) => {
                console.error('Failed to load Chart.js:', error);
                reject(error);
            };
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
        const firstChartElement = document.getElementById('transfers-status-pie');
        if (!firstChartElement) {
            console.warn('Chart canvas elements not found, retrying...');
            setTimeout(() => this.initializeAllCharts(), 100);
            return;
        }
        
        console.log('Initializing all charts with data:', {
            transfers: this.state.transfers,
            orders: this.state.orders,
            currencies: this.state.currencies
        });
        
        // Проверяем все canvas элементы
        const expectedCanvasIds = [
            'transfers-status-pie',
            'orders-status-pie',
            'top-contragents-chart',
            'transfers-currency-chart',
            'transfers-monthly-chart',
            'orders-monthly-chart',
            'transfers-country-chart',
            'top-payers-chart',
            'managers-efficiency-chart',
            'rub-distribution-pie',
            'usd-distribution-pie',
            'eur-distribution-pie',
            'total-balance-doughnut',
            'transfers-dynamics-line',
            'orders-dynamics-line',
            'transfers-type-bar',
            'weekday-load-bar',
            'processing-time-bar',
            'import-export-donut',
            'contragents-by-zayavki-chart',
            'contragent-avg-check-chart',
            'agents-by-zayavki-chart',
            'clients-by-zayavki-chart',
            'client-avg-amount-chart',
            'subagent-payers-by-zayavki-chart'
        ];
        
        const missingCanvasIds = expectedCanvasIds.filter(id => !document.getElementById(id));
        if (missingCanvasIds.length > 0) {
            console.warn('Missing canvas elements:', missingCanvasIds);
        }
        
        try {
            // 1. Переводы по статусам (круговая с процентами)
            const transfersStatusData = Object.values(this.state.transfers.byStatus);
            if (transfersStatusData.length > 0) {
                this.renderPieChartWithPercentage('transfers-status-pie', {
                    labels: Object.keys(this.state.transfers.byStatus),
                    data: transfersStatusData,
                    title: 'Переводы по статусам'
                });
            }
            
            // 2. Ордера по статусам (круговая с процентами) 
            const ordersStatusData = Object.values(this.state.orders.byStatus);
            if (ordersStatusData.length > 0) {
                this.renderPieChartWithPercentage('orders-status-pie', {
                    labels: Object.keys(this.state.orders.byStatus),
                    data: ordersStatusData,
                    title: 'Ордера по статусам'
                });
            }
            
            // 3. Топ контрагентов (горизонтальная столбчатая)
            if (this.state.contragents.length > 0) {
                this.renderHorizontalBarChart('top-contragents-chart', {
                    labels: this.state.contragents.map(c => c.name),
                    data: this.state.contragents.map(c => c.count),
                    title: 'Топ контрагентов по переводам'
                });
            }
            
            // 4. Переводы по валютам (горизонтальная столбчатая)
            const transfersByCurrencyData = Object.values(this.state.transfers.byCurrency);
            if (transfersByCurrencyData.length > 0) {
                this.renderHorizontalBarChart('transfers-currency-chart', {
                    labels: Object.keys(this.state.transfers.byCurrency),
                    data: transfersByCurrencyData,
                    title: 'Переводы по валютам'
                });
            }
            
            // 5. Переводы по месяцам (линейная)
            if (this.state.transfers.byMonth && this.state.transfers.byMonth.length > 0) {
                this.renderLineChart('transfers-monthly-chart', {
                    labels: this.state.transfers.byMonth.map(item => item.month),
                    data: this.state.transfers.byMonth.map(item => item.count),
                    title: 'Переводы по месяцам'
                });
            }
            
            // 6. Ордера по месяцам (линейная)
            if (this.state.orders.byMonth && this.state.orders.byMonth.length > 0) {
                this.renderLineChart('orders-monthly-chart', {
                    labels: this.state.orders.byMonth.map(item => item.month),
                    data: this.state.orders.byMonth.map(item => item.count),
                    title: 'Ордера по месяцам'
                });
            }
            
            // 7. Переводы по странам (горизонтальная столбчатая)
            const transfersByCountryData = Object.values(this.state.transfers.byCountry);
            if (transfersByCountryData.length > 0) {
                this.renderHorizontalBarChart('transfers-country-chart', {
                    labels: Object.keys(this.state.transfers.byCountry),
                    data: transfersByCountryData,
                    title: 'Переводы по странам'
                });
            }
            
            // 8. Топ плательщиков (горизонтальная столбчатая)
            if (this.state.payers.length > 0) {
                this.renderHorizontalBarChart('top-payers-chart', {
                    labels: this.state.payers.map(p => p.name),
                    data: this.state.payers.map(p => p.amount),
                    title: 'Топ плательщиков'
                });
            }
            
            // 9. Эффективность менеджеров (горизонтальная столбчатая)
            if (this.state.managers.length > 0) {
                this.renderHorizontalBarChart('managers-efficiency-chart', {
                    labels: this.state.managers.map(m => m.name),
                    data: this.state.managers.map(m => m.processed || m.efficiency || 0),
                    title: 'Эффективность менеджеров'
                });
            }
            
            // 10-13. Распределение валют (круговые с процентами)
            const rubBalance = Math.abs(this.state.currencies.rub || 0);
            if (rubBalance > 0) {
                this.renderPieChartWithPercentage('rub-distribution-pie', {
                    labels: ['Положительный', 'Отрицательный'],
                    data: [Math.max(0, this.state.currencies.rub), Math.abs(Math.min(0, this.state.currencies.rub))],
                    title: 'Распределение RUB'
                });
            }
            
            const usdBalance = Math.abs(this.state.currencies.usd || 0);
            if (usdBalance > 0) {
                this.renderPieChartWithPercentage('usd-distribution-pie', {
                    labels: ['Положительный', 'Отрицательный'],
                    data: [Math.max(0, this.state.currencies.usd), Math.abs(Math.min(0, this.state.currencies.usd))],
                    title: 'Распределение USD'
                });
            }
            
            const euroBalance = Math.abs(this.state.currencies.euro || 0);
            if (euroBalance > 0) {
                this.renderPieChartWithPercentage('eur-distribution-pie', {
                    labels: ['Положительный', 'Отрицательный'],
                    data: [Math.max(0, this.state.currencies.euro), Math.abs(Math.min(0, this.state.currencies.euro))],
                    title: 'Распределение EUR'
                });
            }
            
            // Общий баланс по валютам
            const totalBalances = [
                Math.abs(this.state.currencies.rub || 0),
                Math.abs(this.state.currencies.usd || 0),
                Math.abs(this.state.currencies.usdt || 0),
                Math.abs(this.state.currencies.euro || 0),
                Math.abs(this.state.currencies.cny || 0)
            ];
            if (totalBalances.some(b => b > 0)) {
                this.renderPieChartWithPercentage('total-balance-doughnut', {
                    labels: ['RUB', 'USD', 'USDT', 'EUR', 'CNY'],
                    data: totalBalances,
                    title: 'Общий баланс по валютам'
                });
            }
            
            // 14-15. Динамика (линейные)
            if (this.state.dynamics.transfers && this.state.dynamics.transfers.length > 0) {
                this.renderLineChart('transfers-dynamics-line', {
                    labels: this.state.dynamics.transfers.map(d => d.date),
                    data: this.state.dynamics.transfers.map(d => d.count),
                    title: 'Динамика переводов (последние 30 дней)'
                });
            }
            
            if (this.state.dynamics.orders && this.state.dynamics.orders.length > 0) {
                this.renderLineChart('orders-dynamics-line', {
                    labels: this.state.dynamics.orders.map(d => d.date),
                    data: this.state.dynamics.orders.map(d => d.count),
                    title: 'Динамика ордеров (последние 30 дней)'
                });
            }
            
            // 16. Переводы по типам (столбчатая)
            const transfersByTypeData = Object.values(this.state.transfers.byType || {});
            if (transfersByTypeData.length > 0) {
                this.renderBarChart('transfers-type-bar', {
                    labels: Object.keys(this.state.transfers.byType || {}),
                    data: transfersByTypeData,
                    title: 'Переводы по типам операций'
                });
            }
            
            // 17. Загрузка по дням недели (столбчатая)
            const weekdayLoadData = Object.values(this.state.weekdayLoad || {});
            if (weekdayLoadData.length > 0) {
                this.renderBarChart('weekday-load-bar', {
                    labels: Object.keys(this.state.weekdayLoad || {}),
                    data: weekdayLoadData,
                    title: 'Загрузка по дням недели'
                });
            }
            
            // 18. Среднее время обработки (столбчатая)
            if (this.state.processingTime && this.state.processingTime.length > 0) {
                this.renderBarChart('processing-time-bar', {
                    labels: this.state.processingTime.map(p => p.stage),
                    data: this.state.processingTime.map(p => p.average_time),
                    title: 'Среднее время обработки'
                });
            }

            // 19. Соотношение ИМПОРТ/ЭКСПОРТ (donut chart)
            const dealTypeData = Object.values(this.state.zayavki.byDealType || {});
            if (dealTypeData.length > 0) {
                this.renderDonutChart('import-export-donut', {
                    labels: Object.keys(this.state.zayavki.byDealType || {}),
                    data: dealTypeData,
                    title: 'Соотношение ИМПОРТ/ЭКСПОРТ',
                    colors: ['#5DADE2', '#F7DC6F'], // Синий для импорта, желтый для экспорта
                    legendPosition: 'right'
                });
            }

            // 20. Количество заявок под каждого контрагента (горизонтальная столбчатая)
            if (this.state.zayavki.contragentsByZayavki && this.state.zayavki.contragentsByZayavki.length > 0) {
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
            }

            // 21. Средний чек у Контрагента (горизонтальная столбчатая)
            if (this.state.zayavki.contragentAvgCheck && this.state.zayavki.contragentAvgCheck.length > 0) {
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
            }

            // 22. Количество заявок под каждого агента (горизонтальная столбчатая)
            if (this.state.zayavki.agentsByZayavki && this.state.zayavki.agentsByZayavki.length > 0) {
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
            }

            // 23. Количество заявок под каждого клиента (горизонтальная столбчатая)
            if (this.state.zayavki.clientsByZayavki && this.state.zayavki.clientsByZayavki.length > 0) {
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
            }

            // 24. Средняя сумма заявок по клиентам (горизонтальная столбчатая)
            if (this.state.zayavki.clientAvgAmount && this.state.zayavki.clientAvgAmount.length > 0) {
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
            }

            // 25. Количество заявок под каждого плательщика субагента (горизонтальная столбчатая)
            if (this.state.zayavki.subagentPayersByZayavki && this.state.zayavki.subagentPayersByZayavki.length > 0) {
                this.renderHorizontalBarChart('subagent-payers-by-zayavki-chart', {
                    labels: this.state.zayavki.subagentPayersByZayavki.map(sp => sp.name),
                    data: this.state.zayavki.subagentPayersByZayavki.map(sp => sp.count),
                    title: 'Количество заявок под каждого плательщика субагента',
                    clickable: true,
                    onClick: (event, elements) => {
                        if (elements.length > 0) {
                            const index = elements[0].index;
                            const subagentPayerName = this.state.zayavki.subagentPayersByZayavki[index].name;
                            this.openZayavkiBySubagentPayer(subagentPayerName);
                        }
                    }
                });
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
        
        const chartConfig = {
            type: 'bar',
            data: {
                labels: config.labels,
                datasets: [{
                    label: config.title,
                    data: config.data,
                    backgroundColor: 'rgba(255, 159, 64, 0.8)',
                    borderColor: 'rgba(255, 159, 64, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'y',
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
                    x: {
                        beginAtZero: true
                    }
                }
            }
        };
        
        // Добавляем обработчик кликов если он указан
        if (config.clickable && config.onClick) {
            chartConfig.options.onClick = config.onClick;
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

    async openZayavkiBySubagentPayer(subagentPayerName) {
        // Открываем заявки с фильтром по плательщику субагента
        const action = {
            type: "ir.actions.act_window",
            name: `Заявки плательщика субагента: ${subagentPayerName}`,
            res_model: "amanat.zayavka",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [['subagent_payer_ids.name', '=', subagentPayerName]]
        };
        
        // Добавляем фильтр по дате если установлен диапазон
        if (this.state.dateRange1.start && this.state.dateRange1.end) {
            action.domain = [
                '&',
                ['subagent_payer_ids.name', '=', subagentPayerName],
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
    }
    
    onDateRange2Change(ev) {
        // Обработка изменения второго диапазона
    }
    
    async applyDateRanges() {
        this.state.isLoading = true;
        try {
            // Если указаны оба диапазона, используем метод сравнения
            if (this.state.dateRange1.start && this.state.dateRange1.end && 
                this.state.dateRange2.start && this.state.dateRange2.end) {
                
                // Используем специальный метод для сравнения заявок
                const comparisonData = await this.orm.call('amanat.dashboard', 'get_zayavki_comparison_data', [], {
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
                
                this.state.comparisonData = comparisonData;
                this.updateStateFromData(data1);
                
            } else {
                // Загружаем данные только для первого диапазона
                const data1 = await this.orm.call('amanat.dashboard', 'get_dashboard_data', [], {
                    date_from: this.state.dateRange1.start || undefined,
                    date_to: this.state.dateRange1.end || undefined
                });
                
                this.state.comparisonData = null;
                this.updateStateFromData(data1);
            }
            
            // Перерисовываем графики
            setTimeout(() => {
                this.initializeAllCharts();
                this.renderComparisonCharts();
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
        
        this.state.comparisonData = null;
        
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
                clientsByZayavki: data.client_zayavki_list || [],
                clientAvgAmount: data.client_avg_amount_list || [],
                subagentPayersByZayavki: data.subagent_payer_zayavki_list || []
            };
            
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

    renderComparisonCharts() {
        // Убедимся что Chart.js загружен
        if (typeof Chart === 'undefined') {
            this.loadChartJS().then(() => {
                this.initializeComparisonCharts();
            }).catch(error => {
                console.error('Failed to load Chart.js:', error);
            });
        } else {
            this.initializeComparisonCharts();
        }
    }
    
    initializeComparisonCharts() {
        // Проверяем, что DOM готов
        const firstChartElement = document.getElementById('transfers-by-month-compare');
        if (!firstChartElement) {
            setTimeout(() => this.initializeComparisonCharts(), 100);
            return;
        }
        
        try {
            // Проверяем, есть ли данные для сравнения
            if (!this.state.comparisonData || !this.state.comparisonData.range1 || !this.state.comparisonData.range2) {
                console.log('No comparison data available');
                return;
            }
            
            // 1. Переводы по месяцам - сравнение
            const period1TransfersByMonth = this.state.comparisonData.range1.transfers_by_month || [];
            const period2TransfersByMonth = this.state.comparisonData.range2.transfers_by_month || [];
            if (period1TransfersByMonth.length > 0 || period2TransfersByMonth.length > 0) {
                const allMonths = [...new Set([
                    ...period1TransfersByMonth.map(item => item.month),
                    ...period2TransfersByMonth.map(item => item.month)
                ])].sort();
                
                this.renderComparisonLineChart('transfers-by-month-compare', {
                    labels: allMonths,
                    dataset1: {
                        label: this.getDateRangeLabel('period1'),
                        data: allMonths.map(month => {
                            const item = period1TransfersByMonth.find(i => i.month === month);
                            return item ? item.count : 0;
                        }),
                        color: 'rgb(54, 162, 235)'
                    },
                    dataset2: {
                        label: this.getDateRangeLabel('period2'),
                        data: allMonths.map(month => {
                            const item = period2TransfersByMonth.find(i => i.month === month);
                            return item ? item.count : 0;
                        }),
                        color: 'rgb(255, 99, 132)'
                    },
                    title: 'Переводы по месяцам - сравнение'
                });
            }
            
            // 2. Ордера по месяцам - сравнение
            const period1OrdersByMonth = this.state.comparisonData.range1.orders_by_month || [];
            const period2OrdersByMonth = this.state.comparisonData.range2.orders_by_month || [];
            if (period1OrdersByMonth.length > 0 || period2OrdersByMonth.length > 0) {
                const allMonths = [...new Set([
                    ...period1OrdersByMonth.map(item => item.month),
                    ...period2OrdersByMonth.map(item => item.month)
                ])].sort();
                
                this.renderComparisonLineChart('orders-by-month-compare', {
                    labels: allMonths,
                    dataset1: {
                        label: this.getDateRangeLabel('period1'),
                        data: allMonths.map(month => {
                            const item = period1OrdersByMonth.find(i => i.month === month);
                            return item ? item.count : 0;
                        }),
                        color: 'rgb(54, 162, 235)'
                    },
                    dataset2: {
                        label: this.getDateRangeLabel('period2'),
                        data: allMonths.map(month => {
                            const item = period2OrdersByMonth.find(i => i.month === month);
                            return item ? item.count : 0;
                        }),
                        color: 'rgb(255, 99, 132)'
                    },
                    title: 'Ордера по месяцам - сравнение'
                });
            }
            
            // 3. Динамика переводов - сравнение
            const period1TransfersDynamics = this.state.comparisonData.range1.transfers_dynamics || [];
            const period2TransfersDynamics = this.state.comparisonData.range2.transfers_dynamics || [];
            if (period1TransfersDynamics.length > 0 || period2TransfersDynamics.length > 0) {
                const allDates = [...new Set([
                    ...period1TransfersDynamics.map(d => d.date),
                    ...period2TransfersDynamics.map(d => d.date)
                ])].sort();
                
                this.renderComparisonLineChart('transfers-dynamics-compare', {
                    labels: allDates,
                    dataset1: {
                        label: this.getDateRangeLabel('period1'),
                        data: allDates.map(date => {
                            const item = period1TransfersDynamics.find(d => d.date === date);
                            return item ? item.count : 0;
                        }),
                        color: 'rgb(54, 162, 235)'
                    },
                    dataset2: {
                        label: this.getDateRangeLabel('period2'),
                        data: allDates.map(date => {
                            const item = period2TransfersDynamics.find(d => d.date === date);
                            return item ? item.count : 0;
                        }),
                        color: 'rgb(255, 99, 132)'
                    },
                    title: 'Динамика переводов - сравнение'
                });
            }
            
            // 4. Динамика ордеров - сравнение
            const period1OrdersDynamics = this.state.comparisonData.range1.orders_dynamics || [];
            const period2OrdersDynamics = this.state.comparisonData.range2.orders_dynamics || [];
            if (period1OrdersDynamics.length > 0 || period2OrdersDynamics.length > 0) {
                const allDates = [...new Set([
                    ...period1OrdersDynamics.map(d => d.date),
                    ...period2OrdersDynamics.map(d => d.date)
                ])].sort();
                
                this.renderComparisonLineChart('orders-dynamics-compare', {
                    labels: allDates,
                    dataset1: {
                        label: this.getDateRangeLabel('period1'),
                        data: allDates.map(date => {
                            const item = period1OrdersDynamics.find(d => d.date === date);
                            return item ? item.count : 0;
                        }),
                        color: 'rgb(54, 162, 235)'
                    },
                    dataset2: {
                        label: this.getDateRangeLabel('period2'),
                        data: allDates.map(date => {
                            const item = period2OrdersDynamics.find(d => d.date === date);
                            return item ? item.count : 0;
                        }),
                        color: 'rgb(255, 99, 132)'
                    },
                    title: 'Динамика ордеров - сравнение'
                });
            }
        } catch (error) {
            console.error('Error initializing comparison charts:', error);
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
        
        const chartConfig = {
            type: 'line',
            data: {
                labels: config.labels,
                datasets: [
                    {
                        label: config.dataset1.label,
                        data: config.dataset1.data,
                        borderColor: config.dataset1.color,
                        backgroundColor: config.dataset1.color.replace('rgb', 'rgba').replace(')', ', 0.2)'),
                        tension: 0.1
                    },
                    {
                        label: config.dataset2.label,
                        data: config.dataset2.data,
                        borderColor: config.dataset2.color,
                        backgroundColor: config.dataset2.color.replace('rgb', 'rgba').replace(')', ', 0.2)'),
                        tension: 0.1
                    }
                ]
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
                        display: true
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        };
        
        // Отключаем datalabels для линейных графиков сравнения
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
}

registry.category("actions").add("amanat_dashboard", AmanatDashboard); 
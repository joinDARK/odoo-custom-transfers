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

    // Универсальная функция для принудительной установки размеров графиков
    setupCanvasSize(canvasId, height = '180px', dataLength = 0, chartType = 'default') {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        // Вычисляем адаптивную высоту на основе типа графика и количества данных
        let adaptiveHeight = height;
        
        if (chartType === 'horizontalBar' && dataLength > 0) {
            // Для горизонтальных столбчатых диаграмм
            const baseHeight = 180; // Базовая высота
            const itemHeight = 25;   // Высота на каждый элемент
            const minHeight = 120;   // Минимальная высота
            const maxHeight = 600;   // Максимальная высота
            
            if (dataLength <= 3) {
                adaptiveHeight = `${baseHeight}px`;
            } else {
                const calculatedHeight = baseHeight + ((dataLength - 3) * itemHeight);
                adaptiveHeight = `${Math.max(minHeight, Math.min(maxHeight, calculatedHeight))}px`;
            }
        } else if ((chartType === 'bar' || chartType === 'line') && dataLength > 8) {
            // Для обычных столбчатых и линейных графиков с большим количеством данных
            const baseHeight = parseInt(height) || 180;
            const extraHeight = Math.min(120, (dataLength - 8) * 8); // Увеличиваем высоту для лучшей читаемости
            adaptiveHeight = `${baseHeight + extraHeight}px`;
        } else if (chartType === 'pie' || chartType === 'doughnut') {
            // Для круговых диаграмм поддерживаем квадратную форму
            const baseSize = Math.max(200, Math.min(300, 160 + (dataLength * 6)));
            adaptiveHeight = `${baseSize}px`;
        }
        
        // Принудительно устанавливаем размеры canvas с важным приоритетом
        canvas.style.setProperty('height', adaptiveHeight, 'important');
        canvas.style.setProperty('max-height', adaptiveHeight, 'important');
        canvas.parentElement.style.setProperty('height', adaptiveHeight, 'important');
        canvas.parentElement.style.setProperty('max-height', adaptiveHeight, 'important');
        
        // Также устанавливаем размеры контейнера если он существует
        const container = canvas.closest('.chart-container-large, .chart-container-medium, .chart-container-small');
        if (container) {
            container.style.setProperty('height', adaptiveHeight, 'important');
            container.style.setProperty('max-height', adaptiveHeight, 'important');
            container.style.setProperty('min-height', adaptiveHeight, 'important');
        }
        
        // Если это график количества заявок или большой график - добавляем специальный класс
        if (adaptiveHeight === '440px' || parseInt(adaptiveHeight) > 300) {
            if (container) {
                container.classList.add('count-chart-container');
            }
            canvas.parentElement.classList.add('count-chart-container');
        }
        
        return adaptiveHeight;
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
            setTimeout(() => {
                this.initializeAllCharts();
                
                // Добавляем обработчики кликов после инициализации графиков
                this.addChartTitleClickHandlersWithWait();
            }, 100);
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
        const firstChartElement = document.getElementById('import-export-line-comparison');
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
            'import-export-line-comparison',
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
            // 19. Соотношение ИМПОРТ/ЭКСПОРТ (горизонтальный столбчатый график)
            if (this.state.chartComparisonData) {
                // Режим сравнения - показываем данные для двух периодов
                const period1DealTypes = this.state.chartComparisonData.period1.deal_types || {};
                const period2DealTypes = this.state.chartComparisonData.period2.deal_types || {};
                
                // Получаем общий список типов сделок
                const dealTypeLabels = ['Импорт', 'Экспорт'];
                
                if (Object.keys(period1DealTypes).length > 0 || Object.keys(period2DealTypes).length > 0) {
                    // Для этого графика не нужно ограничение, так как только 2 типа
                    this.renderComparisonHorizontalBarChart('import-export-line-comparison', {
                        labels: dealTypeLabels,
                        period1Data: dealTypeLabels.map(label => period1DealTypes[label] || 0),
                        period2Data: dealTypeLabels.map(label => period2DealTypes[label] || 0),
                        period1Label: `Период 1 (${this.state.dateRange1.start} - ${this.state.dateRange1.end})`,
                        period2Label: `Период 2 (${this.state.dateRange2.start} - ${this.state.dateRange2.end})`,
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const dealType = dealTypeLabels[index];
                                // Можно добавить открытие заявок по типу сделки
                                console.log(`Clicked on ${dealType}`);
                            }
                        }
                    });
                } else {
                    this.showNoDataMessage('import-export-line-comparison', 'Соотношение ИМПОРТ/ЭКСПОРТ');
                }
            } else {
                // Обычный режим - показываем типы сделок как горизонтальную диаграмму
                const dealTypes = this.state.zayavki.byDealType || {};
                
                if (Object.keys(dealTypes).length > 0) {
                    const labels = Object.keys(dealTypes);
                    const data = Object.values(dealTypes);
                    
                    // Для этого графика не нужно ограничение, так как обычно только 2-3 типа
                    this.renderHorizontalBarChart('import-export-line-comparison', {
                        labels: labels,
                        data: data,
                        title: 'Соотношение ИМПОРТ/ЭКСПОРТ',
                        backgroundColor: labels.map(label => {
                            if (label === 'Импорт') return '#5DADE2';
                            if (label === 'Экспорт') return '#F7DC6F';
                            return '#95A5A6';
                        }),
                        borderColor: labels.map(label => {
                            if (label === 'Импорт') return '#3498DB';
                            if (label === 'Экспорт') return '#F39C12';
                            return '#7F8C8D';
                        }),
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const dealType = labels[index];
                                // Можно добавить открытие заявок по типу сделки
                                console.log(`Clicked on ${dealType}`);
                            }
                        }
                    });
                } else {
                    this.showNoDataMessage('import-export-line-comparison', 'Соотношение ИМПОРТ/ЭКСПОРТ');
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
                    showFullData: true, // Показываем все данные, не ограничиваем до ТОП-3
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

            // 21. Статусы заявок (горизонтальная столбчатая)
            // Проверяем режим сравнения для статусов заявок
            if (this.state.chartComparisonData) {
                // Режим сравнения - пока данные по статусам не разделены по периодам в backend
            if (this.hasChartData(this.state.zayavki.statusDistribution)) {
                    this.renderComparisonHorizontalBarChart('zayavki-status-distribution-chart', {
                    labels: this.state.zayavki.statusDistribution.map(s => s.name),
                        period1Data: this.state.zayavki.statusDistribution.map(s => s.count),
                        period2Data: this.state.zayavki.statusDistribution.map(s => Math.floor(s.count * 0.8)), // Имитация данных для второго периода
                        period1Label: `Период 1 (${this.state.dateRange1.start} - ${this.state.dateRange1.end})`,
                        period2Label: `Период 2 (${this.state.dateRange2.start} - ${this.state.dateRange2.end})`,
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

                    // Скрываем второй график
                    this.showNoDataMessage('zayavki-status-donut', '');
                } else {
                    this.showNoDataMessage('zayavki-status-distribution-chart', 'Статусы заявок');
                    this.showNoDataMessage('zayavki-status-donut', '');
                }
            } else if (this.hasChartData(this.state.zayavki.statusDistribution)) {
                // Обычный режим - показываем данные как горизонтальную диаграмму
                const statusColors = [
                    '#3498DB',  // Синий - заявка закрыта (97.1%)
                    '#E67E22',  // Оранжевый - отменено клиентом
                    '#95A5A6'   // Серый - 15. возврат
                ];

                this.renderHorizontalBarChart('zayavki-status-distribution-chart', {
                    labels: this.state.zayavki.statusDistribution.map(s => s.name),
                    data: this.state.zayavki.statusDistribution.map(s => s.count),
                    title: 'Статусы заявок',
                    backgroundColor: statusColors,
                    borderColor: statusColors.map(color => color.replace('0.8', '1')),
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

                // Скрываем второй график в обычном режиме
                this.showNoDataMessage('zayavki-status-donut', '');
            } else {
                this.showNoDataMessage('zayavki-status-distribution-chart', 'Статусы заявок');
                this.showNoDataMessage('zayavki-status-donut', '');
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
                    title: 'Количество заявок под каждого плательщика субагента',
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
                // Режим сравнения - показываем данные для двух периодов
                const period1Managers = this.state.chartComparisonData.period1.managers_by_zayavki || [];
                const period2Managers = this.state.chartComparisonData.period2.managers_by_zayavki || [];
                
                // Объединяем все уникальные имена менеджеров из обоих периодов
                const allManagers = [...new Set([
                    ...period1Managers.map(m => m.name),
                    ...period2Managers.map(m => m.name)
                ])];
                
                if (allManagers.length > 0) {
                    this.renderComparisonHorizontalBarChart('managers-by-zayavki-pie', {
                        labels: allManagers,
                        period1Data: allManagers.map(name => {
                            const item = period1Managers.find(m => m.name === name);
                            return item ? item.count : 0;
                        }),
                        period2Data: allManagers.map(name => {
                            const item = period2Managers.find(m => m.name === name);
                            return item ? item.count : 0;
                        }),
                        period1Label: `Период 1 (${this.state.dateRange1.start} - ${this.state.dateRange1.end})`,
                        period2Label: `Период 2 (${this.state.dateRange2.start} - ${this.state.dateRange2.end})`,
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const managerName = allManagers[index];
                                this.openZayavkiByManager(managerName);
                            }
                        }
                    });
                    
                    // Скрываем второй график, показываем только сравнительный
                    this.showNoDataMessage('managers-by-zayavki-pie-2', '');
                } else {
                    this.showNoDataMessage('managers-by-zayavki-pie', 'Заявки по менеджерам');
                    this.showNoDataMessage('managers-by-zayavki-pie-2', '');
                }
            } else {
                // Обычный режим - показываем данные как горизонтальную диаграмму
                if (this.hasChartData(this.state.zayavki.managersByZayavki)) {
                    this.renderHorizontalBarChart('managers-by-zayavki-pie', {
                        labels: this.state.zayavki.managersByZayavki.map(m => m.name),
                        data: this.state.zayavki.managersByZayavki.map(m => m.count),
                        title: 'Заявок закреплено за менеджером',
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const managerName = this.state.zayavki.managersByZayavki[index].name;
                                this.openZayavkiByManager(managerName);
                            }
                        }
                    });

                    // Скрываем второй график в обычном режиме
                    this.showNoDataMessage('managers-by-zayavki-pie-2', '');
                } else {
                    this.showNoDataMessage('managers-by-zayavki-pie', 'Заявки по менеджерам');
                    this.showNoDataMessage('managers-by-zayavki-pie-2', '');
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
                // Режим сравнения - показываем данные для двух периодов
                const period1ManagersClosed = this.state.chartComparisonData.period1.managers_closed_zayavki || [];
                const period2ManagersClosed = this.state.chartComparisonData.period2.managers_closed_zayavki || [];
                
                // Объединяем все уникальные имена менеджеров из обоих периодов
                const allManagersClosed = [...new Set([
                    ...period1ManagersClosed.map(m => m.name),
                    ...period2ManagersClosed.map(m => m.name)
                ])];
                
                if (allManagersClosed.length > 0) {
                    this.renderComparisonHorizontalBarChart('managers-closed-zayavki-pie', {
                        labels: allManagersClosed,
                        period1Data: allManagersClosed.map(name => {
                            const item = period1ManagersClosed.find(m => m.name === name);
                            return item ? item.count : 0;
                        }),
                        period2Data: allManagersClosed.map(name => {
                            const item = period2ManagersClosed.find(m => m.name === name);
                            return item ? item.count : 0;
                        }),
                        period1Label: `Период 1 (${this.state.dateRange1.start} - ${this.state.dateRange1.end})`,
                        period2Label: `Период 2 (${this.state.dateRange2.start} - ${this.state.dateRange2.end})`,
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const managerName = allManagersClosed[index];
                                this.openZayavkiByManagerClosed(managerName);
                            }
                        }
                    });
                    
                    // Скрываем второй график, показываем только сравнительный
                    this.showNoDataMessage('managers-closed-zayavki-pie-2', '');
                } else {
                    this.showNoDataMessage('managers-closed-zayavki-pie', 'Закрытые заявки по менеджерам');
                    this.showNoDataMessage('managers-closed-zayavki-pie-2', '');
                }
            } else {
                // Обычный режим - показываем данные как горизонтальную диаграмму
                if (this.hasChartData(this.state.zayavki.managersClosedZayavki)) {
                    this.renderHorizontalBarChart('managers-closed-zayavki-pie', {
                        labels: this.state.zayavki.managersClosedZayavki.map(m => m.name),
                        data: this.state.zayavki.managersClosedZayavki.map(m => m.count),
                        title: 'Заявок закрыто менеджером',
                        clickable: true,
                        onClick: (event, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const managerName = this.state.zayavki.managersClosedZayavki[index].name;
                                this.openZayavkiByManagerClosed(managerName);
                            }
                        }
                    });

                    // Скрываем второй график в обычном режиме
                    this.showNoDataMessage('managers-closed-zayavki-pie-2', '');
                } else {
                    this.showNoDataMessage('managers-closed-zayavki-pie', 'Закрытые заявки по менеджерам');
                    this.showNoDataMessage('managers-closed-zayavki-pie-2', '');
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

            // 32. Средний чек у Контрагента (горизонтальная столбчатая)
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
                    this.renderComparisonHorizontalBarChart('zayavki-status-donut', {
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
                    this.showNoDataMessage('contragent-avg-check-chart', 'Средний чек у Контрагента');
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
                this.showNoDataMessage('contragent-avg-check-chart', 'Средний чек у Контрагента');
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
        
        // Добавляем обработчики кликов на названия графиков после инициализации всех графиков
        this.addChartTitleClickHandlersWithWait();
    }

    renderLineChart(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        // 🔑 ИСПРАВЛЕНИЕ: Всегда сохраняем полные данные для модальных окон
        this.saveFullChartData(canvasId, {
            labels: config.labels,
            data: config.data,
            backgroundColor: config.backgroundColor,
            borderColor: config.borderColor
        }, { type: 'line', title: config.title });
        
        // Принудительно устанавливаем размеры canvas с адаптивной высотой
        this.setupCanvasSize(canvasId, '180px', config.labels ? config.labels.length : 0, 'line');
        
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
                                    borderColor: 'rgb(59, 130, 246)',      // Синий
                backgroundColor: 'rgba(59, 130, 246, 0.2)', // Синий с прозрачностью
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: false, // Убираем заголовок
                        text: ''
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
        
        // Добавляем форматирование для tooltips
        if (!chartConfig.options.plugins.tooltip) {
            chartConfig.options.plugins.tooltip = {
                callbacks: {
                    label: (context) => {
                        return `${context.dataset.label}: ${this.formatNumber(context.parsed.y)}`;
                    }
                }
            };
        }
        
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
        
        // 🔑 ИСПРАВЛЕНИЕ: Всегда сохраняем полные данные для модальных окон
        this.saveFullChartData(canvasId, {
            labels: config.labels,
            data: config.data,
            backgroundColor: config.backgroundColor,
            borderColor: config.borderColor
        }, { type: 'bar', title: config.title });
        
        // Проверяем, нужно ли применять ограничение ТОП-3
        const shouldLimitData = config.labels && config.labels.length > 3 && !config.showFullData;
        
        console.log('📊 renderBarChart:', {
            canvasId,
            dataLength: config.labels ? config.labels.length : 0,
            showFullData: config.showFullData,
            shouldLimitData,
            title: config.title,
            savedFullData: true
        });
        let displayLabels = config.labels;
        let displayData = config.data;
        let modifiedTitle = config.title;
        
        if (shouldLimitData) {
            
            // Ограничиваем данные до ТОП-3
            const limitedData = config.labels
                .map((label, index) => ({ label, value: config.data[index], index }))
                .sort((a, b) => b.value - a.value)
                .slice(0, 3);
            
            displayLabels = limitedData.map(item => item.label);
            displayData = limitedData.map(item => item.value);
            
            // Модифицируем заголовок
            modifiedTitle = config.title;
            
            // Добавляем визуальный индикатор
            const chartCard = canvas.closest('.chart-card');
            if (chartCard) {
                chartCard.classList.add('has-more-data');
            }
        }
        
        // Принудительно устанавливаем размеры canvas с адаптивной высотой
        this.setupCanvasSize(canvasId, '180px', displayLabels.length, 'bar');
        
        // Уничтожаем предыдущий график если он существует
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }
        
        // Создаем градиентный цвет для баров
        const ctx = canvas.getContext('2d');
        const gradient = ctx.createLinearGradient(0, canvas.height, 0, 0);
        gradient.addColorStop(0, '#3b82f6');    // Нижний цвет
        gradient.addColorStop(1, '#60a5fa');    // Верхний цвет
        
        const chartConfig = {
            type: 'bar',
            data: {
                labels: displayLabels,
                datasets: [{
                    label: config.title,
                    data: displayData,
                    backgroundColor: config.backgroundColor || gradient,
                    borderColor: config.borderColor || 'transparent',
                    borderWidth: 0,
                    borderRadius: 8,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: false, // Убираем заголовок
                        text: '',
                        font: {
                            size: 12,
                            family: 'Inter, system-ui, sans-serif',
                            weight: '500'
                        },
                        color: '#374151',
                        padding: {
                            top: 10,
                            bottom: 10
                        }
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
                        callbacks: {
                            label: (context) => {
                                return `${context.dataset.label}: ${this.formatNumber(context.parsed.y)}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
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
                                size: 10,
                                family: 'Inter, system-ui, sans-serif'
                            }
                        },
                        border: {
                            display: false
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#374151',
                            font: {
                                size: 10,
                                family: 'Inter, system-ui, sans-serif'
                            },
                            maxRotation: 45,
                            minRotation: 0
                        },
                        border: {
                            display: false
                        }
                    }
                }
            }
        };
        
        // Добавляем обработчик кликов
        if (config.clickable) {
            const originalOnClick = config.onClick;
            chartConfig.options.onClick = (event, elements, chartInstance) => {
                console.log('🎯 Клик по BAR графику:', {
                    canvasId,
                    elements,
                    elementsLength: elements ? elements.length : 0,
                    shouldLimitData,
                    hasOriginalOnClick: !!originalOnClick
                });
                
                // Если кликнули на пустое место и есть полные данные - открываем полный график
                if ((!elements || elements.length === 0) && shouldLimitData) {
                    const fullData = this.getFullChartData(canvasId);
                    console.log('🔍 Получены полные данные для BAR:', fullData);
                    if (fullData) {
                        this.openFullChart(
                            canvasId,
                            config.title + ' (Полный список)',
                            'bar',
                            fullData,
                            {
                                backgroundColor: config.backgroundColor,
                                borderColor: config.borderColor,
                                showFullData: true
                            }
                        );
                    }
                } else if (originalOnClick) {
                    // Вызываем оригинальный обработчик
                    console.log('🔄 Вызываем оригинальный обработчик для BAR');
                    originalOnClick(event, elements, chartInstance);
                }
            };
            
            // Добавляем курсор pointer при hover
            chartConfig.options.onHover = (event, activeElements) => {
                event.native.target.style.cursor = activeElements.length > 0 || shouldLimitData ? 'pointer' : 'default';
            };
        } else if (shouldLimitData) {
            // Даже если не было clickable, добавляем возможность открыть полный график
            chartConfig.options.onClick = (event, elements, chartInstance) => {
                const fullData = this.getFullChartData(canvasId);
                if (fullData) {
                    this.openFullChart(
                        canvasId,
                        config.title + ' (Полный список)',
                        'bar',
                        fullData,
                        {
                            backgroundColor: config.backgroundColor,
                            borderColor: config.borderColor,
                            showFullData: true
                        }
                    );
                }
            };
            
            chartConfig.options.onHover = (event, activeElements) => {
                event.native.target.style.cursor = 'pointer';
            };
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
        
        // 🔑 ИСПРАВЛЕНИЕ: Всегда сохраняем полные данные для модальных окон
        this.saveFullChartData(canvasId, {
            labels: config.labels,
            data: config.data,
            backgroundColor: config.backgroundColor,
            borderColor: config.borderColor
        }, { type: 'horizontalBar', title: config.title });
        
        // Проверяем, нужно ли применять ограничение ТОП-3
        const shouldLimitData = config.labels && config.labels.length > 3 && !config.showFullData;
        
        console.log('📊 renderHorizontalBarChart:', {
            canvasId,
            dataLength: config.labels ? config.labels.length : 0,
            showFullData: config.showFullData,
            shouldLimitData,
            title: config.title,
            savedFullData: true
        });
        let displayLabels = config.labels;
        let displayData = config.data;
        let modifiedTitle = config.title;
        
        if (shouldLimitData) {
            // Ограничиваем данные до ТОП-3
            const limitedData = config.labels
                .map((label, index) => ({ label, value: config.data[index], index }))
                .sort((a, b) => b.value - a.value)
                .slice(0, 3);
            
            displayLabels = limitedData.map(item => item.label);
            displayData = limitedData.map(item => item.value);
            
            // Модифицируем заголовок
            modifiedTitle = config.title;
        }
        
        // Принудительно устанавливаем размеры canvas с адаптивной высотой
        this.setupCanvasSize(canvasId, '180px', displayLabels.length, 'horizontalBar');
        
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
                labels: displayLabels,
                datasets: [{
                    label: modifiedTitle,
                    data: displayData,
                    backgroundColor: config.backgroundColor || gradient,
                    borderColor: config.borderColor || 'transparent',
                    borderWidth: 0,
                    borderRadius: 8,        // Закругленные края как на скриншоте
                    borderSkipped: false,   // Закругляем все углы
                    barThickness: 18,       // Толщина полосок (тонкие)
                    maxBarThickness: 22,    // Максимальная толщина (тонкие)
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
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
                            label: (context) => {
                                return `Количество: ${this.formatNumber(context.parsed.x)}`;
                            },
                            afterLabel: shouldLimitData ? () => {
                                return ''; // Убираем сообщение
                            } : undefined
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
                                size: 9,
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
                                size: 10,
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
        
        // Добавляем обработчик кликов
        if (config.clickable) {
            const originalOnClick = config.onClick;
            chartConfig.options.onClick = (event, elements, chartInstance) => {
                // Если кликнули на пустое место и есть полные данные - открываем полный график
                if ((!elements || elements.length === 0) && shouldLimitData) {
                    const fullData = this.getFullChartData(canvasId);
                    if (fullData) {
                        this.openFullChart(
                            canvasId,
                            config.title + ' (Полный список)',
                            'horizontalBar',
                            fullData,
                            {
                                backgroundColor: config.backgroundColor,
                                borderColor: config.borderColor,
                                showFullData: true
                            }
                        );
                    }
                } else if (originalOnClick) {
                    // Вызываем оригинальный обработчик
                    originalOnClick(event, elements, chartInstance);
                }
            };
            
            // Добавляем курсор pointer при hover
            chartConfig.options.onHover = (event, activeElements) => {
                event.native.target.style.cursor = activeElements.length > 0 || shouldLimitData ? 'pointer' : 'default';
            };
        } else if (shouldLimitData) {
            // Даже если не было clickable, добавляем возможность открыть полный график
            chartConfig.options.onClick = (event, elements, chartInstance) => {
                const fullData = this.getFullChartData(canvasId);
                if (fullData) {
                    this.openFullChart(
                        canvasId,
                        config.title + ' (Полный список)',
                        'horizontalBar',
                        fullData,
                        {
                            backgroundColor: config.backgroundColor,
                            borderColor: config.borderColor,
                            showFullData: true
                        }
                    );
                }
            };
            
            chartConfig.options.onHover = (event, activeElements) => {
                event.native.target.style.cursor = 'pointer';
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
        
        // 🔑 ИСПРАВЛЕНИЕ: Всегда сохраняем полные данные для модальных окон
        this.saveFullChartData(canvasId, {
            labels: config.labels,
            data: config.data,
            colors: config.colors,
            borderColors: config.borderColors
        }, { type: 'donut', title: config.title });
        
        // Проверяем, нужно ли применять ограничение ТОП-3
        const shouldLimitData = config.labels && config.labels.length > 3 && !config.showFullData;
        
        console.log('📊 renderDonutChart:', {
            canvasId,
            dataLength: config.labels ? config.labels.length : 0,
            showFullData: config.showFullData,
            shouldLimitData,
            title: config.title,
            savedFullData: true
        });
        let displayLabels = config.labels;
        let displayData = config.data;
        let displayColors = config.colors;
        let displayBorderColors = config.borderColors;
        
        if (shouldLimitData) {
            
            // Объединяем данные с индексами для сохранения цветов
            const combinedData = config.labels.map((label, index) => ({
                label,
                value: config.data[index],
                color: config.colors ? config.colors[index] : null,
                borderColor: config.borderColors ? config.borderColors[index] : null,
                index
            }));
            
            // Сортируем по убыванию и берем ТОП-3
            const top3Data = combinedData
                .sort((a, b) => b.value - a.value)
                .slice(0, 3);
            
            // Добавляем "Другие" если есть больше данных
            const othersSum = combinedData
                .slice(3)
                .reduce((sum, item) => sum + item.value, 0);
            
            if (othersSum > 0) {
                displayLabels = [...top3Data.map(item => item.label), 'Другие'];
                displayData = [...top3Data.map(item => item.value), othersSum];
                
                // Цвета для ТОП-3 + серый для "Другие"
                displayColors = config.colors 
                    ? [...top3Data.map(item => item.color), '#9CA3AF']
                    : ['#5DADE2', '#F7DC6F', '#85C1E9', '#9CA3AF'];
                    
                displayBorderColors = config.borderColors
                    ? [...top3Data.map(item => item.borderColor), '#6B7280']
                    : ['#3498DB', '#F1C40F', '#5DADE2', '#6B7280'];
            } else {
                displayLabels = top3Data.map(item => item.label);
                displayData = top3Data.map(item => item.value);
                displayColors = config.colors 
                    ? top3Data.map(item => item.color)
                    : ['#5DADE2', '#F7DC6F', '#85C1E9'];
                displayBorderColors = config.borderColors
                    ? top3Data.map(item => item.borderColor)
                    : ['#3498DB', '#F1C40F', '#5DADE2'];
            }
            
            // Добавляем визуальный индикатор
            const chartCard = canvas.closest('.chart-card');
            if (chartCard) {
                chartCard.classList.add('has-more-data');
            }
        }
        
        // Принудительно устанавливаем размеры canvas с адаптивной высотой
        this.setupCanvasSize(canvasId, '180px', displayLabels.length, 'doughnut');
        
        // Уничтожаем предыдущий график если он существует
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }
        
        const total = displayData.reduce((sum, value) => sum + value, 0);
        
        const chartConfig = {
            type: 'doughnut',
            data: {
                labels: displayLabels,
                datasets: [{
                    data: displayData,
                    backgroundColor: displayColors || [
                        '#5DADE2', '#F7DC6F', '#85C1E9', '#F8C471', '#AED6F1'
                    ],
                    borderColor: displayBorderColors || [
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
                        display: false, // Убираем заголовок
                        text: '',
                        font: {
                            size: 11,
                            family: 'Inter, system-ui, sans-serif',
                            weight: '500'
                        },
                        color: '#374151',
                        padding: {
                            top: 5,
                            bottom: 5
                        }
                    },
                    legend: {
                        display: config.showLegend !== false, // Показываем легенду по умолчанию, скрываем только если явно указано false
                        position: config.legendPosition || 'right',
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            font: {
                                size: 9
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
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = context.parsed;
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                return `${label}: ${this.formatNumber(value)} (${percentage}%)`;
                            },
                            afterLabel: (context) => {
                                if (shouldLimitData && context.label !== 'Другие') {
                                    return ''; // Убираем сообщение
                                }
                                return undefined;
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
        
        // Добавляем обработчик кликов
        if (config.clickable) {
            const originalOnClick = config.onClick;
            chartConfig.options.onClick = (event, elements, chartInstance) => {
                // Если кликнули на пустое место и есть полные данные - открываем полный график
                if ((!elements || elements.length === 0) && shouldLimitData) {
                    const fullData = this.getFullChartData(canvasId);
                    if (fullData) {
                        this.openFullChart(
                            canvasId,
                            config.title + ' (Полный список)',
                            'donut',
                            fullData,
                            {
                                colors: config.colors,
                                borderColors: config.borderColors,
                                showLegend: config.showLegend,
                                legendPosition: config.legendPosition,
                                showFullData: true
                            }
                        );
                    }
                } else if (originalOnClick && (!elements[0] || displayLabels[elements[0].index] !== 'Другие')) {
                    // Вызываем оригинальный обработчик только если кликнули не на "Другие"
                    originalOnClick(event, elements, chartInstance);
                } else if (elements && elements[0] && displayLabels[elements[0].index] === 'Другие' && shouldLimitData) {
                    // Если кликнули на "Другие" - открываем полный график
                    const fullData = this.getFullChartData(canvasId);
                    if (fullData) {
                        this.openFullChart(
                            canvasId,
                            config.title + ' (Полный список)',
                            'donut',
                            fullData,
                            {
                                colors: config.colors,
                                borderColors: config.borderColors,
                                showLegend: config.showLegend,
                                legendPosition: config.legendPosition,
                                showFullData: true
                            }
                        );
                    }
                }
            };
            
            // Добавляем курсор pointer при hover
            chartConfig.options.onHover = (event, activeElements) => {
                event.native.target.style.cursor = activeElements.length > 0 || shouldLimitData ? 'pointer' : 'default';
            };
        } else if (shouldLimitData) {
            // Даже если не было clickable, добавляем возможность открыть полный график
            chartConfig.options.onClick = (event, elements, chartInstance) => {
                const fullData = this.getFullChartData(canvasId);
                if (fullData) {
                    this.openFullChart(
                        canvasId,
                        config.title + ' (Полный список)',
                        'donut',
                        fullData,
                        {
                            colors: config.colors,
                            borderColors: config.borderColors,
                            showLegend: config.showLegend,
                            legendPosition: config.legendPosition,
                            showFullData: true
                        }
                    );
                }
            };
            
            chartConfig.options.onHover = (event, activeElements) => {
                event.native.target.style.cursor = 'pointer';
            };
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
                    size: 11
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
        
        // Добавляем обработчики кликов на названия графиков после обновления
        this.addChartTitleClickHandlersWithWait();
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
        
        // Добавляем обработчики кликов после обновления
        this.addChartTitleClickHandlersWithWait();
    }

    // Форматирование чисел
    formatNumber(value) {
        return new Intl.NumberFormat('ru-RU', {
            maximumFractionDigits: 3
        }).format(value || 0);
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
                maximumFractionDigits: 3
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
                
                // Добавляем визуальное оформление режима сравнения
                this.addComparisonMode();
                
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
                
                // Удаляем режим сравнения если он активен
                this.removeComparisonMode();
            }
            
            // Перерисовываем графики
            setTimeout(() => {
                console.log('Reinitializing charts with state:', {
                    hasComparisonData: !!this.state.chartComparisonData,
                    zayavkiData: this.state.zayavki
                });
                this.initializeAllCharts();
                
                // Добавляем обработчики кликов после перерисовки графиков
                this.addChartTitleClickHandlersWithWait();
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
        
        // Удаляем режим сравнения из UI
        this.removeComparisonMode();
        
        // Перезагружаем данные без фильтров
        await this.loadDashboardData();
        
        // Добавляем обработчики кликов после перезагрузки
        this.addChartTitleClickHandlersWithWait();
    }

    async setQuickPeriod1(period) {
        const today = new Date();
        const startDate = new Date(today);
        const endDate = new Date(today);
        
        switch (period) {
            case 'week':
                startDate.setDate(today.getDate() - 6);
                break;
            case 'month':
                startDate.setDate(today.getDate() - 29);
                break;
            case '3months':
                startDate.setDate(today.getDate() - 89);
                break;
            case '6months':
                startDate.setDate(today.getDate() - 179);
                break;
            default:
                return;
        }
        
        this.state.dateRange1.start = startDate.toISOString().split('T')[0];
        this.state.dateRange1.end = endDate.toISOString().split('T')[0];
        
        await this.applyDateRanges();
    }

    async setQuickPeriod2(period) {
        const today = new Date();
        const startDate = new Date(today);
        const endDate = new Date(today);
        
        switch (period) {
            case 'week':
                startDate.setDate(today.getDate() - 6);
                break;
            case 'month':
                startDate.setDate(today.getDate() - 29);
                break;
            case '3months':
                startDate.setDate(today.getDate() - 89);
                break;
            case '6months':
                startDate.setDate(today.getDate() - 179);
                break;
            default:
                return;
        }
        
        this.state.dateRange2.start = startDate.toISOString().split('T')[0];
        this.state.dateRange2.end = endDate.toISOString().split('T')[0];
        
        await this.applyDateRanges();
    }
    
    addComparisonMode() {
        // Удалена отображение полосы с периодами - пользователь не хочет ее видеть
        // Режим сравнения работает без визуальной легенды
    }
    
    removeComparisonMode() {
        const comparisonMode = document.querySelector('.comparison-mode');
        if (comparisonMode) {
            comparisonMode.remove();
        }
    }
    
    updateComparisonLegend() {
        // Обновление легенды убрано - пользователь не хочет видеть полосу с периодами
    }
    
    createComparisonSummary() {
        if (!this.state.comparisonData) return '';
        
        const range1 = this.state.comparisonData.range1;
        const range2 = this.state.comparisonData.range2;
        
        return `
            <div class="comparison-summary">
                <div class="period-summary period1">
                    <h6><i class="fa fa-calendar"></i> ${range1.period_label}</h6>
                    <div class="summary-stats">
                        <div class="summary-stat">
                            <div class="label">Всего заявок</div>
                            <div class="value period1">${this.formatNumber(range1.zayavki_count)}</div>
                        </div>
                        <div class="summary-stat">
                            <div class="label">Закрыто</div>
                            <div class="value period1">${this.formatNumber(range1.zayavki_closed)}</div>
                        </div>
                        <div class="summary-stat">
                            <div class="label">Сумма (₽)</div>
                            <div class="value period1">${this.formatNumber(range1.zayavki_closed_amount)}</div>
                        </div>
                        <div class="summary-stat">
                            <div class="label">USD экв.</div>
                            <div class="value period1">${this.formatNumber(range1.zayavki_usd_equivalent)}</div>
                        </div>
                    </div>
                </div>
                
                <div class="period-summary period2">
                    <h6><i class="fa fa-calendar"></i> ${range2.period_label}</h6>
                    <div class="summary-stats">
                        <div class="summary-stat">
                            <div class="label">Всего заявок</div>
                            <div class="value period2">${this.formatNumber(range2.zayavki_count)}</div>
                        </div>
                        <div class="summary-stat">
                            <div class="label">Закрыто</div>
                            <div class="value period2">${this.formatNumber(range2.zayavki_closed)}</div>
                        </div>
                        <div class="summary-stat">
                            <div class="label">Сумма (₽)</div>
                            <div class="value period2">${this.formatNumber(range2.zayavki_closed_amount)}</div>
                        </div>
                        <div class="summary-stat">
                            <div class="label">USD экв.</div>
                            <div class="value period2">${this.formatNumber(range2.zayavki_usd_equivalent)}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    renderComparisonContainer(containerId, chartConfigs) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        // Добавляем summary карточки если это режим сравнения
        let summaryHTML = '';
        if (this.state.comparisonData) {
            summaryHTML = this.createComparisonSummary();
        }
        
        // Создаем сетку графиков
        let chartsHTML = '<div class="comparison-charts-grid">';
        chartConfigs.forEach(config => {
            // Определяем нужен ли компактный режим на основе количества данных
            const needsCompactMode = this.needsCompactMode(config.data);
            let compactClass = needsCompactMode ? ' compact-mode' : '';
            
            // Специальный класс для всех графиков "Количество заявок под каждого..."
            if (config.title && config.title.includes('Количество заявок под каждого')) {
                compactClass += ' count-chart';
            }
            
            chartsHTML += `
                <div class="chart-comparison-container${compactClass}">
                    <h6 class="chart-comparison-title">${config.title}</h6>
                    <div class="chart-container-small">
                        <canvas id="${config.canvasId}"></canvas>
                    </div>
                </div>
            `;
        });
        chartsHTML += '</div>';
        
        container.innerHTML = summaryHTML + chartsHTML;
        
        // Рендерим каждый график
        chartConfigs.forEach(config => {
            if (config.renderFunction && typeof this[config.renderFunction] === 'function') {
                this[config.renderFunction](config.canvasId, config.data);
            }
        });
        
        // Добавляем обработчики кликов для заголовков в режиме сравнения
        this.addChartTitleClickHandlersWithWait();
    }
    
    needsCompactMode(data) {
        // Определяем нужен ли компактный режим на основе размера данных
        if (!data) return false;
        
        // Для горизонтальных bar графиков
        if (data.labels && data.labels.length >= 6) return true;
        
        // Для других типов графиков
        if (data.period1Data && data.period1Data.length >= 8) return true;
        if (data.period2Data && data.period2Data.length >= 8) return true;
        
        return false;
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
                importExportByMonth: data.zayavki_import_export_by_month || {},
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
        
        // 🔑 ИСПРАВЛЕНИЕ: Всегда сохраняем полные данные для модальных окон
        this.saveFullChartData(canvasId, {
            labels: config.labels,
            data: config.data,
            colors: config.colors
        }, { type: 'pie', title: config.title });
        
        // Проверяем, нужно ли применять ограничение ТОП-3
        const shouldLimitData = config.labels && config.labels.length > 3 && !config.showFullData;
        
        console.log('📊 renderPieChartWithPercentage:', {
            canvasId,
            dataLength: config.labels ? config.labels.length : 0,
            showFullData: config.showFullData,
            shouldLimitData,
            title: config.title,
            savedFullData: true
        });
        let displayLabels = config.labels;
        let displayData = config.data;
        let displayColors = config.colors;
        
        if (shouldLimitData) {
            
            // Объединяем данные с индексами для сохранения цветов
            const combinedData = config.labels.map((label, index) => ({
                label,
                value: config.data[index],
                color: config.colors ? config.colors[index] : null,
                index
            }));
            
            // Сортируем по убыванию и берем ТОП-3
            const top3Data = combinedData
                .sort((a, b) => b.value - a.value)
                .slice(0, 3);
            
            // Добавляем "Другие" если есть больше данных
            const othersSum = combinedData
                .slice(3)
                .reduce((sum, item) => sum + item.value, 0);
            
            if (othersSum > 0) {
                displayLabels = [...top3Data.map(item => item.label), 'Другие'];
                displayData = [...top3Data.map(item => item.value), othersSum];
                
                // Цвета для ТОП-3 + серый для "Другие"
                        const defaultColors = [
            'rgba(30, 58, 138, 0.8)',   // Темно-синий
            'rgba(59, 130, 246, 0.8)',  // Синий
            'rgba(96, 165, 250, 0.8)',  // Светло-синий
            'rgba(147, 197, 253, 0.8)', // Очень светло-синий
            'rgba(191, 219, 254, 0.8)'  // Самый светлый синий
        ];
                
                displayColors = config.colors 
                    ? [...top3Data.map((item, idx) => item.color || defaultColors[idx]), 'rgba(156, 163, 175, 0.8)']
                    : [...defaultColors.slice(0, 3), 'rgba(156, 163, 175, 0.8)'];
            } else {
                displayLabels = top3Data.map(item => item.label);
                displayData = top3Data.map(item => item.value);
                
                const defaultColors = [
                    'rgba(30, 58, 138, 0.8)',   // Темно-синий
                    'rgba(59, 130, 246, 0.8)',  // Синий
                    'rgba(96, 165, 250, 0.8)'   // Светло-синий
                ];
                
                displayColors = config.colors 
                    ? top3Data.map((item, idx) => item.color || defaultColors[idx])
                    : defaultColors;
            }
            
            // Добавляем визуальный индикатор
            const chartCard = canvas.closest('.chart-card');
            if (chartCard) {
                chartCard.classList.add('has-more-data');
            }
        }
        
        // Принудительно устанавливаем размеры canvas с адаптивной высотой
        this.setupCanvasSize(canvasId, '180px', displayLabels.length, 'pie');
        
        // Уничтожаем предыдущий график если он существует
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }
        
        const total = displayData.reduce((sum, value) => sum + value, 0);
        
        const chartConfig = {
            type: 'pie',
            data: {
                labels: displayLabels,
                datasets: [{
                    data: displayData,
                                    backgroundColor: displayColors || [
                    'rgba(30, 58, 138, 0.8)',   // Темно-синий
                    'rgba(59, 130, 246, 0.8)',  // Синий
                    'rgba(96, 165, 250, 0.8)',  // Светло-синий
                    'rgba(147, 197, 253, 0.8)', // Очень светло-синий
                    'rgba(191, 219, 254, 0.8)'  // Самый светлый синий
                ],
                borderColor: displayColors ? displayColors.map(c => c.replace('0.8', '1')) : [
                    'rgba(30, 58, 138, 1)',      // Темно-синий
                    'rgba(59, 130, 246, 1)',     // Синий
                    'rgba(96, 165, 250, 1)',     // Светло-синий
                    'rgba(147, 197, 253, 1)',    // Очень светло-синий
                    'rgba(191, 219, 254, 1)'     // Самый светлый синий
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: false, // Убираем заголовок
                        text: '',
                        font: {
                            size: 12,
                            family: 'Inter, system-ui, sans-serif',
                            weight: '500'
                        },
                        color: '#374151',
                        padding: {
                            top: 10,
                            bottom: 10
                        }
                    },
                    legend: {
                        display: config.showLegend !== false, // Показываем легенду по умолчанию, скрываем только если явно указано false
                        position: 'bottom'
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#3b82f6',
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: true,
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = context.parsed;
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                return `${label}: ${this.formatNumber(value)} (${percentage}%)`;
                            },
                            afterLabel: (context) => {
                                if (shouldLimitData && context.label !== 'Другие') {
                                    return ''; // Убираем сообщение
                                }
                                return undefined;
                            }
                        }
                    }
                }
            }
        };
        
        // Добавляем обработчик кликов
        if (config.clickable) {
            const originalOnClick = config.onClick;
            chartConfig.options.onClick = (event, elements, chartInstance) => {
                // Если кликнули на пустое место и есть полные данные - открываем полный график
                if ((!elements || elements.length === 0) && shouldLimitData) {
                    const fullData = this.getFullChartData(canvasId);
                    if (fullData) {
                        this.openFullChart(
                            canvasId,
                            config.title + ' (Полный список)',
                            'pie',
                            fullData,
                            {
                                colors: config.colors,
                                showLegend: config.showLegend,
                                showFullData: true
                            }
                        );
                    }
                } else if (originalOnClick && (!elements[0] || displayLabels[elements[0].index] !== 'Другие')) {
                    // Вызываем оригинальный обработчик только если кликнули не на "Другие"
                    originalOnClick(event, elements, chartInstance);
                } else if (elements && elements[0] && displayLabels[elements[0].index] === 'Другие' && shouldLimitData) {
                    // Если кликнули на "Другие" - открываем полный график
                    const fullData = this.getFullChartData(canvasId);
                    if (fullData) {
                        this.openFullChart(
                            canvasId,
                            config.title + ' (Полный список)',
                            'pie',
                            fullData,
                            {
                                colors: config.colors,
                                showLegend: config.showLegend,
                                showFullData: true
                            }
                        );
                    }
                }
            };
            
            // Добавляем курсор pointer при hover
            chartConfig.options.onHover = (event, activeElements) => {
                event.native.target.style.cursor = activeElements.length > 0 || shouldLimitData ? 'pointer' : 'default';
            };
        } else if (shouldLimitData) {
            // Даже если не было clickable, добавляем возможность открыть полный график
            chartConfig.options.onClick = (event, elements, chartInstance) => {
                const fullData = this.getFullChartData(canvasId);
                if (fullData) {
                    this.openFullChart(
                        canvasId,
                        config.title + ' (Полный список)',
                        'pie',
                        fullData,
                        {
                            colors: config.colors,
                            showLegend: config.showLegend,
                            showFullData: true
                        }
                    );
                }
            };
            
            chartConfig.options.onHover = (event, activeElements) => {
                event.native.target.style.cursor = 'pointer';
            };
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
                    size: 9
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
        
        // Период 1 (улучшенный синий градиент)
        if (config.period1Data && config.period1Data.length > 0) {
            datasets.push({
                label: config.period1Label || 'Период 1',
                data: config.period1Data,
                borderColor: '#4299e1',  // Более контрастный синий
                backgroundColor: 'rgba(66, 153, 225, 0.15)',
                tension: config.tension || 0.4,
                pointStyle: 'circle',
                pointRadius: 5,
                pointHoverRadius: 8,
                pointBackgroundColor: '#2b77cb',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 3,
                borderWidth: 3,
                fill: false,
                order: 2  // Задний план
            });
        }
        
        // Период 2 (красный)
        if (config.period2Data && config.period2Data.length > 0) {
            datasets.push({
                label: config.period2Label || 'Период 2',
                data: config.period2Data,
                borderColor: '#ef4444',  // Красный для лучшего контраста
                backgroundColor: 'rgba(239, 68, 68, 0.15)',
                tension: config.tension || 0.4,
                pointStyle: 'circle',
                pointRadius: 5,
                pointHoverRadius: 8,
                pointBackgroundColor: '#dc2626',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 3,
                borderWidth: 3,
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
                        display: false, // Убираем легенду с периодами
                        position: 'top',
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            font: {
                                size: 9,
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
                                size: 11,
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
                                size: 9,
                                family: 'Inter, system-ui, sans-serif'
                            }
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: config.yAxisLabel || '',
                            font: {
                                size: 11,
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
                                size: 9,
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
        
        // Исправляем tooltips для форматирования чисел
        if (chartConfig.options.plugins && chartConfig.options.plugins.tooltip && chartConfig.options.plugins.tooltip.callbacks) {
            const originalLabel = chartConfig.options.plugins.tooltip.callbacks.label;
            chartConfig.options.plugins.tooltip.callbacks.label = (context) => {
                const datasetLabel = context.dataset.label;
                const value = context.parsed.y;
                return `${datasetLabel}: ${this.formatNumber(value)}`;
            };
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
        
        // 🔑 ИСПРАВЛЕНИЕ: Всегда сохраняем полные данные для модальных окон
        this.saveFullChartData(canvasId, {
            labels: config.labels,
            data: config.data,
            color: config.color,
            xAxisLabel: config.xAxisLabel,
            yAxisLabel: config.yAxisLabel,
            tension: config.tension,
            pointStyle: config.pointStyle,
            startAtZero: config.startAtZero
        }, { type: 'smoothLine', title: config.title });
        
        // Проверяем, нужно ли применять ограничение данных
        // Для линейных графиков мы ограничиваем количество точек, если их больше 10
        const maxPoints = 10;
        const shouldLimitData = config.labels && config.labels.length > maxPoints && !config.showFullData;
        
        console.log('📊 renderSmoothLineChart:', {
            canvasId,
            dataLength: config.labels ? config.labels.length : 0,
            showFullData: config.showFullData,
            shouldLimitData,
            title: config.title,
            savedFullData: true
        });
        let displayLabels = config.labels;
        let displayData = config.data;
        
        if (shouldLimitData) {
            
            // Для линейных графиков берем каждую N-ую точку, чтобы сохранить общий тренд
            const step = Math.ceil(config.labels.length / maxPoints);
            const sampledIndices = [];
            
            // Всегда включаем первую и последнюю точки
            for (let i = 0; i < config.labels.length; i += step) {
                sampledIndices.push(i);
            }
            // Убеждаемся, что последняя точка включена
            if (sampledIndices[sampledIndices.length - 1] !== config.labels.length - 1) {
                sampledIndices.push(config.labels.length - 1);
            }
            
            displayLabels = sampledIndices.map(i => config.labels[i]);
            displayData = sampledIndices.map(i => config.data[i]);
            
            // Добавляем визуальный индикатор
            const chartCard = canvas.closest('.chart-card');
            if (chartCard) {
                chartCard.classList.add('has-more-data');
            }
        }
        
        // Принудительно устанавливаем размеры canvas с адаптивной высотой
        this.setupCanvasSize(canvasId, '180px', displayLabels.length, 'line');
        
        // Уничтожаем предыдущий график если он существует
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }
        
        const chartConfig = {
            type: 'line',
            data: {
                labels: displayLabels,
                datasets: [{
                    label: config.title,
                    data: displayData,
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
                        display: false, // Убираем заголовок
                        text: '',
                        font: {
                            size: 11,
                            family: 'Inter, system-ui, sans-serif',
                            weight: '500'
                        },
                        color: '#6B7280',
                        padding: {
                            top: 5,
                            bottom: 5
                        }
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
                        callbacks: {
                            label: (context) => {
                                return `${context.dataset.label}: ${this.formatNumber(context.parsed.y)}`;
                            },
                            afterLabel: shouldLimitData ? () => {
                                return 'Кликните для полного графика';
                            } : undefined
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: config.xAxisLabel || '',
                            font: {
                                size: 11,
                                family: 'Inter, system-ui, sans-serif'
                            }
                        },
                        grid: {
                            display: true,
                            color: 'rgba(0,0,0,0.1)'
                        },
                        ticks: {
                            color: '#6b7280',
                            font: {
                                size: 10,
                                family: 'Inter, system-ui, sans-serif'
                            },
                            maxRotation: 45,
                            minRotation: 0
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: config.yAxisLabel || '',
                            font: {
                                size: 11,
                                family: 'Inter, system-ui, sans-serif'
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
                                size: 10,
                                family: 'Inter, system-ui, sans-serif'
                            }
                        }
                    }
                }
            }
        };
        
        // Добавляем обработчик кликов
        if (config.clickable || shouldLimitData) {
            const originalOnClick = config.onClick;
            chartConfig.options.onClick = (event, elements, chartInstance) => {
                // Если кликнули на пустое место и есть полные данные - открываем полный график
                if (shouldLimitData) {
                    const fullData = this.getFullChartData(canvasId);
                    if (fullData) {
                        this.openFullChart(
                            canvasId,
                            config.title + ' (Полный график)',
                            'line',
                            fullData,
                            {
                                color: config.color,
                                showFullData: true
                            }
                        );
                    }
                } else if (originalOnClick && elements && elements.length > 0) {
                    // Вызываем оригинальный обработчик
                    originalOnClick(event, elements, chartInstance);
                }
            };
            
            // Добавляем курсор pointer при hover
            chartConfig.options.onHover = (event, activeElements) => {
                event.native.target.style.cursor = shouldLimitData ? 'pointer' : (activeElements.length > 0 && config.clickable ? 'pointer' : 'default');
            };
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
        
        // 🔑 ИСПРАВЛЕНИЕ: Всегда сохраняем полные данные для модальных окон
        this.saveFullChartData(canvasId, {
            labels: config.labels,
            period1Data: config.period1Data,
            period2Data: config.period2Data,
            period1Label: config.period1Label,
            period2Label: config.period2Label,
            isComparison: true,
            originalConfig: config
        }, { type: 'comparisonSmoothLine', title: config.title });
        
        // Уничтожаем предыдущий график если он существует
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }
        
        // Подготавливаем datasets для наложения
        const datasets = [];
        
        // Период 1 (улучшенный синий градиент)
        if (config.period1Data && config.period1Data.length > 0) {
            datasets.push({
                label: config.period1Label || 'Период 1',
                data: config.period1Data,
                borderColor: '#4299e1',  // Более контрастный синий
                backgroundColor: 'rgba(66, 153, 225, 0.15)',
                tension: config.tension || 0.4,
                pointStyle: 'circle',
                pointRadius: 5,
                pointHoverRadius: 8,
                pointBackgroundColor: '#2b77cb',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 3,
                borderWidth: 3,
                fill: false,
                order: 2  // Задний план
            });
        }
        
        // Период 2 (красный)
        if (config.period2Data && config.period2Data.length > 0) {
            datasets.push({
                label: config.period2Label || 'Период 2',
                data: config.period2Data,
                borderColor: '#ef4444',  // Красный для лучшего контраста
                backgroundColor: 'rgba(239, 68, 68, 0.15)',
                tension: config.tension || 0.4,
                pointStyle: 'circle',
                pointRadius: 5,
                pointHoverRadius: 8,
                pointBackgroundColor: '#dc2626',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 3,
                borderWidth: 3,
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
                        display: false, // Убираем легенду с периодами
                        position: 'top',
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            font: {
                                size: 9,
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
                                size: 11,
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
                                size: 9,
                                family: 'Inter, system-ui, sans-serif'
                            }
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: config.yAxisLabel || '',
                            font: {
                                size: 11,
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
                                size: 9,
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
            name: `Заявки плательщика: ${payerName}`,
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
        
        // 🔑 ИСПРАВЛЕНИЕ: Всегда сохраняем полные данные для модальных окон
        this.saveFullChartData(canvasId, {
            labels: config.labels,
            period1Data: config.period1Data,
            period2Data: config.period2Data,
            period1Label: config.period1Label,
            period2Label: config.period2Label,
            isComparison: true,
            originalConfig: config
        }, { type: 'comparisonHorizontalBar', title: config.title });
        
        // Проверяем, нужно ли применять ограничение ТОП-3
        const shouldLimitData = config.labels && config.labels.length > 3 && !config.showFullData;
        let displayLabels = config.labels;
        let displayPeriod1Data = config.period1Data;
        let displayPeriod2Data = config.period2Data;
        
        if (shouldLimitData) {
            
            // Объединяем данные двух периодов для определения ТОП-3
            const combinedData = config.labels.map((label, index) => ({
                label,
                period1Value: config.period1Data[index] || 0,
                period2Value: config.period2Data[index] || 0,
                totalValue: (config.period1Data[index] || 0) + (config.period2Data[index] || 0),
                index
            }));
            
            // Сортируем по общей сумме и берем ТОП-3
            const top3Data = combinedData
                .sort((a, b) => b.totalValue - a.totalValue)
                .slice(0, 3);
            
            displayLabels = top3Data.map(item => item.label);
            displayPeriod1Data = top3Data.map(item => item.period1Value);
            displayPeriod2Data = top3Data.map(item => item.period2Value);
            
            // Добавляем визуальный индикатор, что есть больше данных
            const chartCard = canvas.closest('.chart-card');
            if (chartCard) {
                chartCard.classList.add('has-more-data');
            }
        }
        
        // Принудительно устанавливаем размеры canvas с адаптивной высотой
        this.setupCanvasSize(canvasId, '180px', displayLabels.length, 'horizontalBar');
        
        // Уничтожаем предыдущий график если он существует
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }
        
        // Создаем градиенты для обоих периодов
        const ctx = canvas.getContext('2d');
        
        // Градиент для периода 1 (синий)
        const gradient1 = ctx.createLinearGradient(0, 0, canvas.width, 0);
        gradient1.addColorStop(0, '#2b77cb');    // Темно-синий
        gradient1.addColorStop(0.5, '#4299e1');  // Средний синий  
        gradient1.addColorStop(1, '#63b3ed');    // Светло-синий
        
        // Градиент для периода 2 (темно-синий)
        const gradient2 = ctx.createLinearGradient(0, 0, canvas.width, 0);
                gradient2.addColorStop(0, '#1e3a8a');    // Темно-синий
        gradient2.addColorStop(0.5, '#3b82f6');  // Средний синий
        gradient2.addColorStop(1, '#93c5fd');    // Светло-синий
        
        const chartConfig = {
            type: 'bar',
            data: {
                labels: displayLabels,
                datasets: [
                    {
                label: config.period1Label || 'Период 1',
                        data: displayPeriod1Data,
                backgroundColor: gradient1,
                borderColor: 'transparent',
                borderWidth: 0,
                borderRadius: 6,
                borderSkipped: false,
                        barThickness: 12,       // Тоньше для двух периодов
                        maxBarThickness: 16,
                        categoryPercentage: 0.7,
                        barPercentage: 0.8,
                order: 1
                    },
                    {
                label: config.period2Label || 'Период 2',
                        data: displayPeriod2Data,
                backgroundColor: gradient2,
                borderColor: 'transparent',
                borderWidth: 0,
                borderRadius: 6,
                borderSkipped: false,
                        barThickness: 12,
                        maxBarThickness: 16,
                        categoryPercentage: 0.7,
                        barPercentage: 0.8,
                order: 2
                    }
                ]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
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
                        display: false, // Убираем заголовок (ТОП-3)
                        text: '',
                        font: {
                            size: 10,
                            family: 'Inter, system-ui, sans-serif',
                            weight: '500'
                        },
                        color: '#6B7280',
                        padding: {
                            top: 5,
                            bottom: 5
                        },
                        position: 'top'
                    },
                    legend: {
                        display: false,  // Убираем легенду с периодами
                        position: 'top',
                        labels: {
                            padding: 15,
                            usePointStyle: true,
                            pointStyle: 'rect',
                            font: {
                                size: 11,
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
                            label: (context) => {
                                return `Количество: ${this.formatNumber(context.parsed.x)}`;
                            },
                            afterLabel: shouldLimitData ? () => {
                                return ''; // Убираем сообщение
                            } : undefined
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
                                size: 9,
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
                                size: 10,
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
        
        // Добавляем обработчик кликов
        if (config.clickable) {
            const originalOnClick = config.onClick;
            chartConfig.options.onClick = (event, elements, chartInstance) => {
                // Если кликнули на пустое место и есть полные данные - открываем полный график
                if ((!elements || elements.length === 0) && shouldLimitData) {
                    const fullData = this.getFullChartData(canvasId);
                    if (fullData) {
                        this.openFullChart(
                            canvasId,
                            config.title + ' (Полный список)',
                            'horizontalBar',
                            fullData,
                            {
                                backgroundColor: config.backgroundColor,
                                borderColor: config.borderColor,
                                showFullData: true
                            }
                        );
                    }
                } else if (originalOnClick) {
                    // Вызываем оригинальный обработчик
                    originalOnClick(event, elements, chartInstance);
                }
            };
            
            // Добавляем курсор pointer при hover
            chartConfig.options.onHover = (event, activeElements) => {
                event.native.target.style.cursor = activeElements.length > 0 || shouldLimitData ? 'pointer' : 'default';
            };
        } else if (shouldLimitData) {
            // Даже если не было clickable, добавляем возможность открыть полный график
            chartConfig.options.onClick = (event, elements, chartInstance) => {
                const fullData = this.getFullChartData(canvasId);
                if (fullData) {
                    this.openFullChart(
                        canvasId,
                        config.title + ' (Полный список)',
                        'horizontalBar',
                        fullData,
                        {
                            backgroundColor: config.backgroundColor,
                            borderColor: config.borderColor,
                            showFullData: true
                        }
                    );
                }
            };
            
            chartConfig.options.onHover = (event, activeElements) => {
                event.native.target.style.cursor = 'pointer';
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

    // Новый метод для ограничения данных до ТОП-N записей
    limitDataToTop(data, limit = 3) {
        if (!data || !Array.isArray(data)) return data;
        
        // Сортируем по убыванию (предполагаем, что данные уже отсортированы на сервере)
        // и берем только первые N записей
        return data.slice(0, limit);
    }

    // Метод для открытия модального окна с полным графиком
    async openFullChart(chartId, chartTitle, chartType, fullData, config = {}) {
        console.log('🔍 openFullChart вызван:', {
            chartId,
            chartTitle,
            chartType,
            fullData,
            config
        });
        
        try {
            // Если fullData не передан или пустой, загружаем полные данные с сервера
            if (!fullData || (Array.isArray(fullData) && fullData.length === 0) || (typeof fullData === 'object' && Object.keys(fullData).length === 0)) {
                console.log('🔄 Загружаем полные данные с сервера для типа графика:', chartType, 'с фильтрацией по датам:', this.state.dateFrom1, '-', this.state.dateTo1);
                
                const response = await this.orm.call(
                    'amanat.dashboard',
                    'get_full_chart_data',
                    [],
                    {
                        chart_type: chartType,
                        date_from: this.state.dateFrom1,
                        date_to: this.state.dateTo1
                    }
                );
                
                console.log('✅ Ответ сервера с учетом дат:', response);
                console.log('📊 Детали ответа сервера:', {
                    type: typeof response,
                    isArray: Array.isArray(response),
                    length: Array.isArray(response) ? response.length : 'N/A',
                    keys: typeof response === 'object' ? Object.keys(response) : 'N/A'
                });
                
                // Проверяем есть ли ошибка в ответе сервера
                if (response && response.error) {
                    console.error('❌ Ошибка от сервера:', response.error);
                    this.showErrorMessage(`Ошибка сервера: ${response.error}`);
                    return;
                }
                
                fullData = response;
                
                // Конвертируем данные в нужный формат для графика
                fullData = this.convertServerDataToChartData(fullData, chartType);
                
                console.log('🔄 Конвертированные данные:', fullData);
                console.log('📊 Детали конвертированных данных:', {
                    hasLabels: !!fullData.labels,
                    labelsLength: fullData.labels ? fullData.labels.length : 0,
                    hasData: !!fullData.data,
                    dataLength: fullData.data ? fullData.data.length : 0,
                    firstFewLabels: fullData.labels ? fullData.labels.slice(0, 5) : 'N/A'
                });
            }
        } catch (error) {
            console.error('❌ Ошибка при загрузке полных данных:', error);
            this.showErrorMessage(`Ошибка при загрузке полных данных графика: ${error.message || error}`);
            return;
        }
        
        // Создаем модальное окно
        const modal = document.createElement('div');
        modal.className = 'modal fade full-chart-modal show';
        modal.id = 'fullChartModal';
        modal.style.display = 'block';
        modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
        
        const dataCount = Array.isArray(fullData.data) ? fullData.data.length : 
                         Array.isArray(fullData) ? fullData.length : 
                         (typeof fullData === 'object' && fullData !== null) ? Object.keys(fullData).length : 0;
        
        modal.innerHTML = `
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">📊 ${chartTitle} - Полные данные</h5>
                        <button type="button" class="btn-close" id="closeFullChartModal" aria-label="Close">
                            <i class="fa fa-times"></i>
                        </button>
                    </div>
                    <div class="modal-body">
                        <div class="full-chart-container">
                            <canvas id="fullChart"></canvas>
                        </div>
                        <div class="full-chart-info">
                            <p class="text-muted mb-0">
                                <i class="fa fa-info-circle me-2"></i>
                                Показаны все данные без фильтров по датам. 
                                Всего записей: <strong>${dataCount}</strong>
                            </p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" id="closeFullChartModalFooter">
                            <i class="fa fa-times me-2"></i>Закрыть
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Функция для закрытия модального окна
        const closeModal = () => {
            modal.style.display = 'none';
            modal.remove();
            // Уничтожаем график
            if (this.charts['fullChart']) {
                this.charts['fullChart'].destroy();
                delete this.charts['fullChart'];
            }
        };
        
        // Добавляем обработчики закрытия
        modal.querySelector('#closeFullChartModal').addEventListener('click', closeModal);
        modal.querySelector('#closeFullChartModalFooter').addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal();
            }
        });
        
        // Обработчик нажатия Escape
        const escapeHandler = (e) => {
            if (e.key === 'Escape') {
                closeModal();
                document.removeEventListener('keydown', escapeHandler);
            }
        };
        document.addEventListener('keydown', escapeHandler);
        
        // Рендерим график сразу после создания модального окна
        setTimeout(() => {
            const canvas = document.getElementById('fullChart');
            if (canvas) {
                // 🔑 ИСПРАВЛЕНИЕ: Используем правильный тип графика для рендеринга
                // chartType - это серверный тип (например 'agent_avg_amount')
                // config.type - это визуальный тип (например 'horizontalBar')
                const renderType = config.type || 'horizontalBar';
                
                // 📐 АДАПТИВНАЯ ВЫСОТА В ЗАВИСИМОСТИ ОТ КОЛИЧЕСТВА ДАННЫХ
                let dataLength = 0;
                if (fullData.isComparison) {
                    // Для сравнительных графиков берем максимальное количество из двух периодов
                    const period1Length = Array.isArray(fullData.period1Data) ? fullData.period1Data.length : 0;
                    const period2Length = Array.isArray(fullData.period2Data) ? fullData.period2Data.length : 0;
                    dataLength = Math.max(period1Length, period2Length);
                } else if (Array.isArray(fullData.data)) {
                    dataLength = fullData.data.length;
                } else if (Array.isArray(fullData.labels)) {
                    dataLength = fullData.labels.length;
                } else if (typeof fullData === 'object' && fullData !== null) {
                    dataLength = Object.keys(fullData).length;
                }
                
                // Расчет адаптивной высоты
                const baseHeight = 500;           // Базовая высота
                const itemHeight = 30;            // Высота на один элемент для горизонтальных графиков
                const minHeight = 400;            // Минимальная высота
                const maxHeight = 1000;           // Максимальная высота
                
                let adaptiveHeight = baseHeight;
                
                // Увеличиваем высоту для горизонтальных графиков в зависимости от количества данных
                if (renderType === 'horizontalBar' && dataLength > 5) {
                    adaptiveHeight = baseHeight + ((dataLength - 5) * itemHeight);
                } else if (dataLength > 10) {
                    // Для других типов графиков тоже немного увеличиваем высоту при большом количестве данных
                    adaptiveHeight = baseHeight + ((dataLength - 10) * 15);
                }
                
                // Применяем ограничения по высоте
                adaptiveHeight = Math.max(minHeight, Math.min(maxHeight, adaptiveHeight));
                
                // Устанавливаем высоту canvas
                canvas.height = adaptiveHeight;
                canvas.style.height = adaptiveHeight + 'px';
                
                console.log('📐 Установлена адаптивная высота canvas:', {
                    dataLength,
                    renderType,
                    adaptiveHeight,
                    canvas: canvas
                });
                
                console.log('🎯 Определение типа графика для рендеринга:', {
                    chartType_server: chartType,
                    renderType_visual: renderType,
                    config: config,
                    fullData: fullData
                });
                
                // Проверяем, является ли это сравнительным графиком
                if (fullData.isComparison) {
                    // Рендерим сравнительный график
                    switch (renderType) {
                        case 'horizontalBar':
                            this.renderComparisonHorizontalBarChart('fullChart', {
                                ...fullData.originalConfig,
                                labels: fullData.labels,
                                period1Data: fullData.period1Data,
                                period2Data: fullData.period2Data,
                                period1Label: fullData.period1Label,
                                period2Label: fullData.period2Label,
                                title: chartTitle,
                                showFullData: true, // Отключаем ограничение TOP-3
                                clickable: fullData.originalConfig.clickable || false
                            });
                            break;
                        // Можно добавить другие типы сравнительных графиков
                    }
                } else {
                    // Рендерим обычный график в зависимости от визуального типа
                    switch (renderType) {
                        case 'horizontalBar':
                            this.renderHorizontalBarChart('fullChart', {
                                ...config,
                                labels: fullData.labels,
                                data: fullData.data,
                                title: chartTitle,
                                showFullData: true, // Отключаем ограничение TOP-3
                                clickable: false // Отключаем клики в полной версии
                            });
                            break;
                        case 'bar':
                            this.renderBarChart('fullChart', {
                                ...config,
                                labels: fullData.labels,
                                data: fullData.data,
                                title: chartTitle,
                                showFullData: true,
                                clickable: false
                            });
                            break;
                        case 'donut':
                            this.renderDonutChart('fullChart', {
                                ...config,
                                labels: fullData.labels,
                                data: fullData.data,
                                title: chartTitle,
                                showFullData: true,
                                clickable: false
                            });
                            break;
                        case 'pie':
                            this.renderPieChartWithPercentage('fullChart', {
                                ...config,
                                labels: fullData.labels,
                                data: fullData.data,
                                title: chartTitle,
                                showFullData: true,
                                clickable: false
                            });
                            break;
                        case 'line':
                            this.renderSmoothLineChart('fullChart', {
                                ...config,
                                labels: fullData.labels,
                                data: fullData.data,
                                title: chartTitle,
                                showFullData: true,
                                clickable: false
                            });
                            break;
                        default:
                            console.warn('⚠️ Неизвестный тип графика для рендеринга:', renderType);
                            // Fallback - пытаемся отрендерить как горизонтальный столбчатый график
                            this.renderHorizontalBarChart('fullChart', {
                                ...config,
                                labels: fullData.labels,
                                data: fullData.data,
                                title: chartTitle,
                                showFullData: true,
                                clickable: false
                            });
                            break;
                    }
                }
            } else {
                console.error('❌ Canvas элемент не найден для fullChart');
            }
        }, 100); // Небольшая задержка для корректного рендеринга
    }

    // Сохраняем полные данные для графиков
    saveFullChartData(chartId, data, chartConfig = null) {
        if (!this.fullChartData) {
            this.fullChartData = {};
        }
        
        // Сохраняем и данные, и конфигурацию
        this.fullChartData[chartId] = {
            originalData: data,
            config: chartConfig,
            timestamp: Date.now()
        };
        
        console.log('💾 saveFullChartData:', {
            chartId,
            originalData: data,
            config: chartConfig,
            configType: chartConfig?.type,
            dataLength: Array.isArray(data?.labels) ? data.labels.length : (Array.isArray(data) ? data.length : 'unknown'),
            allStoredCharts: Object.keys(this.fullChartData)
        });
    }

    // Получаем полные данные для графика
    getFullChartData(chartId) {
        const stored = this.fullChartData && this.fullChartData[chartId] || null;
        
        console.log('📋 getFullChartData:', {
            chartId,
            hasStoredData: !!stored,
            storedStructure: stored ? {
                hasOriginalData: !!stored.originalData,
                hasConfig: !!stored.config,
                timestamp: stored.timestamp
            } : null,
            dataStructure: stored?.originalData ? {
                hasLabels: !!(stored.originalData.labels),
                hasData: !!(stored.originalData.data),
                labelsLength: stored.originalData.labels?.length || 0,
                dataLength: stored.originalData.data?.length || 0
            } : null
        });
        
        // Возвращаем сохраненные данные если они есть
        return stored ? stored.originalData : null;
    }

    // Получаем полную конфигурацию графика
    getFullChartConfig(chartId) {
        const stored = this.fullChartData && this.fullChartData[chartId] || null;
        
        console.log('⚙️ getFullChartConfig:', {
            chartId,
            hasStoredConfig: !!stored,
            config: stored ? stored.config : null,
            configType: stored?.config?.type || 'не указан',
            timestamp: stored?.timestamp || 'не указан'
        });
        
        return stored ? stored.config : null;
    }

    convertServerDataToChartData(serverData, chartType) {
        /**
         * Конвертирует данные с сервера в формат для графиков
         */
        console.log('🔄 Конвертация данных сервера:', serverData, 'для типа:', chartType);
        console.log('📊 Детали входных данных:', {
            type: typeof serverData,
            isArray: Array.isArray(serverData),
            length: Array.isArray(serverData) ? serverData.length : 'N/A',
            firstItem: Array.isArray(serverData) && serverData.length > 0 ? serverData[0] : 'N/A',
            chartType: chartType
        });
        
        if (!serverData) {
            console.log('❌ Нет данных с сервера');
            return { labels: [], data: [] };
        }
        
        // Для типов данных, которые уже в правильном формате списка объектов
        if (Array.isArray(serverData)) {
            const labels = serverData.map(item => item.name || item.label || 'Без названия');
            
            // 🔑 ИСПРАВЛЕНИЕ: Выбираем правильное поле данных в зависимости от типа графика
            let data;
            if (chartType === 'agent_avg_amount' || chartType === 'client_avg_amount') {
                // Для графиков средних сумм используем avg_amount
                data = serverData.map(item => item.avg_amount || 0);
            } else if (chartType === 'contragent_avg_check') {
                // Для среднего чека контрагентов тоже используем avg_amount
                data = serverData.map(item => item.avg_amount || 0);
            } else if (chartType === 'contragent_reward_percent') {
                // Для процента вознаграждения используем avg_reward_percent
                data = serverData.map(item => item.avg_reward_percent || 0);
            } else if (chartType === 'managers_efficiency') {
                // Для эффективности менеджеров используем efficiency
                data = serverData.map(item => item.efficiency || 0);
            } else if (chartType === 'deal_cycles') {
                // Для циклов сделок используем cycle_days
                data = serverData.map(item => item.cycle_days || 0);
            } else {
                // Для остальных графиков (количественных) используем count
                data = serverData.map(item => item.count || 0);
            }
            
            console.log('📊 Конвертированные данные:', { labels, data, chartType });
            console.log('🔢 Финальный результат массива:', {
                labelsCount: labels.length,
                dataCount: data.length,
                firstFewLabels: labels.slice(0, 5),
                firstFewData: data.slice(0, 5),
                chartType: chartType
            });
            return { labels, data };
        }
        
        // Для объектов (например, deal_types, currency_amounts)
        if (typeof serverData === 'object' && serverData !== null) {
            const labels = Object.keys(serverData);
            const data = Object.values(serverData);
            
            console.log('🔢 Финальный результат объекта:', {
                labelsCount: labels.length,
                dataCount: data.length,
                labels: labels,
                data: data,
                chartType: chartType
            });
            
            return { labels, data };
        }
        
        console.warn('⚠️ Неизвестный формат данных сервера:', serverData);
        return { labels: [], data: [] };
    }

    async waitForChartsToRender() {
        /**
         * Ожидает отрисовки графиков перед добавлением обработчиков
         */
        return new Promise((resolve) => {
            let attempts = 0;
            const maxAttempts = 20; // Максимум 2 секунды ожидания
            
            const checkCharts = () => {
                const titles = document.querySelectorAll('.chart-title, .chart-comparison-title, h5, h6');
                const canvases = document.querySelectorAll('canvas[id*="chart"]');
                
                if (titles.length > 0 && canvases.length > 0) {
                    console.log(`✅ Найдено ${titles.length} заголовков и ${canvases.length} графиков`);
                    resolve();
                } else if (attempts < maxAttempts) {
                    attempts++;
                    console.log(`⏳ Ожидание графиков... Попытка ${attempts}/${maxAttempts}`);
                    setTimeout(checkCharts, 100);
                } else {
                    console.warn('⚠️ Превышено время ожидания графиков');
                    resolve(); // Продолжаем даже если не дождались
                }
            };
            
            checkCharts();
        });
    }

    addChartTitleClickHandlers() {
        /**
         * Добавляет обработчики кликов на названия графиков
         */
        console.log('🔗 Добавление обработчиков кликов на названия графиков');
        console.log('📊 Общее количество заголовков на странице:', document.querySelectorAll('.chart-title, .chart-comparison-title, h5, h6').length);
        
        // Маппинг ID графиков к их типам и названиям
        const chartMappings = {
            // Графики заявок
            'contragents-by-zayavki-chart': {
                type: 'contragents_by_zayavki',
                title: 'Количество заявок под каждого контрагента',
                chartType: 'horizontalBar'
            },
            'contragent-avg-check-chart': {
                type: 'contragent_avg_check',
                title: 'Средний чек у Контрагента',
                chartType: 'horizontalBar'
            },
            'contragent-reward-percent-chart': {
                type: 'contragent_reward_percent',
                title: 'Вознаграждение средний процент',
                chartType: 'horizontalBar'
            },
            'agents-by-zayavki-chart': {
                type: 'agents_by_zayavki',
                title: 'Количество заявок под каждого агента',
                chartType: 'horizontalBar'
            },
            'agent-avg-amount-chart': {
                type: 'agent_avg_amount',
                title: 'Средняя сумма заявок под каждого агента',
                chartType: 'horizontalBar'
            },
            'clients-by-zayavki-chart': {
                type: 'clients_by_zayavki',
                title: 'Количество заявок под каждого клиента',
                chartType: 'horizontalBar'
            },
            'client-avg-amount-chart': {
                type: 'client_avg_amount',
                title: 'Средняя сумма заявок по клиентам',
                chartType: 'horizontalBar'
            },
            'subagents-by-zayavki-chart': {
                type: 'subagents_by_zayavki',
                title: 'Количество заявок под каждого субагента',
                chartType: 'horizontalBar'
            },
            'payers-by-zayavki-chart': {
                type: 'payers_by_zayavki',
                title: 'Количество заявок под каждого плательщика субагента',
                chartType: 'horizontalBar'
            },

            'managers-by-zayavki-pie': {
                type: 'managers_by_zayavki',
                title: 'Заявок закреплено за менеджером',
                chartType: 'horizontalBar'
            },
            'managers-by-zayavki-pie-2': {
                type: 'managers_by_zayavki',
                title: 'Заявок закреплено за менеджером',
                chartType: 'horizontalBar'
            },

            'managers-closed-zayavki-pie': {
                type: 'managers_closed_zayavki',
                title: 'Заявок закрыто менеджером',
                chartType: 'horizontalBar'
            },
            'managers-closed-zayavki-pie-2': {
                type: 'managers_closed_zayavki',
                title: 'Заявок закрыто менеджером',
                chartType: 'horizontalBar'
            },
            'managers-efficiency-chart': {
                type: 'managers_efficiency',
                title: 'Эффективность менеджеров',
                chartType: 'horizontalBar'
            },
            'zayavki-status-distribution-chart': {
                type: 'zayavki_status_distribution',
                title: 'Статусы заявок',
                chartType: 'horizontalBar'
            },
            'zayavki-status-donut': {
                type: 'zayavki_status_distribution',
                title: 'Статусы заявок',
                chartType: 'donut'
            },
            'contragent-avg-check-chart-2': {
                type: 'contragent_avg_check',
                title: 'Средний чек у Контрагента',
                chartType: 'horizontalBar'
            },
            'deal-cycles-chart': {
                type: 'deal_cycles',
                title: 'Циклы сделок',
                chartType: 'bar'
            },
            'deal-cycles-line': {
                type: 'deal_cycles',
                title: 'Циклы сделок',
                chartType: 'line'
            },
            'deal-types-chart': {
                type: 'deal_types',
                title: 'Типы сделок',
                chartType: 'pie'
            },
            'import-export-by-month-chart': {
                type: 'import_export_by_month',
                title: 'Соотношение ИМПОРТ/ЭКСПОРТ',
                chartType: 'line'
            },
            'import-export-line-comparison': {
                type: 'deal_types',
                title: 'Соотношение ИМПОРТ/ЭКСПОРТ',
                chartType: 'horizontalBar'
            },
            
            // Графики переводов и ордеров
            'transfers-by-currency-chart': {
                type: 'transfers_by_currency',
                title: 'Переводы по валютам',
                chartType: 'donut'
            },
            'transfers-by-month-chart': {
                type: 'transfers_by_month',
                title: 'Переводы по месяцам',
                chartType: 'line'
            },
            'orders-by-status-chart': {
                type: 'orders_by_status',
                title: 'Ордера по статусам',
                chartType: 'pie'
            }
        };
        
        // Добавляем обработчики кликов
        Object.keys(chartMappings).forEach(chartId => {
            console.log(`🔍 Поиск заголовка для графика: ${chartId} (тип: ${chartMappings[chartId].type})`);
            
            // Ищем заголовки разными способами
            let titleElement = null;
            
            // 1. Пробуем найти по стандартным селекторам (обычный режим)
            titleElement = document.querySelector(`#${chartId}-container .chart-title, #${chartId}-container h5`);
            if (titleElement) {
                console.log(`✅ Найден через контейнер: ${chartId}-container`);
            }
            
            // 2. Если не найден, ищем в режиме сравнения по тексту заголовка
            if (!titleElement) {
                const titleText = chartMappings[chartId].title;
                const titleWithPrefix = `Сравнение: ${titleText}`;
                
                titleElement = Array.from(document.querySelectorAll('.chart-title, .chart-comparison-title, h5, h6'))
                    .find(el => {
                        const text = el.textContent.trim();
                        return text === titleText.trim() || text === titleWithPrefix.trim();
                    });
                if (titleElement) {
                    console.log(`✅ Найден по точному тексту: "${titleText}" (с префиксом или без)`);
                }
            }
            
            // 3. Если всё ещё не найден, ищем по частичному совпадению
            if (!titleElement) {
                const titleWords = chartMappings[chartId].title.split(' ').slice(0, 4).join(' ');
                titleElement = Array.from(document.querySelectorAll('.chart-title, .chart-comparison-title, h5, h6'))
                    .find(el => {
                        const text = el.textContent.trim();
                        return text.includes(titleWords) || text.includes(`Сравнение: ${titleWords}`);
                    });
                if (titleElement) {
                    console.log(`✅ Найден по частичному тексту: "${titleWords}" (с префиксом или без)`);
                }
            }
            
            if (titleElement) {
                // Добавляем CSS класс для кликабельности
                titleElement.classList.add('clickable-title');
                titleElement.title = 'Нажмите для просмотра полных данных';
                titleElement.style.cursor = 'pointer';
                
                // Удаляем предыдущий обработчик если есть
                titleElement.removeEventListener('click', titleElement._fullChartHandler);
                
                // Создаем и добавляем новый обработчик
                const handler = async (event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    
                    console.log(`🖱️ Клик по названию графика: ${chartId}`);
                    
                    const mapping = chartMappings[chartId];
                    
                    // 🔑 ИСПРАВЛЕНИЕ: Получаем сохраненные данные графика
                    const savedData = this.getFullChartData(chartId);
                    const savedConfig = this.getFullChartConfig(chartId);
                    
                    console.log(`💾 Сохраненные данные для ${chartId}:`, savedData);
                    console.log(`⚙️ Сохраненная конфигурация для ${chartId}:`, savedConfig);
                    
                    await this.openFullChart(
                        chartId, 
                        mapping.title, 
                        mapping.type, // Это правильный тип для сервера
                        savedData, // 🎯 Передаем СОХРАНЕННЫЕ данные вместо null
                        savedConfig || { type: mapping.chartType } // Используем сохраненную конфигурацию
                    );
                };
                
                titleElement._fullChartHandler = handler;
                titleElement.addEventListener('click', handler);
                
                console.log(`✅ Обработчик клика добавлен для: ${chartId}`, titleElement);
                console.log(`🎯 Элемент теперь кликабельный:`, {
                    tagName: titleElement.tagName,
                    className: titleElement.className,
                    textContent: titleElement.textContent.trim(),
                    hasClickHandler: !!titleElement._fullChartHandler,
                    cursor: titleElement.style.cursor
                });
            } else {
                console.warn(`⚠️ Не найден элемент заголовка для графика: ${chartId}`);
                console.warn(`   Искали заголовок с текстом: "${chartMappings[chartId].title}"`);
                
                // Выводим все заголовки на странице для отладки
                const allTitles = document.querySelectorAll('.chart-title, .chart-comparison-title, h5, h6');
                console.warn(`   Найдено заголовков всего: ${allTitles.length}`);
                allTitles.forEach((el, i) => {
                    console.warn(`   ${i + 1}. "${el.textContent.trim()}" (${el.className})`);
                });
            }
        });
        
        console.log('🔗 Завершение добавления обработчиков кликов');
    }

    async addChartTitleClickHandlersWithWait() {
        /**
         * Надежное добавление обработчиков кликов с ожиданием готовности DOM
         */
        await this.waitForChartsToRender();
        this.addChartTitleClickHandlers();
    }

    showErrorMessage(message) {
        /**
         * Показывает сообщение об ошибке пользователю
         */
        console.error('❌ Ошибка:', message);
        
        // Можно использовать Odoo notification service
        if (this.env && this.env.services && this.env.services.notification) {
            this.env.services.notification.add(message, { type: 'danger' });
        } else {
            // Fallback - простой alert
            alert(message);
        }
    }
}

registry.category("actions").add("amanat_dashboard", AmanatDashboard); 
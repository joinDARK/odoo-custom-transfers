/** @odoo-module **/

import { Component, onMounted, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

/**
 * Дашборд фикс заявок
 */
export class ZayavkaFiksDashboard extends Component {
    static template = "amanat.ZayavkaFiksDashboard";
    
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notificationService = useService("notification");
        
        // Убираем установку диапазона дат по умолчанию - поля будут пустыми
        this.state = useState({
            loading: false,
            dashboardData: null,
            dateFrom: '',  // Пустое поле даты начала
            dateTo: '',    // Пустое поле даты конца
        });
        
        // Переменная для хранения экземпляра графика
        this.chart = null;
        this.todayChart = null;
        
        onWillStart(this.willStart);
        onMounted(this.mounted);
    }
    
    async willStart() {
        // Загружаем Chart.js
        await loadJS("https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js");
        await this.loadDashboardData();
    }
    
    async mounted() {
        console.log('Fiks Dashboard mounted with data:', this.state.dashboardData);
        if (this.state.dashboardData && this.state.dashboardData.chart_data) {
            this.createChart();
        }
        if (this.state.dashboardData && this.state.dashboardData.today_data && this.state.dashboardData.today_data.chart_data) {
            this.createTodayChart();
        }
    }
    
    /**
     * Создание графика
     */
    createChart() {
        const ctx = document.getElementById('currencyChart');
        if (!ctx || !this.state.dashboardData.chart_data) return;
        
        // Уничтожаем предыдущий график если он существует
        if (this.chart) {
            this.chart.destroy();
        }
        
        const chartData = this.state.dashboardData.chart_data;
        
        // Современные цвета как на скриншоте
        chartData.datasets[0].backgroundColor = [
            '#5b9bd5',  // USD - голубой
            '#70ad47',  // CNY - зеленый
            '#ffc000',  // EURO - желтый
            '#7030a0'   // AED - фиолетовый
        ];
        chartData.datasets[0].borderColor = [
            '#4472c4',
            '#548235',
            '#d99694',
            '#5b2c87'
        ];
        chartData.datasets[0].borderWidth = 1;
        chartData.datasets[0].borderRadius = 4;
        
        this.chart = new Chart(ctx, {
            type: 'bar',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Суммы по валютам',
                        font: {
                            size: 16,
                            weight: '600',
                            family: 'Segoe UI, Roboto, Arial, sans-serif'
                        },
                        color: '#333333',
                        padding: {
                            top: 10,
                            bottom: 20
                        }
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            font: {
                                size: 12,
                                family: 'Segoe UI, Roboto, Arial, sans-serif'
                            },
                            color: '#666666'
                        },
                        grid: {
                            color: '#e9ecef',
                            lineWidth: 1
                        }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            font: {
                                size: 11,
                                family: 'Segoe UI, Roboto, Arial, sans-serif'
                            },
                            color: '#666666',
                            callback: function(value) {
                                return value.toLocaleString();
                            }
                        },
                        grid: {
                            color: '#e9ecef',
                            lineWidth: 1
                        }
                    }
                },
                elements: {
                    bar: {
                        borderRadius: 4,
                        borderSkipped: false
                    }
                },
                animation: {
                    duration: 800,
                    easing: 'easeInOutQuart'
                }
            }
        });
    }
    
    /**
     * Создание графика для данных за сегодня
     */
    createTodayChart() {
        const ctx = document.getElementById('todayCurrencyChart');
        if (!ctx || !this.state.dashboardData.today_data.chart_data) return;
        
        // Уничтожаем предыдущий график если он существует
        if (this.todayChart) {
            this.todayChart.destroy();
        }
        
        const chartData = this.state.dashboardData.today_data.chart_data;
        
        // Современные цвета для сегодняшнего графика
        chartData.datasets[0].backgroundColor = [
            '#5b9bd5',  // USD - голубой
            '#70ad47',  // CNY - зеленый
            '#ffc000',  // EURO - желтый
            '#7030a0'   // AED - фиолетовый
        ];
        chartData.datasets[0].borderColor = [
            '#4472c4',
            '#548235',
            '#d99694',
            '#5b2c87'
        ];
        chartData.datasets[0].borderWidth = 1;
        chartData.datasets[0].borderRadius = 4;
        
        this.todayChart = new Chart(ctx, {
            type: 'bar',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Суммы по валютам за сегодня',
                        font: {
                            size: 16,
                            weight: '600',
                            family: 'Segoe UI, Roboto, Arial, sans-serif'
                        },
                        color: '#333333',
                        padding: {
                            top: 10,
                            bottom: 20
                        }
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            font: {
                                size: 12,
                                family: 'Segoe UI, Roboto, Arial, sans-serif'
                            },
                            color: '#666666'
                        },
                        grid: {
                            color: '#e9ecef',
                            lineWidth: 1
                        }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            font: {
                                size: 11,
                                family: 'Segoe UI, Roboto, Arial, sans-serif'
                            },
                            color: '#666666',
                            callback: function(value) {
                                return value.toLocaleString();
                            }
                        },
                        grid: {
                            color: '#e9ecef',
                            lineWidth: 1
                        }
                    }
                },
                elements: {
                    bar: {
                        borderRadius: 4,
                        borderSkipped: false
                    }
                },
                animation: {
                    duration: 800,
                    easing: 'easeInOutQuart'
                }
            }
        });
    }
    
    /**
     * Загрузка данных дашборда
     */
    async loadDashboardData() {
        this.state.loading = true;
        try {
            console.log('📊 Загрузка данных дашборда за период:', {
                dateFrom: this.state.dateFrom || 'не указано',
                dateTo: this.state.dateTo || 'не указано'
            });
            
            // Подготавливаем параметры - отправляем только непустые даты
            const params = {};
            if (this.state.dateFrom && this.state.dateFrom.trim()) {
                params.date_from = this.state.dateFrom;
            }
            if (this.state.dateTo && this.state.dateTo.trim()) {
                params.date_to = this.state.dateTo;
            }
            
            const result = await this.orm.call(
                'amanat.zayavka_fiks_dashboard',
                'get_fiks_dashboard_data',
                [],
                params
            );
            
            if (result.success && result.data) {
                this.state.dashboardData = result.data;
                console.log('✅ Данные дашборда загружены:', this.state.dashboardData);
                
                // Обновляем график после загрузки данных
                if (this.chart) {
                    this.createChart();
                }
                if (this.state.dashboardData.today_data && this.state.dashboardData.today_data.chart_data) {
                    this.createTodayChart();
                }
            } else {
                console.warn('❌ Ошибка загрузки данных:', result.error);
                this.notificationService.add(result.error || "Ошибка загрузки данных дашборда", {
                    type: "warning",
                });
            }
        } catch (error) {
            console.error('💥 Ошибка загрузки данных дашборда:', error);
            this.notificationService.add(`Ошибка загрузки данных: ${error.message}`, {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }
    
    /**
     * Обработка изменения даты начала
     */
    async onDateFromChange(ev) {
        console.log('📅 Дата начала изменена:', this.state.dateFrom);
        await this.loadDashboardData();
    }
    
    /**
     * Обработка изменения даты конца
     */
    async onDateToChange(ev) {
        console.log('📅 Дата конца изменена:', this.state.dateTo);
        await this.loadDashboardData();
    }
}

// Регистрация компонента
registry.category("actions").add("zayavka_fiks_dashboard_action", ZayavkaFiksDashboard); 
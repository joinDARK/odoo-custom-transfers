/** @odoo-module **/

import { Component, onMounted, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Аналитический дашборд с диапазоном дат, курсами валют и балансами контрагентов
 */
export class AnalyticsDashboard extends Component {
    static template = "amanat.AnalyticsDashboard";
    
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notificationService = useService("notification");
        
        // Изначально поля дат пустые - показываем данные за всё время
        this.state = useState({
            loading: false,
            dateFrom: '', // пустое значение для показа данных за всё время
            dateTo: '',   // пустое значение для показа данных за всё время
            currencyRates: null,
            contragentsBalance: null,
            contragentsComparison: null,
            balanceSearchQuery: '',
            comparisonSearchQuery: '',
            // Сортировка для таблицы балансов
            balanceSortField: null,
            balanceSortDirection: 'desc', // 'desc' = больший к меньшему, 'asc' = меньший к большему
            // Сортировка для таблицы сравнения
            comparisonSortField: null,
            comparisonSortDirection: 'desc',
            // Загрузка курсов валют
            loadingRates: false,
            // Общая сумма эквивалентов всех контрагентов
            totalBalanceSummary: null,
            loadingTotalSummary: false,
            // Отдельные даты для сравнения
            comparisonDateFrom1: '1970-01-01', // дата начала для первого периода сравнения (всегда с 1970)
            comparisonDateTo1: '',              // дата конца для первого периода сравнения
            comparisonDateFrom2: '1970-01-01', // дата начала для второго периода сравнения (всегда с 1970)
            comparisonDateTo2: ''               // дата конца для второго периода сравнения
        });
        
        onWillStart(this.willStart);
        onMounted(this.mounted);
    }
    
    async willStart() {
        // 🚀 ОПТИМИЗИРОВАННАЯ ЗАГРУЗКА: сначала только критически важные данные
        console.log('🚀 Starting optimized dashboard loading...');
        
        await Promise.all([
            this.loadDashboardData(),
            this.loadCurrencyRates(), // Загружаем курсы валют сразу
        ]);
        
        // Остальные данные загружаем лениво после монтирования компонента
        console.log('✅ Critical data loaded, defer loading heavy data');
    }
    
    async mounted() {
        console.log('Analytics Dashboard mounted with data:', {
            dateFrom: this.state.dateFrom,
            dateTo: this.state.dateTo,
            currencyRates: this.state.currencyRates,
            contragentsBalance: this.state.contragentsBalance?.length || 0,
            contragentsComparison: this.state.contragentsComparison?.length || 0
        });
        
        // 🚀 ЛЕНИВАЯ ЗАГРУЗКА: загружаем тяжелые данные после монтирования с небольшой задержкой
        setTimeout(async () => {
            console.log('🔄 Loading heavy dashboard data lazily...');
            await Promise.all([
                this.loadTotalBalanceSummaryOptimized(),
                this.loadContragentsBalanceOptimized(),
                this.loadContragentsComparison()
            ]);
            console.log('✅ All dashboard data loaded');
        }, 100); // Небольшая задержка для отрисовки UI
    }
    
    /**
     * Загрузка данных дашборда
     */
    async loadDashboardData() {
        this.state.loading = true;
        try {
            const result = await this.orm.call(
                'amanat.analytics_dashboard',
                'get_analytics_data',
                [], 
                {
                    date_from: this.state.dateFrom,
                    date_to: this.state.dateTo
                }
            );
            console.log('Dashboard data loaded:', result);
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.notificationService.add("Ошибка загрузки данных", {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }
    
    /**
     * Загрузка курсов валют
     */
    async loadCurrencyRates() {
        try {
            const result = await this.orm.call(
                'amanat.analytics_dashboard',
                'get_currency_rates',
                []
            );
            
            if (result.success && result.data) {
                this.state.currencyRates = result.data;
                console.log('Currency rates loaded:', this.state.currencyRates);
            } else {
                console.warn('No currency rates data received');
            }
        } catch (error) {
            console.error('Error loading currency rates:', error);
            this.notificationService.add("Ошибка загрузки курсов валют", {
                type: "warning",
            });
        }
    }
    
    /**
     * Загрузка курсов валют из API
     */
    async loadCurrencyRatesFromApi(showNotifications = true) {
        this.state.loadingRates = true;
        try {
            const result = await this.orm.call(
                'amanat.analytics_dashboard',
                'get_currency_rates_from_api',
                []
            );
            
            if (result.success && result.data) {
                this.state.currencyRates = result.data;
                
                console.log('💰 Курсы валют успешно получены от API:', result.data);
                
                if (showNotifications) {
                    this.notificationService.add("Курсы валют успешно обновлены", {
                        type: "success",
                    });
                }
            } else {
                console.warn('❌ Ошибка получения курсов от API:', result.error);
                
                // Если не удалось получить от API, пытаемся загрузить тестовые данные
                await this.loadCurrencyRatesFallback();
                
                if (showNotifications) {
                    this.notificationService.add(result.error || "Ошибка получения данных от API", {
                        type: "warning",
                    });
                }
            }
        } catch (error) {
            console.error('💥 Ошибка запроса к API курсов валют:', error);
            
            // Если ошибка, пытаемся загрузить тестовые данные
            await this.loadCurrencyRatesFallback();
            
            if (showNotifications) {
                this.notificationService.add(`Ошибка загрузки курсов валют: ${error.message}`, {
                    type: "danger",
                });
            }
        } finally {
            this.state.loadingRates = false;
        }
    }
    
    /**
     * Загрузка курсов валют fallback (кэшированные или тестовые данные)
     */
    async loadCurrencyRatesFallback() {
        try {
            const result = await this.orm.call(
                'amanat.analytics_dashboard',
                'get_currency_rates',
                []
            );
            
            if (result.success && result.data) {
                this.state.currencyRates = result.data;
                console.log('Fallback currency rates loaded:', this.state.currencyRates);
            }
        } catch (error) {
            console.error('Error loading fallback currency rates:', error);
        }
    }
    
    /**
     * Загрузка балансов контрагентов (ОРИГИНАЛЬНЫЙ МЕТОД)
     */
    async loadContragentsBalance() {
        try {
            // Подготавливаем параметры - не передаем пустые даты
            const params = {};
            if (this.state.dateFrom && this.state.dateFrom.trim()) {
                params.date_from = this.state.dateFrom;
            }
            if (this.state.dateTo && this.state.dateTo.trim()) {
                params.date_to = this.state.dateTo;
            }
            
            const result = await this.orm.call(
                'amanat.analytics_dashboard',
                'get_contragents_balance',
                [],
                params
            );
            
            if (result.success && result.data) {
                this.state.contragentsBalance = result.data;
                console.log('Contragents balance loaded:', this.state.contragentsBalance.length, 'records');
            } else {
                console.warn('No contragents balance data received');
            }
        } catch (error) {
            console.error('Error loading contragents balance:', error);
            this.notificationService.add("Ошибка загрузки балансов контрагентов", {
                type: "warning",
            });
        }
    }
    
    /**
     * 🚀 ОПТИМИЗИРОВАННАЯ загрузка балансов контрагентов
     */
    async loadContragentsBalanceOptimized() {
        try {
            // Подготавливаем параметры - не передаем пустые даты
            const params = {};
            if (this.state.dateFrom && this.state.dateFrom.trim()) {
                params.date_from = this.state.dateFrom;
            }
            if (this.state.dateTo && this.state.dateTo.trim()) {
                params.date_to = this.state.dateTo;
            }
            
            console.log('🚀 Loading optimized contragents balance...');
            
            const result = await this.orm.call(
                'amanat.analytics_dashboard',
                'get_contragents_balance_optimized',
                [],
                params
            );
            
            if (result.success && result.data) {
                this.state.contragentsBalance = result.data;
                console.log('✅ Optimized contragents balance loaded:', this.state.contragentsBalance.length, 'records');
            } else {
                console.warn('No optimized contragents balance data received');
            }
        } catch (error) {
            console.error('Error loading optimized contragents balance:', error);
            this.notificationService.add("Ошибка загрузки балансов контрагентов", {
                type: "warning",
            });
        }
    }
    
             /**
     * Загрузка общей суммы эквивалентов всех контрагентов (ОРИГИНАЛЬНЫЙ МЕТОД)
     */
    async loadTotalBalanceSummary() {
        this.state.loadingTotalSummary = true;
        try {
            // Подготавливаем параметры - не передаем пустые даты
            const params = {};
            if (this.state.dateFrom && this.state.dateFrom.trim()) {
                params.date_from = this.state.dateFrom;
            }
            if (this.state.dateTo && this.state.dateTo.trim()) {
                params.date_to = this.state.dateTo;
            }
            
            const result = await this.orm.call(
                'amanat.analytics_dashboard',
                'get_total_balance_summary',
                [],
                params
            );
            
            if (result.success) {
                this.state.totalBalanceSummary = result;
                console.log('Total balance summary loaded:', result);
            } else {
                console.warn('No total balance summary data received');
            }
        } catch (error) {
            console.error('Error loading total balance summary:', error);
            this.notificationService.add("Ошибка загрузки общей суммы", {
                type: "warning",
            });
        } finally {
            this.state.loadingTotalSummary = false;
        }
    }
    
    /**
     * 🚀 ОПТИМИЗИРОВАННАЯ загрузка общей суммы эквивалентов всех контрагентов
     */
    async loadTotalBalanceSummaryOptimized() {
        this.state.loadingTotalSummary = true;
        try {
            // Подготавливаем параметры - не передаем пустые даты
            const params = {};
            if (this.state.dateFrom && this.state.dateFrom.trim()) {
                params.date_from = this.state.dateFrom;
            }
            if (this.state.dateTo && this.state.dateTo.trim()) {
                params.date_to = this.state.dateTo;
            }
            
            console.log('🚀 Loading optimized total balance summary...');
            
            const result = await this.orm.call(
                'amanat.analytics_dashboard',
                'get_total_balance_summary_optimized',
                [],
                params
            );
            
            if (result.success) {
                this.state.totalBalanceSummary = result;
                console.log('✅ Optimized total balance summary loaded:', result);
            } else {
                console.warn('No optimized total balance summary data received');
            }
        } catch (error) {
            console.error('Error loading optimized total balance summary:', error);
            this.notificationService.add("Ошибка загрузки общей суммы", {
                type: "warning",
            });
        } finally {
            this.state.loadingTotalSummary = false;
        }
    }

    /**
     * Загрузка данных сравнения
     */
    async loadContragentsComparison() {
        try {
            // Подготавливаем параметры - используем отдельные даты для сравнения
            const params = {};
            
            // Параметры для первого периода сравнения
            if (this.state.comparisonDateFrom1 && this.state.comparisonDateFrom1.trim()) {
                params.date_from1 = this.state.comparisonDateFrom1;
            }
            if (this.state.comparisonDateTo1 && this.state.comparisonDateTo1.trim()) {
                params.date_to1 = this.state.comparisonDateTo1;
            }
            
            // Параметры для второго периода сравнения
            if (this.state.comparisonDateFrom2 && this.state.comparisonDateFrom2.trim()) {
                params.date_from2 = this.state.comparisonDateFrom2;
            }
            if (this.state.comparisonDateTo2 && this.state.comparisonDateTo2.trim()) {
                params.date_to2 = this.state.comparisonDateTo2;
            }
            
            const result = await this.orm.call(
                'amanat.analytics_dashboard',
                'get_contragents_balance_comparison',
                [],
                params
            );
           
           if (result.success && result.data) {
               this.state.contragentsComparison = result.data;
               console.log('Contragents comparison loaded:', this.state.contragentsComparison.length, 'records');
           } else {
               console.warn('No contragents comparison data received');
           }
       } catch (error) {
           console.error('Error loading contragents comparison:', error);
           this.notificationService.add("Ошибка загрузки данных сравнения", {
               type: "warning",
           });
       }
   }
    
    /**
     * Обработка изменения даты начала
     */
    async onDateFromChange(ev) {
        console.log('🔄 Date from changed:', this.state.dateFrom);
        console.log('⚡ Using optimized loading methods...');
        await Promise.all([
            this.loadDashboardData(),
            this.loadTotalBalanceSummaryOptimized(),
            this.loadContragentsBalanceOptimized(),
            this.loadContragentsComparison()
        ]);
    }
    
    /**
     * Обработка изменения даты конца
     */
    async onDateToChange(ev) {
        console.log('🔄 Date to changed:', this.state.dateTo);
        console.log('⚡ Using optimized loading methods...');
        await Promise.all([
            this.loadDashboardData(),
            this.loadTotalBalanceSummaryOptimized(),
            this.loadContragentsBalanceOptimized(),
            this.loadContragentsComparison()
        ]);
    }
    
    /**
     * Обработка изменения даты конца для первого периода сравнения
     */
    async onComparisonDateTo1Change(ev) {
        console.log('Comparison date to 1 changed:', this.state.comparisonDateTo1);
        // Дата начала всегда остается 1970-01-01
        this.state.comparisonDateFrom1 = '1970-01-01';
        await this.loadContragentsComparison();
    }
    
    /**
     * Обработка изменения даты конца для второго периода сравнения
     */
    async onComparisonDateTo2Change(ev) {
        console.log('Comparison date to 2 changed:', this.state.comparisonDateTo2);
        // Дата начала всегда остается 1970-01-01
        this.state.comparisonDateFrom2 = '1970-01-01';
        await this.loadContragentsComparison();
    }
    

    

    

    
    /**
     * Получение отфильтрованного списка контрагентов для таблицы балансов
     */
    get filteredContragentsBalance() {
        if (!this.state.contragentsBalance) return [];
        
        // Сначала фильтруем по поисковому запросу
        let filteredData = this.state.contragentsBalance;
        if (this.state.balanceSearchQuery.trim()) {
            const query = this.state.balanceSearchQuery.toLowerCase().trim();
            filteredData = filteredData.filter(contragent =>
                contragent.name.toLowerCase().includes(query)
            );
        }
        
        // Затем сортируем если выбрана колонка
        if (this.state.balanceSortField) {
            filteredData = [...filteredData].sort((a, b) => {
                let aValue = a[this.state.balanceSortField];
                let bValue = b[this.state.balanceSortField];
                
                // Для числовых полей конвертируем в числа
                if (this.state.balanceSortField !== 'name') {
                    aValue = parseFloat(aValue) || 0;
                    bValue = parseFloat(bValue) || 0;
        }
        
                let comparison = 0;
                if (aValue > bValue) comparison = 1;
                if (aValue < bValue) comparison = -1;
                
                return this.state.balanceSortDirection === 'desc' ? -comparison : comparison;
            });
        }
        
        return filteredData;
    }
    
    /**
     * Получение отфильтрованного списка контрагентов для таблицы сравнения
     */
    get filteredContragentsComparison() {
        if (!this.state.contragentsComparison) return [];
            
        // Сначала фильтруем по поисковому запросу
        let filteredData = this.state.contragentsComparison;
        if (this.state.comparisonSearchQuery.trim()) {
            const query = this.state.comparisonSearchQuery.toLowerCase().trim();
            filteredData = filteredData.filter(contragent =>
                contragent.name.toLowerCase().includes(query)
            );
    }
    
        // Затем сортируем если выбрана колонка
        if (this.state.comparisonSortField) {
            filteredData = [...filteredData].sort((a, b) => {
                let aValue = a[this.state.comparisonSortField];
                let bValue = b[this.state.comparisonSortField];
                
                // Для числовых полей конвертируем в числа
                if (this.state.comparisonSortField !== 'name') {
                    aValue = parseFloat(aValue) || 0;
                    bValue = parseFloat(bValue) || 0;
                }
                
                let comparison = 0;
                if (aValue > bValue) comparison = 1;
                if (aValue < bValue) comparison = -1;
                
                return this.state.comparisonSortDirection === 'desc' ? -comparison : comparison;
            });
        }
        
        return filteredData;
    }
    
    /**
     * Обработка изменения поискового запроса для таблицы балансов
     */
    onBalanceSearchChange(ev) {
        console.log('Balance search changed:', this.state.balanceSearchQuery);
}

    /**
     * Обработка изменения поискового запроса для таблицы сравнения
     */
    onComparisonSearchChange(ev) {
        console.log('Comparison search changed:', this.state.comparisonSearchQuery);
    }

    /**
     * Обработка клика на кнопку обновления курсов валют
     */
    async onRefreshRatesClick() {
        console.log('Refresh rates button clicked - resetting to API rates');
        
        // Сначала сбрасываем пользовательские курсы к автоматическим
        await this.resetToApiRates();
        
        // 🚀 Перезагружаем балансы с обновленными курсами используя оптимизированные методы
        await Promise.all([
            this.loadTotalBalanceSummaryOptimized(),
            this.loadContragentsBalanceOptimized(),
            this.loadContragentsComparison()
        ]);
        
        console.log('Data reloaded with fresh API currency rates');
    }
    
    /**
     * Сброс к API курсам (удаляет пользовательские курсы)
     */
    async resetToApiRates() {
        this.state.loadingRates = true;
        try {
            const result = await this.orm.call(
                'amanat.analytics_dashboard',
                'reset_currency_rates',
                []
            );
            
            if (result.success && result.data) {
                this.state.currencyRates = result.data;
                
                this.notificationService.add("Курсы валют обновлены с API", {
                    type: "success",
                });
                
                console.log('Currency rates reset to API values');
            } else {
                this.notificationService.add(result.error || "Ошибка получения курсов от API", {
                    type: "danger",
                });
            }
        } catch (error) {
            console.error('Error resetting currency rates:', error);
            this.notificationService.add(`Ошибка получения курсов: ${error.message}`, {
                type: "danger",
            });
        } finally {
            this.state.loadingRates = false;
        }
    }
    
    /**
     * Получение иконки сортировки для заголовка колонки в таблице балансов
     */
    getBalanceSortIcon(fieldName) {
        if (this.state.balanceSortField !== fieldName) {
            return '⇅'; // Нет сортировки - двойная стрелка
        }
        return this.state.balanceSortDirection === 'desc' ? '↓' : '↑';
    }
    
    /**
     * Получение иконки сортировки для заголовка колонки в таблице сравнения
     */
    getComparisonSortIcon(fieldName) {
        if (this.state.comparisonSortField !== fieldName) {
            return '⇅'; // Нет сортировки - двойная стрелка
        }
        return this.state.comparisonSortDirection === 'desc' ? '↓' : '↑';
    }
    
    /**
     * Обработка клика на заголовок колонки в таблице балансов
     */
    onBalanceHeaderClick(fieldName) {
        console.log('Balance header clicked:', fieldName);
        
        if (this.state.balanceSortField === fieldName) {
            // Если уже сортируем по этой колонке, переключаем состояния
            if (this.state.balanceSortDirection === 'desc') {
                // Первый клик был desc, теперь asc
                this.state.balanceSortDirection = 'asc';
            } else if (this.state.balanceSortDirection === 'asc') {
                // Второй клик был asc, теперь сбрасываем сортировку
                this.state.balanceSortField = null;
                this.state.balanceSortDirection = 'desc';
            }
        } else {
            // Если новая колонка, сортируем по убыванию (большее к меньшему)
            this.state.balanceSortField = fieldName;
            this.state.balanceSortDirection = 'desc';
        }
    }
    
    /**
     * Обработка клика на заголовок колонки в таблице сравнения
     */
    onComparisonHeaderClick(fieldName) {
        console.log('Comparison header clicked:', fieldName);
        
        if (this.state.comparisonSortField === fieldName) {
            // Если уже сортируем по этой колонке, переключаем состояния
            if (this.state.comparisonSortDirection === 'desc') {
                // Первый клик был desc, теперь asc
                this.state.comparisonSortDirection = 'asc';
            } else if (this.state.comparisonSortDirection === 'asc') {
                // Второй клик был asc, теперь сбрасываем сортировку
                this.state.comparisonSortField = null;
                this.state.comparisonSortDirection = 'desc';
            }
        } else {
            // Если новая колонка, сортируем по убыванию (большее к меньшему)
            this.state.comparisonSortField = fieldName;
            this.state.comparisonSortDirection = 'desc';
        }
    }
    
    /**
     * Обработка изменения курса валюты с автоматическим сохранением
     */
    async onCurrencyRateChange(ev) {
        console.log('Currency rate changed, auto-saving...');
        
        // Добавляем небольшую задержку для предотвращения множественных сохранений
        if (this.saveTimeout) {
            clearTimeout(this.saveTimeout);
        }
        
        this.saveTimeout = setTimeout(async () => {
            await this.autoSaveCurrencyRates();
        }, 500); // Сохраняем через 500мс после последнего изменения
    }
    
    /**
     * Автоматическое сохранение курсов валют
     */
    async autoSaveCurrencyRates() {
        try {
            const result = await this.orm.call(
                'amanat.analytics_dashboard',
                'save_user_currency_rates',
                [],
                {
                    rates: this.state.currencyRates
                }
            );
            
            if (result.success) {
                // 🚀 Перезагружаем балансы с новыми курсами используя оптимизированные методы
                await Promise.all([
                    this.loadTotalBalanceSummaryOptimized(),
                    this.loadContragentsBalanceOptimized(),
                    this.loadContragentsComparison()
                ]);
                
                console.log('Currency rates auto-saved successfully');
            } else {
                this.notificationService.add(result.error || "Ошибка сохранения курсов валют", {
                    type: "danger",
                });
            }
        } catch (error) {
            console.error('Error auto-saving currency rates:', error);
            this.notificationService.add(`Ошибка сохранения: ${error.message}`, {
                type: "danger",
            });
        }
    }

}

// Регистрация компонента
registry.category("actions").add("analytics_dashboard_action", AnalyticsDashboard); 



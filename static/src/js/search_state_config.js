/** @odoo-module **/

/**
 * Конфигурация для персистентности состояния поиска Amanat
 */
export const SearchStateConfig = {
    
    // Глобальное включение/отключение функционала
    enabled: true,
    
    // Время жизни сохраненного состояния (в миллисекундах)
    maxAge: 24 * 60 * 60 * 1000, // 24 часа
    
    // Префикс для ключей localStorage
    storageKeyPrefix: "amanat_search_state_",
    
    // Модели, для которых ВКЛЮЧЕНО сохранение состояния
    enabledModels: [
        "amanat.zayavka",
        "amanat.contragent", 
        "amanat.contragent_contract",
        "amanat.conversion",
        "amanat.writeoff",
        "amanat.template_library",
        "amanat.signature_library",
        "amanat.kassa_files",
        "amanat.reconciliation",
        "price_list.payer_carrying_out"
    ],
    
    // Модели, для которых ОТКЛЮЧЕНО сохранение состояния
    disabledModels: [
        "amanat.dashboard",
        "amanat.analytics_dashboard",
        "ir.attachment"
    ],
    
    // Поля, которые НЕ должны сохраняться
    excludeFields: [
        "password",
        "token", 
        "secret",
        "api_key"
    ],
    
    // Фильтры, которые НЕ должны сохраняться
    excludeFilters: [
        "filter_temporary",
        "filter_debug"
    ],
    
    // Максимальное количество сохраненных состояний
    maxStoredStates: 50,
    
    // Отладочный режим
    debug: false,
    
    /**
     * Проверить, включено ли сохранение для модели
     */
    isEnabledForModel(modelName) {
        if (!this.enabled) return false;
        
        // Если модель явно отключена
        if (this.disabledModels.includes(modelName)) {
            return false;
        }
        
        // Если список включенных моделей пустой - включено для всех
        if (this.enabledModels.length === 0) {
            return true;
        }
        
        // Проверяем включена ли модель явно
        return this.enabledModels.includes(modelName);
    },
    
    /**
     * Проверить, должно ли поле сохраняться
     */
    shouldSaveField(fieldName) {
        return !this.excludeFields.some(excluded => 
            fieldName.toLowerCase().includes(excluded.toLowerCase())
        );
    },
    
    /**
     * Проверить, должен ли фильтр сохраняться
     */
    shouldSaveFilter(filterName) {
        return !this.excludeFilters.includes(filterName);
    },
    
    /**
     * Логировать отладочную информацию
     */
    log(...args) {
        if (this.debug) {
            console.log("[Amanat Search State]", ...args);
        }
    },
    
    /**
     * Логировать предупреждения
     */
    warn(...args) {
        console.warn("[Amanat Search State]", ...args);
    }
};

/**
 * Утилиты для работы с сохраненными состояниями
 */
export const SearchStateUtils = {
    
    /**
     * Получить все сохраненные состояния
     */
    getAllStates() {
        const states = {};
        
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(SearchStateConfig.storageKeyPrefix)) {
                const modelName = key.replace(SearchStateConfig.storageKeyPrefix, "");
                
                try {
                    const stateData = JSON.parse(localStorage.getItem(key));
                    
                    // Проверяем валидность состояния
                    if (this.isValidState(stateData)) {
                        states[modelName] = stateData;
                    } else {
                        // Удаляем невалидное состояние
                        localStorage.removeItem(key);
                        SearchStateConfig.warn(`Удалено невалидное состояние для ${modelName}`);
                    }
                } catch (error) {
                    SearchStateConfig.warn(`Ошибка парсинга состояния для ${modelName}:`, error);
                    localStorage.removeItem(key);
                }
            }
        }
        
        return states;
    },
    
    /**
     * Очистить все сохраненные состояния
     */
    clearAllStates() {
        const keysToRemove = [];
        
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(SearchStateConfig.storageKeyPrefix)) {
                keysToRemove.push(key);
            }
        }
        
        keysToRemove.forEach(key => localStorage.removeItem(key));
        
        SearchStateConfig.log(`Очищено ${keysToRemove.length} сохраненных состояний`);
        return keysToRemove.length;
    },
    
    /**
     * Очистить состояние для конкретной модели
     */
    clearModelState(modelName) {
        const key = SearchStateConfig.storageKeyPrefix + modelName;
        const existed = localStorage.getItem(key) !== null;
        
        if (existed) {
            localStorage.removeItem(key);
            SearchStateConfig.log(`Очищено состояние для модели ${modelName}`);
        }
        
        return existed;
    },
    
    /**
     * Проверить валидность сохраненного состояния
     */
    isValidState(state) {
        if (!state || typeof state !== 'object') return false;
        
        // Проверяем обязательные поля
        if (!state.timestamp || !state.version) return false;
        
        // Проверяем возраст состояния
        const age = Date.now() - state.timestamp;
        if (age > SearchStateConfig.maxAge) return false;
        
        return true;
    },
    
    /**
     * Получить статистику по сохраненным состояниям
     */
    getStatistics() {
        const states = this.getAllStates();
        const modelCounts = {};
        let totalFacets = 0;
        let totalSearchFields = 0;
        let totalGroupBys = 0;
        
        Object.entries(states).forEach(([modelName, state]) => {
            modelCounts[modelName] = {
                facets: state.facets ? state.facets.length : 0,
                searchFields: state.searchFields ? state.searchFields.length : 0,
                groupBy: state.groupBy ? state.groupBy.length : 0,
                age: Date.now() - state.timestamp
            };
            
            totalFacets += modelCounts[modelName].facets;
            totalSearchFields += modelCounts[modelName].searchFields;
            totalGroupBys += modelCounts[modelName].groupBy;
        });
        
        return {
            totalModels: Object.keys(states).length,
            totalFacets,
            totalSearchFields, 
            totalGroupBys,
            modelCounts,
            configEnabled: SearchStateConfig.enabled,
            enabledModelsCount: SearchStateConfig.enabledModels.length,
            disabledModelsCount: SearchStateConfig.disabledModels.length
        };
    },
    
    /**
     * Экспорт состояний в JSON
     */
    exportStates() {
        const states = this.getAllStates();
        const exportData = {
            exportDate: new Date().toISOString(),
            version: "1.0",
            states: states,
            config: {
                enabled: SearchStateConfig.enabled,
                enabledModels: SearchStateConfig.enabledModels,
                disabledModels: SearchStateConfig.disabledModels
            }
        };
        
        return JSON.stringify(exportData, null, 2);
    },
    
    /**
     * Импорт состояний из JSON
     */
    importStates(jsonData) {
        try {
            const importData = JSON.parse(jsonData);
            
            if (!importData.states || typeof importData.states !== 'object') {
                throw new Error("Неверный формат данных импорта");
            }
            
            let importedCount = 0;
            
            Object.entries(importData.states).forEach(([modelName, state]) => {
                if (this.isValidState(state)) {
                    const key = SearchStateConfig.storageKeyPrefix + modelName;
                    localStorage.setItem(key, JSON.stringify(state));
                    importedCount++;
                } else {
                    SearchStateConfig.warn(`Пропущено невалидное состояние для ${modelName}`);
                }
            });
            
            SearchStateConfig.log(`Импортировано ${importedCount} состояний`);
            return importedCount;
            
        } catch (error) {
            SearchStateConfig.warn("Ошибка импорта состояний:", error);
            throw error;
        }
    }
};

// Глобальные утилиты для консоли разработчика
window.AmanatSearchState = {
    config: SearchStateConfig,
    utils: SearchStateUtils,
    
    // Быстрые команды для отладки
    enable() { 
        SearchStateConfig.enabled = true; 
        console.log("Сохранение состояния поиска включено");
    },
    
    disable() { 
        SearchStateConfig.enabled = false; 
        console.log("Сохранение состояния поиска отключено");
    },
    
    debug() { 
        SearchStateConfig.debug = true; 
        console.log("Отладочный режим включен");
    },
    
    stats() {
        const stats = SearchStateUtils.getStatistics();
        console.table(stats.modelCounts);
        console.log("Общая статистика:", stats);
        return stats;
    },
    
    clear() {
        const count = SearchStateUtils.clearAllStates();
        console.log(`Очищено ${count} сохраненных состояний`);
    }
};



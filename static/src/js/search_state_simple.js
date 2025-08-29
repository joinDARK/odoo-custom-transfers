/** @odoo-module **/

import { Component, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { SearchStateConfig, SearchStateUtils } from "./search_state_config";

/**
 * Простой и надежный подход к сохранению состояния поиска
 * Использует события и localStorage напрямую
 */
class SearchStatePersistence {
    constructor() {
        this.enabled = SearchStateConfig.enabled;
        this.currentModel = null;
        this.searchData = {};
    }

    /**
     * Инициализация отслеживания событий поиска
     */
    init() {
        // Отслеживаем изменения в поисковой панели
        document.addEventListener('input', this._onSearchInput.bind(this));
        document.addEventListener('change', this._onSearchChange.bind(this));
        document.addEventListener('click', this._onSearchClick.bind(this));
        
        // Отслеживаем смену страниц/моделей
        window.addEventListener('hashchange', this._onPageChange.bind(this));
        window.addEventListener('popstate', this._onPageChange.bind(this));
        
        SearchStateConfig.log('Search state persistence инициализован');
    }

    /**
     * Обработчик ввода в поисковые поля
     */
    _onSearchInput(event) {
        const target = event.target;
        
        // Проверяем, что это поле поиска
        if (!target.closest('.o_searchview') && !target.closest('.o_control_panel')) {
            return;
        }

        // Определяем текущую модель
        this._detectCurrentModel();
        
        if (!this.currentModel || !SearchStateConfig.isEnabledForModel(this.currentModel)) {
            return;
        }

        // Сохраняем значение поля
        if (target.name && SearchStateConfig.shouldSaveField(target.name)) {
            this._saveFieldValue(target.name, target.value);
        }
    }

    /**
     * Обработчик изменений чекбоксов и селектов
     */
    _onSearchChange(event) {
        const target = event.target;
        
        if (!target.closest('.o_searchview') && !target.closest('.o_control_panel')) {
            return;
        }

        this._detectCurrentModel();
        
        if (!this.currentModel || !SearchStateConfig.isEnabledForModel(this.currentModel)) {
            return;
        }

        // Сохраняем состояние фильтров
        if (target.type === 'checkbox' && target.name) {
            this._saveFilterState(target.name, target.checked);
        }
    }

    /**
     * Обработчик кликов по фильтрам
     */
    _onSearchClick(event) {
        const target = event.target;
        
        // Проверяем клики по фильтрам
        const filterButton = target.closest('.o_searchview_facet, .o_filter_menu button');
        if (!filterButton) return;

        this._detectCurrentModel();
        
        if (!this.currentModel || !SearchStateConfig.isEnabledForModel(this.currentModel)) {
            return;
        }

        // Небольшая задержка, чтобы состояние обновилось
        setTimeout(() => {
            this._saveCurrentSearchState();
        }, 100);
    }

    /**
     * Обработчик смены страницы/модели
     */
    _onPageChange() {
        const oldModel = this.currentModel;
        this._detectCurrentModel();
        
        if (oldModel && oldModel !== this.currentModel) {
            SearchStateConfig.log(`Смена модели с ${oldModel} на ${this.currentModel}`);
            
            // Сохраняем состояние старой модели
            if (SearchStateConfig.isEnabledForModel(oldModel)) {
                this._saveCurrentSearchState(oldModel);
            }
            
            // Восстанавливаем состояние новой модели
            if (SearchStateConfig.isEnabledForModel(this.currentModel)) {
                setTimeout(() => {
                    this._restoreSearchState();
                }, 300); // Даем время на загрузку интерфейса
            }
        }
    }

    /**
     * Определение текущей модели из URL или DOM
     */
    _detectCurrentModel() {
        // Пытаемся определить из URL
        const hash = window.location.hash;
        const modelMatch = hash.match(/model=([^&]+)/);
        if (modelMatch) {
            this.currentModel = decodeURIComponent(modelMatch[1]);
            return;
        }

        // Пытаемся определить из action в URL
        const actionMatch = hash.match(/action=(\d+)/);
        if (actionMatch) {
            const actionId = actionMatch[1];
            // Здесь можно добавить маппинг action_id -> model_name
            // Пока используем простое определение из DOM
        }

        // Определяем из атрибутов DOM
        const controlPanel = document.querySelector('.o_control_panel');
        if (controlPanel) {
            const modelElement = controlPanel.querySelector('[data-model]');
            if (modelElement) {
                this.currentModel = modelElement.dataset.model;
                return;
            }
        }

        // Определяем из breadcrumb или заголовка
        const breadcrumb = document.querySelector('.o_breadcrumb');
        if (breadcrumb) {
            const text = breadcrumb.textContent.toLowerCase();
            if (text.includes('заявк')) this.currentModel = 'amanat.zayavka';
            else if (text.includes('контрагент')) this.currentModel = 'amanat.contragent';
            else if (text.includes('конвертац')) this.currentModel = 'amanat.conversion';
            else if (text.includes('списан')) this.currentModel = 'amanat.writeoff';
        }
    }

    /**
     * Сохранение значения поля
     */
    _saveFieldValue(fieldName, value) {
        if (!this.searchData[this.currentModel]) {
            this.searchData[this.currentModel] = { fields: {}, filters: {} };
        }
        
        this.searchData[this.currentModel].fields[fieldName] = value;
        this._persistToStorage();
        
        SearchStateConfig.log(`Сохранено поле ${fieldName} = ${value} для ${this.currentModel}`);
    }

    /**
     * Сохранение состояния фильтра
     */
    _saveFilterState(filterName, isActive) {
        if (!this.searchData[this.currentModel]) {
            this.searchData[this.currentModel] = { fields: {}, filters: {} };
        }
        
        this.searchData[this.currentModel].filters[filterName] = isActive;
        this._persistToStorage();
        
        SearchStateConfig.log(`Сохранен фильтр ${filterName} = ${isActive} для ${this.currentModel}`);
    }

    /**
     * Сохранение текущего состояния поиска
     */
    _saveCurrentSearchState(modelName = null) {
        const model = modelName || this.currentModel;
        if (!model) return;

        const searchPanel = document.querySelector('.o_searchview');
        if (!searchPanel) return;

        const state = {
            fields: {},
            filters: {},
            timestamp: Date.now(),
            version: "1.0"
        };

        // Собираем значения полей
        searchPanel.querySelectorAll('input, select').forEach(input => {
            if (input.name && input.value && SearchStateConfig.shouldSaveField(input.name)) {
                state.fields[input.name] = input.value;
            }
        });

        // Собираем активные фильтры
        searchPanel.querySelectorAll('.o_searchview_facet').forEach(facet => {
            const filterName = facet.dataset.name || facet.textContent.trim();
            if (filterName && SearchStateConfig.shouldSaveFilter(filterName)) {
                state.filters[filterName] = true;
            }
        });

        // Сохраняем в localStorage
        const storageKey = SearchStateConfig.storageKeyPrefix + model;
        try {
            localStorage.setItem(storageKey, JSON.stringify(state));
            SearchStateConfig.log(`Сохранено полное состояние для ${model}:`, state);
        } catch (error) {
            SearchStateConfig.warn('Ошибка сохранения состояния:', error);
        }
    }

    /**
     * Восстановление состояния поиска
     */
    _restoreSearchState() {
        if (!this.currentModel) return;

        const storageKey = SearchStateConfig.storageKeyPrefix + this.currentModel;
        const savedStateStr = localStorage.getItem(storageKey);
        
        if (!savedStateStr) return;

        try {
            const savedState = JSON.parse(savedStateStr);
            
            if (!SearchStateUtils.isValidState(savedState)) {
                localStorage.removeItem(storageKey);
                return;
            }

            SearchStateConfig.log(`Восстанавливаем состояние для ${this.currentModel}:`, savedState);

            // Восстанавливаем поля
            Object.entries(savedState.fields || {}).forEach(([fieldName, value]) => {
                const input = document.querySelector(`.o_searchview input[name="${fieldName}"], .o_searchview select[name="${fieldName}"]`);
                if (input) {
                    input.value = value;
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                }
            });

            // Восстанавливаем фильтры требует более сложной логики
            // Пока пропускаем, так как это зависит от конкретной структуры DOM

        } catch (error) {
            SearchStateConfig.warn('Ошибка восстановления состояния:', error);
            localStorage.removeItem(storageKey);
        }
    }

    /**
     * Сохранение в localStorage с оптимизацией
     */
    _persistToStorage() {
        // Ограничиваем частоту сохранения
        if (this._saveTimeout) {
            clearTimeout(this._saveTimeout);
        }
        
        this._saveTimeout = setTimeout(() => {
            Object.entries(this.searchData).forEach(([model, data]) => {
                if (SearchStateConfig.isEnabledForModel(model)) {
                    const storageKey = SearchStateConfig.storageKeyPrefix + model;
                    const state = {
                        ...data,
                        timestamp: Date.now(),
                        version: "1.0"
                    };
                    
                    try {
                        localStorage.setItem(storageKey, JSON.stringify(state));
                    } catch (error) {
                        SearchStateConfig.warn(`Ошибка сохранения для ${model}:`, error);
                    }
                }
            });
        }, 500); // Сохраняем не чаще чем раз в 500ms
    }
}

// Создаем глобальный экземпляр
const searchStatePersistence = new SearchStatePersistence();

// Инициализируем после загрузки DOM
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        searchStatePersistence.init();
    });
} else {
    searchStatePersistence.init();
}

// Экспортируем для использования в других модулях
export { searchStatePersistence };

// Добавляем в глобальный объект для отладки
window.AmanatSearchStatePersistence = searchStatePersistence;



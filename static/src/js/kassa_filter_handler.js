/** @odoo-module */

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";

// Патчим ListController для заявок
patch(ListController.prototype, {
    async setup() {
        await super.setup();
        
        // Проверяем, есть ли данные о результате отправки на сервер в контексте
        this.checkServerResponse();
    },

    checkServerResponse() {
        const context = this.props.context || {};
        
        // Проверяем, есть ли результат отправки данных на сервер
        if (context.server_response && context.server_status) {
            this.logServerResponse(context);
        }
    },

    logServerResponse(context) {
        const { server_response, server_status, sent_count, filtered_zayavkas_count, kassa_file_id, kassa_file_name } = context;
        
        console.group('🏛️ Результат отправки данных на сервер Excel');
        console.log('📊 Количество отфильтрованных заявок:', filtered_zayavkas_count || 0);
        console.log('📤 Количество отправленных заявок:', sent_count || 0);
        console.log('📡 Статус отправки:', server_status);
        console.log('🔧 Касса:', context.kassa_type || 'не указана');
        console.log('📅 Поле фильтрации:', context.filter_field || 'не указано');
        console.log('📅 Дата с:', context.date_from || 'не указана');
        console.log('📅 Дата по:', context.date_to || 'не указана');
        
        if (server_status === 'success') {
            console.log('✅ Успешно отправлено на сервер!');
            console.log('🎯 Ответ сервера:', server_response);
            
            if (kassa_file_id) {
                console.log('📁 Создан файл в системе:');
                console.log('   • ID файла:', kassa_file_id);
                console.log('   • Название файла:', kassa_file_name);
                console.log('   • Файл автоматически скачивается с сервера');
            }
            
            console.log('📋 Отправленные данные включают:');
            console.log('   • Контрагент, Субагент, Клиент, Менеджер');
            console.log('   • Даты: сделка закрыта, фиксация курса, поступление на РС');
            console.log('   • Суммы: заявка, итого клиент, эквивалент USD');
            console.log('   • Проценты: вознаграждения, скрытые комиссии');
            console.log('   • Курсы: скрытый, поручения, Джесс, XE');
            console.log('   • Расходы: конвертация, платежи, операционные');
            console.log('   • Вознаграждения: наше, не наше, агентское');
            console.log('   • Финансовые результаты и анализ');
            console.log('   • Условия расчета и тип сделки');
            console.log('   • Дни просрочки по банкам');
            console.log('   • Суммы по валютам (USD, CNY, AED, THB, EUR, IDR)');
        } else if (server_status === 'error') {
            console.error('❌ Ошибка при отправке на сервер:', server_response);
        } else if (server_status === 'connection_error') {
            console.error('🔌 Ошибка соединения с сервером:', server_response);
        } else if (server_status === 'unexpected_error') {
            console.error('⚠️ Неожиданная ошибка:', server_response);
        }
        
        console.log('🌐 Адрес сервера:', 'http://incube.ai:8085/api/salesRegisters');
        console.log('⏰ Время отправки:', new Date().toLocaleString());
        console.groupEnd();
        
        // Показываем уведомление пользователю
        this.showNotification(server_status, sent_count, filtered_zayavkas_count, kassa_file_id, kassa_file_name);
    },

    showNotification(status, sent_count, filtered_count, kassa_file_id, kassa_file_name) {
        const { notification } = this.env.services;
        
        if (status === 'success') {
            let message = `✅ Успешно отправлено ${sent_count} заявок из ${filtered_count} на сервер Excel! Полный набор данных с вычисляемыми полями.`;
            if (kassa_file_name) {
                message += ` Файл "${kassa_file_name}" создан и скачивается автоматически.`;
            }
            notification.add(message, { type: 'success', sticky: false });
        } else if (status === 'error') {
            notification.add(
                `❌ Ошибка при отправке ${sent_count} заявок на сервер Excel. Проверьте консоль для подробностей.`,
                { type: 'danger', sticky: true }
            );
        } else if (status === 'connection_error') {
            notification.add(
                `🔌 Не удалось подключиться к серверу Excel. Проверьте соединение.`,
                { type: 'warning', sticky: true }
            );
        } else if (status === 'unexpected_error') {
            notification.add(
                `⚠️ Неожиданная ошибка при отправке данных. Проверьте консоль для подробностей.`,
                { type: 'danger', sticky: true }
            );
        }
    }
});

// Также создаем расширение для wizard'а касс
registry.category("actions").add("kassa_filter_response_handler", {
    Component: Component,
    
    async execute(env, action) {
        // Проверяем контекст после применения фильтра
        const context = action.context || {};
        
        if (context.server_response && context.server_status) {
            const { server_response, server_status, sent_count, filtered_zayavkas_count, kassa_file_id, kassa_file_name } = context;
            
            console.group('🏛️ Результат фильтрации по кассам и отправки на сервер');
            console.log('📊 Количество отфильтрованных заявок:', filtered_zayavkas_count || 0);
            console.log('📤 Количество отправленных заявок:', sent_count || 0);
            console.log('📡 Статус отправки:', server_status);
            console.log('🔧 Касса:', context.kassa_type || 'не указана');
            console.log('📅 Поле фильтрации:', context.filter_field || 'не указано');
            console.log('📅 Дата с:', context.date_from || 'не указана');
            console.log('📅 Дата по:', context.date_to || 'не указана');
            
            if (server_status === 'success') {
                console.log('✅ Успешно отправлено на сервер!');
                console.log('🎯 Ответ сервера:', server_response);
                
                if (kassa_file_id) {
                    console.log('📁 Создан файл в системе:');
                    console.log('   • ID файла:', kassa_file_id);
                    console.log('   • Название файла:', kassa_file_name);
                    console.log('   • Доступ к файлу: Касса файлы в меню');
                }
                
                console.log('📋 Отправленные данные включают:');
                console.log('   • Основные: контрагент, субагент, клиент, менеджер');
                console.log('   • Даты: сделка закрыта, фиксация курса, поступление на РС, ТЕЗЕРА');
                console.log('   • Суммы: заявка по валютам, итого клиент, эквивалент USD');
                console.log('   • Проценты: вознаграждения руками, скрытые комиссии');
                console.log('   • Курсы: скрытый, поручения, Джесс (по валютам), XE');
                console.log('   • Расходы: конвертация, платежи, операционные, субагента');
                console.log('   • Вознаграждения: наше, не наше, агентское, тезер');
                console.log('   • Финансовые результаты: реальные и в процентах');
                console.log('   • Условия расчета, тип сделки, аккредитив');
                console.log('   • Дни просрочки: Сбербанк, Совкомбанк, ВТБ, Индивидуалы');
                console.log('   • Плательщики субагента и банк');
            } else {
                console.error('❌ Ошибка при отправке:', server_response);
            }
            
            console.log('🌐 Адрес сервера:', 'http://incube.ai:8085/api/salesRegisters');
            console.log('⏰ Время отправки:', new Date().toLocaleString());
            console.groupEnd();
        }
        
        return action;
    }
});

console.log('📋 Расширенный обработчик фильтра по кассам загружен - поддерживает полный набор данных заявок'); 
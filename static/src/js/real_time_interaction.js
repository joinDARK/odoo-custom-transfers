/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { session } from "@web/session";
import { makeContext } from "@web/core/context";
import { useService } from "@web/core/utils/hooks";

// Сервис для отслеживания активных редакторов
const editingStateService = {
    dependencies: [],
    
    start() {
        const editingRecords = new Map(); // model_name:record_id -> user_info
        const editingNotifications = new Map(); // notification_id -> record_info
        
        return {
            setRecordEditing(model, recordId, userInfo) {
                const key = `${model}:${recordId}`;
                editingRecords.set(key, userInfo);
            },
            
            getRecordEditor(model, recordId) {
                const key = `${model}:${recordId}`;
                return editingRecords.get(key);
            },
            
            clearRecordEditing(model, recordId) {
                const key = `${model}:${recordId}`;
                editingRecords.delete(key);
            },
            
            addEditingNotification(notificationId, recordInfo) {
                editingNotifications.set(notificationId, recordInfo);
            },
            
            removeEditingNotification(notificationId) {
                editingNotifications.delete(notificationId);
            }
        };
    }
};

// Основной сервис real-time обновлений для Odoo 18
const amanatRealTimeService = {
    dependencies: ["bus_service", "action", "notification", "orm"],
    
    start(env, { bus_service, action, notification, orm }) {
        console.log("🚀 Amanat Real-Time Service for Odoo 18 starting...");
        
        // Получаем ID текущего пользователя для Odoo 18
        let currentUserId = null;
        
        try {
            // Способ 1: Через env.services.user (основной для Odoo 18)
            if (env.services.user && env.services.user.userId) {
                currentUserId = env.services.user.userId;
                console.log("🔍 Method 1: Got user ID from env.services.user:", currentUserId);
            }
            
            // Способ 2: Через window.odoo.session_info
            if (!currentUserId && window.odoo && window.odoo.session_info) {
                currentUserId = window.odoo.session_info.uid || window.odoo.session_info.user_id;
                console.log("🔍 Method 2: Got user ID from window.odoo.session_info:", currentUserId);
            }
            
            // Способ 3: Через глобальную переменную session
            if (!currentUserId && typeof session !== 'undefined') {
                currentUserId = session.user_id || session.uid;
                console.log("🔍 Method 3: Got user ID from global session:", currentUserId);
            }
            
            // Способ 4: Через env.services (альтернативные пути)
            if (!currentUserId) {
                try {
                    // Проверяем другие возможные сервисы
                    const userService = env.services.user || env.services.auth || env.services.userService;
                    if (userService) {
                        currentUserId = userService.userId || userService.user?.id || userService.uid;
                        console.log("🔍 Method 4: Got user ID from alternative services:", currentUserId);
                    }
                } catch (e) {
                    console.warn("🔍 Method 4 failed:", e);
                }
            }
            
            // Способ 5: Попробуем через cookie или localStorage
            if (!currentUserId) {
                try {
                    const sessionData = localStorage.getItem('session_info') || sessionStorage.getItem('session_info');
                    if (sessionData) {
                        const parsed = JSON.parse(sessionData);
                        currentUserId = parsed.uid || parsed.user_id;
                        console.log("🔍 Method 5: Got user ID from storage:", currentUserId);
                    }
                } catch (e) {
                    console.warn("🔍 Method 5 failed:", e);
                }
            }
            
            // Способ 6: Пробуем получить из DOM или других источников
            if (!currentUserId) {
                try {
                    const metaElements = document.querySelectorAll('meta[name="user-id"], meta[name="uid"], meta[name="current-user"]');
                    for (const meta of metaElements) {
                        if (meta.content) {
                            currentUserId = parseInt(meta.content);
                            console.log("🔍 Method 6: Got user ID from meta tags:", currentUserId);
                            break;
                        }
                    }
                } catch (e) {
                    console.warn("🔍 Method 6 failed:", e);
                }
            }
            
            // Логируем все доступные данные для отладки
            console.log("🔍 DEBUG: Available data sources:");
            console.log("  - env.services.user:", env.services.user);
            console.log("  - window.odoo:", window.odoo);
            console.log("  - global session:", typeof session !== 'undefined' ? session : 'undefined');
            console.log("  - env.services keys:", Object.keys(env.services));
            
        } catch (e) {
            console.warn("🔍 Error getting user ID:", e);
        }
        
        // Fallback: используем фиксированный ID для тестирования (только в разработке)
        if (!currentUserId) {
            console.warn("🔍 Could not determine user ID, using fallback for testing");
            currentUserId = 2; // Fallback для тестирования
        }
        
        console.log("🆔 Final user ID:", currentUserId);
        
        if (!currentUserId) {
            console.error("❌ Cannot start real-time service without user ID");
            // Попробуем получить пользователя асинхронно через RPC
            console.log("🔍 Trying to get user ID via RPC...");
            
            env.services.rpc("/web/session/get_session_info", {}).then((sessionInfo) => {
                console.log("🔍 RPC session info:", sessionInfo);
                if (sessionInfo && (sessionInfo.uid || sessionInfo.user_id)) {
                    const userId = sessionInfo.uid || sessionInfo.user_id;
                    console.log("✅ Got user ID via RPC:", userId);
                    // Перезапускаем сервис с полученным ID
                    startRealtimeService(userId, env, bus_service, action, notification, orm);
                } else {
                    console.error("❌ Could not get user ID via RPC either");
                }
            }).catch((error) => {
                console.error("❌ RPC failed:", error);
            });
            
            return {
                getCurrentUserId: () => null,
                sendTestMessage: () => console.log("🧪 Service not started - no user ID")
            };
        }
        
        // Запускаем основной сервис
        return startRealtimeService(currentUserId, env, bus_service, action, notification, orm);
    },
};

// Вынесем основную логику в отдельную функцию
function startRealtimeService(currentUserId, env, bus_service, action, notification, orm) {
    console.log("🚀 Starting realtime service with user ID:", currentUserId);
        
        // Подписываемся на каналы согласно Odoo 18 API
    try {
        // Канал 1: Кастомный канал для real-time обновлений
        const customChannel = `amanat_realtime_${currentUserId}`;
        console.log(`📡 Subscribing to custom channel: ${customChannel}`);
        
        bus_service.subscribe(customChannel, (payload) => {
            console.log("🎯 CUSTOM CHANNEL MESSAGE:", payload);
            handleRealtimeMessage(payload, env);
        });
        
        // Канал 2: Личный канал пользователя
        const userChannel = `res.users,${currentUserId}`;
        console.log(`📡 Subscribing to user channel: ${userChannel}`);
        
        bus_service.subscribe(userChannel, (payload) => {
            console.log("🎯 USER CHANNEL MESSAGE:", payload);
            handleRealtimeMessage(payload, env);
        });
        
        // Канал 3: Общий канал для всех amanat обновлений
        const generalChannel = "amanat_general_updates";
        console.log(`📡 Subscribing to general channel: ${generalChannel}`);
        
        bus_service.subscribe(generalChannel, (payload) => {
            console.log("🎯 GENERAL CHANNEL MESSAGE:", payload);
            handleRealtimeMessage(payload, env);
        });
        
        // Запускаем bus сервис (важно для Odoo 18!)
        bus_service.start();
        console.log("✅ Bus service started");
        
    } catch (error) {
        console.error("❌ Error setting up bus subscriptions:", error);
    }
    
    // Обработчик real-time сообщений
    function handleRealtimeMessage(payload, env) {
        console.log("🔥 HANDLING REAL-TIME MESSAGE:", payload);
        console.log("🔥 Message type:", typeof payload);
        console.log("🔥 Message keys:", payload ? Object.keys(payload) : 'null');
        
        try {
            // Извлекаем данные из разных возможных структур
            let messageData = payload;
            
            if (payload.data) {
                messageData = payload.data;
                console.log("🔥 Using payload.data:", messageData);
            } else if (payload.type === 'amanat_realtime_update') {
                messageData = payload;
                console.log("🔥 Direct amanat_realtime_update:", messageData);
            }
            
            // Проверяем, что это наше сообщение
            if (messageData && (
                messageData.type === 'amanat_realtime_update' ||
                (messageData.model && messageData.model.includes('amanat')) ||
                (messageData.type && ['create', 'update', 'delete'].includes(messageData.type))
            )) {
                console.log("✅ Valid amanat real-time message detected");
                
                // Показываем уведомление
                showNotification(messageData, notification);
                
                // Обновляем интерфейс
                updateInterface(messageData, env);
                
            } else {
                console.log("🔍 Not an amanat real-time message:", messageData);
            }
            
        } catch (error) {
            console.error("❌ Error handling real-time message:", error);
        }
    }
    
    // Показ уведомления пользователю
    function showNotification(messageData, notification) {
        try {
            const actionText = {
                'create': 'создал',
                'update': 'обновил',
                'delete': 'удалил'
            }[messageData.type] || 'изменил';
            
            const userName = messageData.user_name || 'Пользователь';
            const recordsCount = messageData.records ? messageData.records.length : 1;
            const modelName = messageData.model_display_name || messageData.model || 'объект';
            
            const message = `${userName} ${actionText} ${recordsCount} записей в ${modelName}`;
            
            if (notification && notification.add) {
                notification.add(message, {
                    title: "🔄 Real-time обновление",
                    type: "info",
                    sticky: false
                });
            }
            
            console.log("📢 Notification shown:", message);
            
        } catch (error) {
            console.error("❌ Error showing notification:", error);
        }
    }
    
    // Обновление интерфейса
    function updateInterface(messageData, env) {
        try {
            console.log("🔄 Updating interface for:", messageData);
            
            // Получаем текущее действие/контроллер
            const currentAction = env.services.action?.currentController?.action;
            const currentModel = currentAction?.res_model;
            
            console.log("🔄 Current model:", currentModel);
            console.log("🔄 Message model:", messageData.model);
            
            // Проверяем, относится ли обновление к текущей модели
            if (currentModel && messageData.model && currentModel === messageData.model) {
                console.log("✅ Models match, updating interface");
                
                // Определяем тип представления
                const viewType = currentAction?.view_mode?.split(',')[0] || 'unknown';
                console.log("🔄 Current view type:", viewType);
                
                // Обновляем в зависимости от типа представления
                switch (viewType) {
                    case 'list':
                        updateListView(messageData);
                        break;
                    case 'form':
                        updateFormView(messageData);
                        break;
                    case 'kanban':
                        updateKanbanView(messageData);
                        break;
                    default:
                        console.log(`🔄 View type ${viewType} not supported for updates`);
                }
            } else {
                console.log("🔄 Models don't match, skipping interface update");
            }
            
        } catch (error) {
            console.error("❌ Error updating interface:", error);
        }
    }
    
    // Обновление List View
    function updateListView(messageData) {
        console.log("📋 Updating list view");
        
        try {
            const listContainer = document.querySelector('.o_list_view table tbody');
            if (!listContainer) {
                console.log("📋 List container not found");
                return;
            }
            
            // Добавляем CSS анимацию для обновленных строк
            if (!document.getElementById('amanat-realtime-styles')) {
                const style = document.createElement('style');
                style.id = 'amanat-realtime-styles';
                style.textContent = `
                    .realtime-updated {
                        background-color: #d4edda !important;
                        transition: background-color 0.3s ease;
                    }
                    .field-updated {
                        background-color: #fff3cd !important;
                        transition: background-color 0.3s ease;
                    }
                `;
                document.head.appendChild(style);
            }
            
            // Обновляем записи
            if (messageData.records) {
                messageData.records.forEach(record => {
                    updateListRecord(listContainer, record, messageData);
                });
            }
            
        } catch (error) {
            console.error("❌ Error updating list view:", error);
        }
    }
    
    // Обновление записи в списке
    function updateListRecord(listContainer, record, messageData) {
        try {
            const recordRow = listContainer.querySelector(`tr[data-id="${record.id}"]`);
            
            if (recordRow) {
                console.log(`📋 Updating existing record ${record.id}`);
                
                // Обновляем ячейки
                const cells = recordRow.querySelectorAll('td[name]');
                cells.forEach(cell => {
                    const fieldName = cell.getAttribute('name');
                    if (fieldName && record.hasOwnProperty(fieldName)) {
                        const newValue = record[fieldName];
                        const oldValue = cell.textContent.trim();
                        
                        if (newValue != oldValue) {
                            cell.textContent = newValue;
                            cell.classList.add('field-updated');
                            
                            setTimeout(() => {
                                cell.classList.remove('field-updated');
                            }, 3000);
                        }
                    }
                });
                
                // Подсвечиваем всю строку
                recordRow.classList.add('realtime-updated');
                setTimeout(() => {
                    recordRow.classList.remove('realtime-updated');
                }, 3000);
                
            } else {
                console.log(`📋 Record ${record.id} not found in current view`);
            }
            
        } catch (error) {
            console.error("❌ Error updating list record:", error);
        }
    }
    
    // Обновление Form View
    function updateFormView(messageData) {
        console.log("📝 Updating form view");
        // TODO: Реализовать обновление формы
    }
    
    // Обновление Kanban View
    function updateKanbanView(messageData) {
        console.log("📊 Updating kanban view");
        // TODO: Реализовать обновление kanban
    }
    
    console.log("✅ Amanat Real-Time Service started successfully");
    
    // Возвращаем публичные методы
    return {
        getCurrentUserId: () => currentUserId,
        sendTestMessage: () => {
            console.log("🧪 Sending test message...");
            // Можно добавить тестовую отправку
        }
    };
}

// Регистрируем сервисы
registry.category("services").add("editing_state", editingStateService);
registry.category("services").add("amanat_realtime", amanatRealTimeService);

// Глобальные функции для тестирования
window.testAmanatRealtime = {
    // Тест стандартного уведомления
    testSimpleNotification: async () => {
        console.log("🧪 Testing simple notification...");
        try {
            const result = await fetch("/amanat/test_realtime_simple", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-Requested-With": "XMLHttpRequest"
                },
                body: JSON.stringify({
                    jsonrpc: "2.0",
                    method: "call",
                    params: {},
                    id: Math.floor(Math.random() * 1000000)
                })
            });
            const data = await result.json();
            console.log("🧪 Simple notification result:", data);
        } catch (error) {
            console.error("🧪 Simple notification error:", error);
        }
    },
    
    // Тест кастомного канала
    testCustomChannel: async () => {
        console.log("🧪 Testing custom channel...");
        try {
            const result = await fetch("/amanat/test_custom_channel", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-Requested-With": "XMLHttpRequest"
                },
                body: JSON.stringify({
                    jsonrpc: "2.0",
                    method: "call",
                    params: {},
                    id: Math.floor(Math.random() * 1000000)
                })
            });
            const data = await result.json();
            console.log("🧪 Custom channel result:", data);
        } catch (error) {
            console.error("🧪 Custom channel error:", error);
        }
    },
    
    // Тест всех методов
    testAllMethods: async () => {
        console.log("🧪 Testing all methods...");
        try {
            const result = await fetch("/amanat/test_all_methods", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-Requested-With": "XMLHttpRequest"
                },
                body: JSON.stringify({
                    jsonrpc: "2.0",
                    method: "call",
                    params: {},
                    id: Math.floor(Math.random() * 1000000)
                })
            });
            const data = await result.json();
            console.log("🧪 All methods result:", data);
        } catch (error) {
            console.error("🧪 All methods error:", error);
        }
    }
};

console.log("🧪 Test functions available at window.testAmanatRealtime");
console.log("🧪 - window.testAmanatRealtime.testSimpleNotification()");
console.log("🧪 - window.testAmanatRealtime.testCustomChannel()"); 
console.log("🧪 - window.testAmanatRealtime.testAllMethods()");
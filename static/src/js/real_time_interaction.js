/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { session } from "@web/session";
import { makeContext } from "@web/core/context";

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

// Основной сервис real-time обновлений
const amanatRealTimeService = {
    dependencies: ["bus_service", "action", "notification", "orm", "editing_state"],
    
    start(env, { bus_service, action, notification, orm, editing_state }) {
        console.log("Amanat Enhanced RealTime Service starting...");
        
        // Получаем ID пользователя из разных источников
        let currentUserId = session.user_id || session.uid || session.user?.id;
        
        // Пробуем получить из env.services
        if (!currentUserId) {
            try {
                // Проверяем разные возможные названия сервиса пользователя
                const userService = env.services.user || env.services.auth || env.services.userService;
                currentUserId = userService?.userId || userService?.user?.id || userService?.uid;
            } catch (e) {
                console.warn("Could not get user ID from env.services:", e);
            }
        }
        
        // Пробуем получить из odoo глобального объекта
        if (!currentUserId) {
            try {
                currentUserId = window.odoo?.session_info?.uid || window.odoo?.session_info?.user_id;
            } catch (e) {
                console.warn("Could not get user ID from window.odoo:", e);
            }
        }
        
        // Последняя попытка - используем фиксированный ID для тестирования
        if (!currentUserId) {
            console.warn("Could not determine user ID, using default for testing");
            currentUserId = 2; // Стандартный admin ID
        }
        
        console.log("🆔 Current user ID:", currentUserId);
        console.log("📊 Session object:", session);
        console.log("🔑 Available session keys:", Object.keys(session));
        console.log("🛠️ Env services keys:", Object.keys(env.services));
        
        // Подписываемся на личный канал пользователя для real-time обновлений
        const userChannel = `res.users,${currentUserId}`;
        console.log(`🔄 Subscribing to user channel: ${userChannel}...`);
        console.log("🔄 Bus service:", bus_service);
        
        bus_service.subscribe(userChannel, async (message) => {
            console.log("🔥 RAW received message:", message);
            console.log("🔥 Message type:", typeof message);
            console.log("🔥 Message structure:", message ? Object.keys(message) : 'null');
            console.log("🔥 User channel subscription is ACTIVE for:", userChannel);
            
            // В Odoo 18 сообщение может иметь разную структуру
            let payload = message;
            
            // Проверяем разные возможные структуры сообщений
            if (message.payload) {
                payload = message.payload;
            } else if (message.message) {
                payload = message.message;
            } else if (message[1]) {
                // Иногда сообщение приходит как массив [channel, event_type, data]
                // Для нашего случая это будет [channel, 'amanat_realtime_update', data]
                payload = message[2] || message[1];
            }
            
            console.log("🔥 Processing payload:", payload);

            if (!payload || !['create', 'update', 'delete'].includes(payload.type)) {
                console.log("❌ Invalid message format or type:", payload);
                console.log("❌ Available payload keys:", payload ? Object.keys(payload) : 'null');
                return;
            }

            // Пользователь получает уведомления только от других пользователей
            // так как в backend мы исключаем текущего пользователя при отправке
            console.log(`📨 Received real-time update from user ${payload.user_name} (ID: ${payload.user_id})`);
            console.log(`📨 Current user ID: ${currentUserId}`);

            try {
                console.log("🚀 Processing realtime update:", payload);
                await handleRealtimeUpdate(payload, env, notification, orm, editing_state);
                console.log("✅ Realtime update processed successfully");
            } catch (error) {
                console.error("❌ Error handling realtime update:", error);
            }
        });
        
        console.log("Amanat Enhanced RealTime Service started successfully");
        return {
            getCurrentUserId: () => currentUserId
        };
    },
};

async function handleRealtimeUpdate(message, env, notification, orm, editingState) {
    const currentController = env.services.action.currentController;
    
    if (!currentController || !currentController.action) {
        console.log("No current controller or action");
        return;
    }
    
    const currentModel = currentController.action.res_model;
    
    if (currentModel !== message.model) {
        console.log("Models don't match, skipping update. Current:", currentModel, "Message:", message.model);
        return;
    }
    
    // Определяем тип текущего представления
    const viewType = getViewType(currentController);
    
    console.log("Current view type:", viewType, "Message type:", message.type);
    
    // Обрабатываем разные типы представлений с точечными обновлениями
    switch (viewType) {
        case 'list':
            await handleListViewRealtimeUpdate(currentController, message, env, notification, editingState);
            break;
            
        case 'form':
            await handleFormViewRealtimeUpdate(currentController, message, env, notification, editingState);
            break;
            
        case 'kanban':
            await handleKanbanViewRealtimeUpdate(currentController, message, env, notification, editingState);
            break;
            
        default:
            console.log(`View type ${viewType} not supported for realtime updates`);
            showFallbackNotification(notification, message);
    }
}

function getViewType(controller) {
    return controller.action.view_mode?.split(',')[0] || 
           controller.props?.type || 
           controller.viewType ||
           'unknown';
}

async function handleListViewRealtimeUpdate(controller, message, env, notification, editingState) {
    console.log("Handling list view realtime update");
    
    try {
        // Пытаемся найти модель контроллера
        const model = controller.model;
        
        if (model && model.root && model.root.model) {
            // Работаем с моделью напрямую
            await handleModelUpdate(model, message, env, notification);
        } else {
            // Fallback к базовой реализации
            console.log("Using fallback list update");
            await handleBasicListUpdate(controller, message, env, notification, editingState);
        }
        
    } catch (error) {
        console.error("Error in handleListViewRealtimeUpdate:", error);
        await fallbackReload(controller, message, notification);
    }
}

async function handleModelUpdate(model, message, env, notification) {
    try {
        switch (message.type) {
            case 'create':
                // Просто перезагружаем данные для новых записей
                await model.root.load();
                showNotification(notification, message, "Новые записи добавлены");
                break;
                
            case 'update':
                // Обновляем конкретные записи
                for (const recordData of message.records) {
                    const record = model.root.records.find(r => r.resId === recordData.id);
                    if (record) {
                        // Обновляем только измененные поля
                        await record.update(recordData, { reload: false });
                    }
                }
                // Перерисовываем представление
                if (model.root.notify_changes) {
                    model.root.notify_changes();
                }
                showNotification(notification, message, "Записи обновлены");
                break;
                
            case 'delete':
                // Удаляем записи из модели
                for (const recordData of message.records) {
                    model.root.records = model.root.records.filter(r => r.resId !== recordData.id);
                }
                if (model.root.notify_changes) {
                    model.root.notify_changes();
                }
                showNotification(notification, message, "Записи удалены");
                break;
        }
        return true;
    } catch (error) {
        console.error("Error in model update:", error);
        return false;
    }
}

async function handleBasicListUpdate(controller, message, env, notification, editingState) {
    // Получаем таблицу списка
    const listContainer = document.querySelector('.o_list_view');
    const tableBody = listContainer?.querySelector('tbody.o_list_table_ungrouped');
    
    if (!tableBody) {
        console.log("List table not found, falling back to reload");
        await fallbackReload(controller, message, notification);
        return;
    }
    
    switch (message.type) {
        case 'create':
            await handleListCreateUpdate(tableBody, message, controller, env, notification);
            break;
            
        case 'update':
            await handleListUpdateUpdate(tableBody, message, controller, env, notification, editingState);
            break;
            
        case 'delete':
            await handleListDeleteUpdate(tableBody, message, env, notification);
            break;
    }
}

async function handleListCreateUpdate(tableBody, message, controller, env, notification) {
    try {
        // Для создания новых записей лучше всего перезагрузить модель
        if (controller.model && controller.model.load) {
            await controller.model.load();
        } else {
            // Fallback - полная перезагрузка
            await fallbackReload(controller, message, notification);
            return;
        }
        
        showNotification(notification, message, `Добавлено записей: ${message.records.length}`);
    } catch (error) {
        console.error("Error in handleListCreateUpdate:", error);
        await fallbackReload(controller, message, notification);
    }
}

async function handleListUpdateUpdate(tableBody, message, controller, env, notification, editingState) {
    try {
        let updatedCount = 0;
        
        for (const recordData of message.records) {
            const row = tableBody.querySelector(`tr[data-id="${recordData.id}"]`);
            if (row) {
                await updateListRowContent(row, recordData, controller, env);
                highlightTableRow(row, 'info');
                updatedCount++;
            }
        }
        
        if (updatedCount > 0) {
            showNotification(notification, message, `Обновлено записей: ${updatedCount}`);
        }
        
    } catch (error) {
        console.error("Error in handleListUpdateUpdate:", error);
        await fallbackReload(controller, message, notification);
    }
}

async function handleListDeleteUpdate(tableBody, message, env, notification) {
    try {
        let deletedCount = 0;
        
        for (const recordData of message.records) {
            const row = tableBody.querySelector(`tr[data-id="${recordData.id}"]`);
            if (row) {
                highlightTableRow(row, 'danger');
                setTimeout(() => row.remove(), 1000);
                deletedCount++;
            }
        }
        
        if (deletedCount > 0) {
            showNotification(notification, message, `Удалено записей: ${deletedCount}`);
        }
        
    } catch (error) {
        console.error("Error in handleListDeleteUpdate:", error);
    }
}

async function updateListRowContent(row, recordData, controller, env) {
    try {
        // Обновляем ячейки в строке
        const cells = row.querySelectorAll('td[name]');
        
        for (const cell of cells) {
            const fieldName = cell.getAttribute('name');
            if (fieldName && recordData.hasOwnProperty(fieldName)) {
                const value = recordData[fieldName];
                updateCellContent(cell, value, fieldName);
            }
        }
    } catch (error) {
        console.error("Error updating row content:", error);
    }
}

function updateCellContent(cell, value, fieldName) {
    try {
        if (value === null || value === undefined) {
            cell.textContent = '';
            return;
        }
        
        // Для Many2one полей
        if (typeof value === 'object' && value.display_name) {
            cell.textContent = value.display_name;
        }
        // Для обычных полей
        else if (typeof value === 'string' || typeof value === 'number') {
            cell.textContent = value;
        }
        // Для boolean полей
        else if (typeof value === 'boolean') {
            cell.textContent = value ? '✓' : '';
        }
        // Для дат
        else if (fieldName.includes('date') && typeof value === 'string') {
            cell.textContent = new Date(value).toLocaleDateString();
        }
        else {
            cell.textContent = String(value);
        }
    } catch (error) {
        console.error("Error updating cell content:", error);
        cell.textContent = String(value);
    }
}

function highlightTableRow(row, type = 'info') {
    const className = `table-${type}`;
    row.classList.add(className);
    
    setTimeout(() => {
        row.classList.remove(className);
    }, 3000);
}

async function handleFormViewRealtimeUpdate(controller, message, env, notification, editingState) {
    console.log("Handling form view realtime update");
    
    const currentRecordId = getCurrentFormRecordId(controller);
    
    if (!currentRecordId) {
        console.log("No current record ID in form view");
        return;
    }
    
    // Проверяем, касается ли обновление текущей записи
    const affectedRecord = message.records.find(record => record.id === currentRecordId);
    
    if (affectedRecord) {
        await handleCurrentFormRecordUpdate(controller, message, affectedRecord, env, notification, editingState);
    }
}

function getCurrentFormRecordId(controller) {
    return controller?.model?.root?.resId || 
           controller?.props?.resId || 
           controller?.state?.currentId;
}

async function handleCurrentFormRecordUpdate(controller, message, recordData, env, notification, editingState) {
    try {
        // Проверяем наличие несохраненных изменений
        const hasUnsavedChanges = checkForUnsavedChanges(controller);
        
        if (hasUnsavedChanges) {
            showFormConflictNotification(notification, message, recordData, controller, env);
            return;
        }
        
        // Обновляем поля формы
        await updateFormFields(controller, recordData, message.changed_fields);
        
        showNotification(notification, message, "Запись обновлена другим пользователем");
        
    } catch (error) {
        console.error("Error in handleCurrentFormRecordUpdate:", error);
    }
}

function checkForUnsavedChanges(controller) {
    try {
        return controller?.model?.root?.isDirty || 
               controller?.model?.root?.hasUnsavedChanges ||
               false;
    } catch (error) {
        return false;
    }
}

async function updateFormFields(controller, recordData, changedFields) {
    try {
        if (controller.model && controller.model.root) {
            // Обновляем данные модели
            await controller.model.root.update(recordData, { reload: false });
        }
        
        // Подсвечиваем измененные поля
        if (changedFields && changedFields.length > 0) {
            highlightChangedFields(changedFields);
        }
        
    } catch (error) {
        console.error("Error updating form fields:", error);
    }
}

function highlightChangedFields(changedFields) {
    try {
        for (const fieldName of changedFields) {
            const fieldElement = document.querySelector(`[name="${fieldName}"]`);
            if (fieldElement) {
                fieldElement.classList.add('field-updated');
                setTimeout(() => {
                    fieldElement.classList.remove('field-updated');
                }, 3000);
            }
        }
    } catch (error) {
        console.error("Error highlighting changed fields:", error);
    }
}

function showFormConflictNotification(notification, message, recordData, controller, env) {
    try {
        notification.add(
            `Запись была изменена пользователем ${message.user_name}. У вас есть несохраненные изменения.`,
            {
                title: "Конфликт изменений",
                type: "warning",
                sticky: true,
                buttons: [
                    {
                        name: "Перезагрузить",
                        primary: true,
                        onClick: async () => {
                            if (controller.model && controller.model.root) {
                                await controller.model.root.load();
                            } else {
                                window.location.reload();
                            }
                        },
                    },
                    {
                        name: "Сохранить мои изменения",
                        onClick: async () => {
                            if (controller.model && controller.model.root && controller.model.root.save) {
                                await controller.model.root.save();
                            }
                        },
                    },
                ],
            }
        );
    } catch (error) {
        console.error("Error showing form conflict notification:", error);
    }
}

async function handleKanbanViewRealtimeUpdate(controller, message, env, notification, editingState) {
    console.log("Handling kanban view realtime update");
    // Для kanban представления пока используем простую перезагрузку
    await fallbackReload(controller, message, notification);
}

async function fallbackReload(controller, message, notification) {
    try {
        console.log("Performing fallback reload");
        
        if (controller && controller.model && controller.model.load) {
            await controller.model.load();
            showNotification(notification, message, "Данные обновлены");
        } else {
            // Последний resort - перезагрузка страницы (не рекомендуется)
            console.warn("Full page reload required");
            showFallbackNotification(notification, message);
        }
    } catch (error) {
        console.error("Error in fallback reload:", error);
        showFallbackNotification(notification, message);
    }
}

function showFallbackNotification(notification, message) {
    try {
        notification.add(
            `Данные были изменены пользователем ${message.user_name}`,
            {
                title: "Обновление данных",
                type: "info",
                buttons: [
                    {
                        name: "Обновить страницу",
                        primary: true,
                        onClick: () => window.location.reload(),
                    },
                ],
            }
        );
    } catch (error) {
        console.error("Error showing fallback notification:", error);
    }
}

function showNotification(notification, message, defaultText) {
    try {
        const text = defaultText || `Данные обновлены пользователем ${message.user_name}`;
        notification.add(text, {
            title: "Real-time обновление",
            type: "info",
        });
    } catch (error) {
        console.error("Error showing notification:", error);
    }
}

// Регистрируем сервисы
// registry.category("services").add("editing_state", editingStateService);
// registry.category("services").add("amanat_realtime", amanatRealTimeService);
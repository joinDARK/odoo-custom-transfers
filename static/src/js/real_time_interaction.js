/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { session } from "@web/session";
import { makeContext } from "@web/core/context";

const amanatRealTimeService = {
    dependencies: ["bus_service", "action", "notification", "orm"],
    
    start(env, { notification, orm }) {
        const busService = env.services.bus_service;
        const actionService = env.services.action;
        
        console.log("Amanat RealTime Service starting...");
        console.log("env", env);
        console.log("session_user_id", session.storeData.Store.settings.user_id.id);
        
        // Подписываемся на канал для real-time обновлений
        busService.subscribe("realtime_updates", async (message) => {
            console.log("message", message);

            if (!['create', 'update', 'delete'].includes(message.type)) {
                return;
            }
            
            try {
                if(!session.storeData.Store.settings.user_id.id == message.user_id) // TODO
                    await handleRealtimeUpdate(message, env, notification, orm);
            } catch (error) {
                console.error("Error handling realtime update:", error);
            }
        });
        
        console.log("Amanat RealTime Service started successfully");
        return {};
    },
};

async function handleRealtimeUpdate(message, env, notification, orm) {
    const currentController = env.services.action.currentController;
    
    if (!currentController || !currentController.action) {
        console.log("No current controller or action");
        return;
    }
    
    const currentModel = currentController.action.res_model;
    console.log("Current model:", currentModel);
    console.log("Message model:", message.model);
    
    if (currentModel !== message.model) {
        console.log("Models don't match, skipping update");
        return;
    }
    
    // Определяем тип текущего представления
    const viewType = currentController.action.view_mode || 
                    currentController.props?.type || 
                    currentController.viewType;
    
    console.log("Current view type:", viewType);
    
    // Обрабатываем разные типы представлений
    switch (viewType) {
        case 'list':
        case 'form':
            await handleListViewUpdate(currentController, message, env, notification, orm);
            break;

        case 'list,form':
            await handleListViewUpdate(currentController, message, env, notification, orm);
            break;
            
        case 'form':
            await handleFormViewUpdate(currentController, message, env, notification, orm);
            break;
            
        case 'kanban':
            await handleKanbanViewUpdate(currentController, message, env, notification, orm);
            break;
            
        default:
            console.log(`View type ${viewType} not supported for realtime updates`);
            await fallbackReload(currentController, message, notification);
    }
}

async function handleListViewUpdate(controller, message, env, notification, orm) {
    console.log("Handling list view update");
    
    try {
        // Попытка 1: Использовать метод reload если он доступен
        if (controller.reload && typeof controller.reload === 'function') {
            console.log("Using controller.reload() - 1");
            await controller.reload();
            showNotification(notification, message, "Список обновлен");
            return;
        }
        
        // Попытка 2: Обновить через модель списка
        if (controller.model && controller.model.load) {
            console.log("Using controller.model.load() - 2");
            await controller.model.load();
            showNotification(notification, message, "Список обновлен");
            return;
        }
        
        // Попытка 3: Обновить через renderer
        if (controller.renderer && controller.renderer.reload) {
            console.log("Using controller.renderer.reload() - 3");
            await controller.renderer.reload();
            showNotification(notification, message, "Список обновлен");
            return;
        }
        
        // Попытка 4: Принудительное обновление через action service
        console.log("Using action service reload - 4");
        const currentAction = controller.action;
        if (currentAction) {
            await env.services.action.doAction(currentAction, {
                clearBreadcrumbs: false,
                replace: true,
            });
            showNotification(notification, message, "Список обновлен");
            return;
        }
        
    } catch (error) {
        console.error("Error in handleListViewUpdate:", error);
    }
    
    // Последний вариант - показать уведомление о необходимости ручного обновления
    notification.add("Данные изменились. Обновите страницу для просмотра изменений.", {
        type: 'info',
        sticky: false,
    });
}

async function handleFormViewUpdate(controller, message, env, notification, orm) {
    console.log("Handling form view update");
    
    try {
        // Проверяем, редактируется ли текущая запись
        const currentRecordId = controller.model?.root?.resId || 
                               controller.props?.resId ||
                               controller.resId;
        
        if (currentRecordId && message.record_id && currentRecordId === message.record_id) {
            // Это та же запись, которая сейчас открыта
            if (message.type === 'delete') {
                notification.add("Эта запись была удалена другим пользователем", {
                    type: 'warning',
                    sticky: true,
                });
                // Можно закрыть форму или перенаправить
                await env.services.action.doAction({ type: 'ir.actions.act_window_close' });
                return;
            }
            
            // Обновляем форму
            if (controller.model && controller.model.load) {
                await controller.model.load();
                showNotification(notification, message, "Форма обновлена");
                return;
            }
            
            if (controller.reload) {
                await controller.reload();
                showNotification(notification, message, "Форма обновлена");
                return;
            }
        }
        
        // Если это не та же запись, показываем общее уведомление
        showNotification(notification, message, "Данные модели обновлены");
        
    } catch (error) {
        console.error("Error in handleFormViewUpdate:", error);
        notification.add("Ошибка при обновлении формы", { type: 'danger' });
    }
}

async function handleKanbanViewUpdate(controller, message, env, notification, orm) {
    console.log("Handling kanban view update");
    
    try {
        if (controller.reload) {
            await controller.reload();
            showNotification(notification, message, "Канбан обновлен");
            return;
        }
        
        if (controller.model && controller.model.load) {
            await controller.model.load();
            showNotification(notification, message, "Канбан обновлен");
            return;
        }
        
    } catch (error) {
        console.error("Error in handleKanbanViewUpdate:", error);
    }
    
    showNotification(notification, message, "Данные канбан-доски обновлены");
}

async function fallbackReload(controller, message, notification) {
    console.log("Using fallback reload method");
    
    // Последний вариант - полная перезагрузка
    notification.add("Данные изменились. Страница будет обновлена.", {
        type: 'info',
        sticky: false,
    });
    
    setTimeout(() => {
        browser.location.reload();
    }, 3000);
}

function showNotification(notification, message, defaultText) {
    const actionText = {
        'create': 'добавлена',
        'update': 'обновлена', 
        'delete': 'удалена'
    }[message.type] || 'изменена';
    
    const text = `Запись ${actionText} в модели ${message.model}`;
    
    notification.add(text, {
        type: 'info',
        sticky: false,
        duration: 3000,
    });
}

// Дополнительный сервис для подписки на конкретные модели
const modelSubscriptionService = {
    dependencies: ["bus_service", "amanat_real_time"],
    
    start(env) {
        return {
            subscribeToModel(model, callback) {
                // Подписываемся на обновления конкретной модели
                env.services.bus_service.subscribe(`model_${model}`, callback);
            },
            
            unsubscribeFromModel(model, callback) {
                // Отписываемся от обновлений модели
                env.services.bus_service.unsubscribe(`model_${model}`, callback);
            }
        };
    }
};

// Регистрируем оба сервиса
registry.category("services").add("amanat_real_time", amanatRealTimeService);
registry.category("services").add("model_subscription", modelSubscriptionService);

export default amanatRealTimeService;















































// /** @odoo-module **/

// import { registry } from "@web/core/registry";
// import { browser } from "@web/core/browser/browser";
// import { makeContext } from "@web/core/context";

// const amanatRealTimeService = {
//     dependencies: ["bus_service", "action", "notification", "orm"],

//     start(env, { notification, orm }) {
//         const busService = env.services.bus_service;
//         const actionService = env.services.action;
        
//         // Получаем текущего пользователя через orm или env
//         let currentUserId = null;
        
//         // Попробуем получить ID пользователя разными способами
//         if (env.services.user) {
//             currentUserId = env.services.user.userId;
//         } else if (odoo && odoo.session_info) {
//             currentUserId = odoo.session_info.uid;
//         } else {
//             // Запросим через ORM как fallback
//             orm.call("res.users", "read", [[]], { fields: ["id"] })
//                 .then(users => {
//                     if (users && users.length > 0) {
//                         currentUserId = users[0].id;
//                     }
//                 })
//                 .catch(error => {
//                     console.error("Failed to get current user ID:", error);
//                 });
//         }

//         console.log("Amanat RealTime Service starting...");
//         console.log("Current user ID:", currentUserId);

//         // Подписываемся на канал для real-time обновлений
//         busService.subscribe("realtime_updates", async (message) => {
//             console.log("Received realtime message:", message);

//             if (!['create', 'update', 'delete'].includes(message.type)) {
//                 return;
//             }

//             // Проверяем, не является ли текущий пользователь инициатором изменения
//             if (message.user_id && message.user_id === currentUserId) {
//                 console.log("Skipping notification - current user is the initiator");
//                 return;
//             }

//             try {
//                 await handleRealtimeUpdate(message, env, notification, orm);
//             } catch (error) {
//                 console.error("Error handling realtime update:", error);
//             }
//         });

//         console.log("Amanat RealTime Service started successfully");
//         return {
//             getCurrentUserId: () => currentUserId
//         };
//     },
// };

// async function handleRealtimeUpdate(message, env, notification, orm) {
//     const currentController = env.services.action.currentController;

//     if (!currentController || !currentController.action) {
//         console.log("No current controller or action");
//         return;
//     }

//     const currentModel = currentController.action.res_model;
//     console.log("Current model:", currentModel);
//     console.log("Message model:", message.model);

//     if (currentModel !== message.model) {
//         console.log("Models don't match, skipping update");
//         return;
//     }

//     // Определяем тип текущего представления
//     const viewType = currentController.action.view_mode ||
//         currentController.props?.type ||
//         currentController.viewType;

//     console.log("Current view type:", viewType);

//     // Показываем уведомление с кнопкой обновления вместо автоматического обновления
//     showUpdateNotification(notification, message, currentController, env);
// }

// function showUpdateNotification(notification, message, controller, env) {
//     const actionText = {
//         'create': 'добавлена',
//         'update': 'обновлена',
//         'delete': 'удалена'
//     }[message.type] || 'изменена';

//     const modelName = message.model_display_name || message.model;
//     const text = `Запись ${actionText} в модели "${modelName}"`;

//     // Создаем уведомление с кнопкой обновления
//     const notificationId = notification.add(text, {
//         type: 'info',
//         sticky: true, // Делаем уведомление постоянным до действия пользователя
//         buttons: [
//             {
//                 name: "Обновить",
//                 primary: true,
//                 onClick: async () => {
//                     try {
//                         await refreshCurrentView(controller, env);
//                         notification.close(notificationId);
//                     } catch (error) {
//                         console.error("Error refreshing view:", error);
//                         notification.add("Ошибка при обновлении. Попробуйте обновить страницу.", {
//                             type: 'warning'
//                         });
//                     }
//                 }
//             },
//             {
//                 name: "Отложить",
//                 onClick: () => {
//                     notification.close(notificationId);
//                     // Показываем менее навязчивое уведомление
//                     notification.add("Обновление отложено. Данные могут быть неактуальными.", {
//                         type: 'info',
//                         duration: 3000
//                     });
//                 }
//             }
//         ]
//     });
// }

// async function refreshCurrentView(controller, env) {
//     console.log("Refreshing current view");

//     const viewType = controller.action.view_mode ||
//         controller.props?.type ||
//         controller.viewType;

//     try {
//         switch (viewType) {
//             case 'list':
//             case 'tree':
//                 await refreshListView(controller, env);
//                 break;

//             case 'form':
//                 await refreshFormView(controller, env);
//                 break;

//             case 'kanban':
//                 await refreshKanbanView(controller, env);
//                 break;

//             default:
//                 await refreshGenericView(controller, env);
//         }

//         // Показываем подтверждение успешного обновления
//         env.services.notification.add("Данные успешно обновлены", {
//             type: 'success',
//             duration: 2000
//         });

//     } catch (error) {
//         console.error("Error refreshing view:", error);
//         throw error;
//     }
// }

// async function refreshListView(controller, env) {
//     console.log("Refreshing list view");

//     // Попытка 1: Использовать метод reload если он доступен
//     if (controller.reload && typeof controller.reload === 'function') {
//         console.log("Using controller.reload()");
//         await controller.reload();
//         return;
//     }

//     // Попытка 2: Обновить через модель списка
//     if (controller.model && controller.model.load) {
//         console.log("Using controller.model.load()");
//         await controller.model.load();
//         return;
//     }

//     // Попытка 3: Обновить через renderer
//     if (controller.renderer && controller.renderer.reload) {
//         console.log("Using controller.renderer.reload()");
//         await controller.renderer.reload();
//         return;
//     }

//     // Попытка 4: Принудительное обновление через action service
//     console.log("Using action service reload");
//     const currentAction = controller.action;
//     if (currentAction) {
//         await env.services.action.doAction(currentAction, {
//             clearBreadcrumbs: false,
//             replace: true,
//         });
//         return;
//     }

//     throw new Error("No suitable refresh method found for list view");
// }

// async function refreshFormView(controller, env) {
//     console.log("Refreshing form view");

//     // Обновляем форму
//     if (controller.model && controller.model.load) {
//         await controller.model.load();
//         return;
//     }

//     if (controller.reload) {
//         await controller.reload();
//         return;
//     }

//     throw new Error("No suitable refresh method found for form view");
// }

// async function refreshKanbanView(controller, env) {
//     console.log("Refreshing kanban view");

//     if (controller.reload) {
//         await controller.reload();
//         return;
//     }

//     if (controller.model && controller.model.load) {
//         await controller.model.load();
//         return;
//     }

//     throw new Error("No suitable refresh method found for kanban view");
// }

// async function refreshGenericView(controller, env) {
//     console.log("Refreshing generic view");

//     // Попробуем общие методы обновления
//     if (controller.reload) {
//         await controller.reload();
//         return;
//     }

//     if (controller.model && controller.model.load) {
//         await controller.model.load();
//         return;
//     }

//     // Последний вариант - перезагрузка через action service
//     const currentAction = controller.action;
//     if (currentAction) {
//         await env.services.action.doAction(currentAction, {
//             clearBreadcrumbs: false,
//             replace: true,
//         });
//         return;
//     }

//     throw new Error("No suitable refresh method found");
// }

// // Дополнительный сервис для подписки на конкретные модели
// const modelSubscriptionService = {
//     dependencies: ["bus_service", "amanat_real_time"],

//     start(env) {
//         return {
//             subscribeToModel(model, callback) {
//                 // Подписываемся на обновления конкретной модели
//                 env.services.bus_service.subscribe(`model_${model}`, callback);
//             },

//             unsubscribeFromModel(model, callback) {
//                 // Отписываемся от обновлений модели
//                 env.services.bus_service.unsubscribe(`model_${model}`, callback);
//             },

//             // Метод для ручного обновления конкретной модели
//             async refreshModel(model) {
//                 const currentController = env.services.action.currentController;
//                 if (currentController && currentController.action.res_model === model) {
//                     await refreshCurrentView(currentController, env);
//                 }
//             }
//         };
//     }
// };

// // Регистрируем оба сервиса
// registry.category("services").add("amanat_real_time", amanatRealTimeService);
// registry.category("services").add("model_subscription", modelSubscriptionService);

// export default amanatRealTimeService;
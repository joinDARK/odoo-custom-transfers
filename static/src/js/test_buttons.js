/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

// Простой компонент с кнопками тестирования
class TestRealtimeButtons extends Component {
    static template = "amanat.TestRealtimeButtons";
    
    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
    }
    
    async testBusMessage() {
        try {
            console.log("🧪 Testing bus message...");
            
            const result = await this.rpc("/amanat/test_bus", {});
            
            console.log("🧪 Bus test result:", result);
            
            if (result.success) {
                this.notification.add("Bus test message sent!", {
                    type: "success",
                });
            } else {
                this.notification.add(`Bus test failed: ${result.error}`, {
                    type: "danger",
                });
            }
        } catch (error) {
            console.error("🧪 Bus test error:", error);
            this.notification.add(`Bus test error: ${error.message}`, {
                type: "danger",
            });
        }
    }
    
    async testRealtimeUpdate() {
        try {
            console.log("🧪 Testing realtime update...");
            
            // Создаем тестовую запись в модели transfer
            const result = await this.rpc("/web/dataset/call_kw", {
                model: "amanat.transfer",
                method: "create",
                args: [{
                    name: `Test Transfer ${new Date().getTime()}`,
                    amount: 100.0,
                }],
                kwargs: {}
            });
            
            console.log("🧪 Test record created:", result);
            
            this.notification.add("Test record created! Check console for real-time updates.", {
                type: "success",
            });
            
        } catch (error) {
            console.error("🧪 Realtime test error:", error);
            this.notification.add(`Realtime test error: ${error.message}`, {
                type: "danger",
            });
        }
    }
}

// Регистрируем глобальные функции для тестирования из консоли
window.testAmanatBus = async function() {
    try {
        const response = await fetch('/amanat/test_bus', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {},
                id: Math.floor(Math.random() * 1000)
            })
        });
        
        const result = await response.json();
        console.log("🧪 Bus test from console:", result);
        return result;
    } catch (error) {
        console.error("🧪 Console bus test error:", error);
        return { success: false, error: error.message };
    }
};

window.testAmanatRealtime = async function() {
    try {
        const response = await fetch('/web/dataset/call_kw', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    model: "amanat.transfer",
                    method: "create",
                    args: [{
                        name: `Console Test ${new Date().getTime()}`,
                        amount: 999.0,
                    }],
                    kwargs: {}
                },
                id: Math.floor(Math.random() * 1000)
            })
        });
        
        const result = await response.json();
        console.log("🧪 Realtime test from console:", result);
        return result;
    } catch (error) {
        console.error("🧪 Console realtime test error:", error);
        return { success: false, error: error.message };
    }
};

console.log("🧪 Test functions registered:");
console.log("🧪 Use testAmanatBus() to test bus messages");
console.log("🧪 Use testAmanatRealtime() to test realtime updates");

// Тестовые функции для отладки real-time системы
const testButtonsService = {
    dependencies: ["bus_service", "notification"],
    
    start(env, { bus_service, notification }) {
        console.log("🧪 Test Buttons Service starting...");
        
        // Добавляем глобальные тестовые функции
        window.amanatTest = {
            // Тест 1: Простая отправка bus сообщения
            sendTestBusMessage: () => {
                console.log("🧪 TEST: Sending test bus message");
                try {
                    const testMessage = {
                        type: 'test',
                        message: 'Hello from frontend!',
                        timestamp: new Date().toISOString()
                    };
                    
                    // Получаем ID пользователя
                    const userId = window.odoo?.session_info?.uid || 2;
                    const userChannel = `res.users,${userId}`;
                    
                    console.log(`🧪 TEST: Sending to channel ${userChannel}:`, testMessage);
                    
                    // Отправляем сообщение через bus
                    bus_service.trigger('test_message', testMessage);
                    
                    notification.add("Тестовое сообщение отправлено!", {
                        type: "success",
                        title: "Тест Bus"
                    });
                } catch (error) {
                    console.error("🧪 TEST ERROR:", error);
                    notification.add(`Ошибка: ${error.message}`, {
                        type: "danger",
                        title: "Ошибка теста"
                    });
                }
            },
            
            // Тест 2: Проверка подписок на каналы
            checkBusSubscriptions: () => {
                console.log("🧪 TEST: Checking bus subscriptions");
                console.log("🧪 TEST: Bus service:", bus_service);
                console.log("🧪 TEST: Current user ID:", window.odoo?.session_info?.uid);
                
                // Выводим информацию о bus сервисе
                if (bus_service) {
                    console.log("🧪 TEST: Bus service available");
                    console.log("🧪 TEST: Bus service methods:", Object.getOwnPropertyNames(bus_service));
                } else {
                    console.error("🧪 TEST: Bus service not available!");
                }
                
                notification.add("Проверка выполнена - смотрите консоль", {
                    type: "info",
                    title: "Проверка Bus"
                });
            },
            
            // Тест 3: Вызов тестового контроллера
            callTestController: async () => {
                console.log("🧪 TEST: Calling test controller");
                try {
                    const response = await fetch('/amanat/test_bus', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            jsonrpc: "2.0",
                            method: "call",
                            params: {},
                            id: new Date().getTime(),
                        }),
                    });
                    
                    const data = await response.json();
                    console.log("🧪 TEST: Controller response:", data);
                    
                    if (data.result?.success) {
                        notification.add("Контроллер вызван успешно!", {
                            type: "success",
                            title: "Тест контроллера"
                        });
                    } else {
                        notification.add(`Ошибка контроллера: ${data.result?.error}`, {
                            type: "warning",
                            title: "Тест контроллера"
                        });
                    }
                } catch (error) {
                    console.error("🧪 TEST: Controller call error:", error);
                    notification.add(`Ошибка вызова: ${error.message}`, {
                        type: "danger",
                        title: "Ошибка контроллера"
                    });
                }
            },
            
            // Тест 4: Прямая подписка на личный канал
            subscribeDirectly: () => {
                console.log("🧪 TEST: Direct subscription test");
                const userId = window.odoo?.session_info?.uid || 2;
                const userChannel = `res.users,${userId}`;
                
                console.log(`🧪 TEST: Subscribing directly to ${userChannel}`);
                
                try {
                    bus_service.addChannel(userChannel);
                    console.log(`�� TEST: Successfully subscribed to ${userChannel}`);
                    
                    notification.add(`Подписан на канал ${userChannel}`, {
                        type: "success",
                        title: "Прямая подписка"
                    });
                } catch (error) {
                    console.error("🧪 TEST: Direct subscription error:", error);
                    notification.add(`Ошибка подписки: ${error.message}`, {
                        type: "danger",
                        title: "Ошибка подписки"
                    });
                }
            }
        };
        
        console.log("🧪 Test functions available at window.amanatTest");
        console.log("🧪 Available tests:", Object.keys(window.amanatTest));
        
        return {};
    }
};

// Регистрируем сервис
registry.category("services").add("test_buttons", testButtonsService);

console.log("🧪 Test Buttons Service registered"); 
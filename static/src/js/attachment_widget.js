/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useX2ManyCrud } from "@web/views/fields/relational_utils";
import { Component } from "@odoo/owl";
import { AmanatFileInput } from "./file_input";

export class AmanatAttachmentWidget extends Component {
    static template = "amanat.AttachmentWidget";
    static components = { AmanatFileInput };
    static props = {
        ...standardFieldProps,
    };
    
    get acceptedFileExtensions() {
        return this.props.options?.accepted_file_extensions || "*";
    }

    showNotification(message, type = "info") {
        if (this.notification && this.notification.add) {
            this.notification.add(message, { type });
        } else {
            // Fallback: используем console или глобальные уведомления
            const icon = type === "success" ? "✅" : type === "danger" ? "❌" : "ℹ️";
            console.log(`${icon} ${message}`);
            
            // Попробуем использовать глобальный объект, если доступен
            if (window.odoo && window.odoo.services && window.odoo.services.notification) {
                window.odoo.services.notification.add(message, { type });
            }
        }
    }

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        try {
            this.notification = useService("notification");
        } catch (e) {
            console.warn("Notification service not available:", e);
            this.notification = null;
        }
        this.ops = useX2ManyCrud(() => this.props.record.data[this.props.name], true);
        
        // Привязываем контекст методов, чтобы избежать потери this
        this.onUpload = this.onUpload.bind(this);
        this.remove = this.remove.bind(this);
        this.onRemoveClick = this.onRemoveClick.bind(this);
        this.onSearchRelatedClick = this.onSearchRelatedClick.bind(this);
        this.url = this.url.bind(this);
    }

    get files() {
        return this.props.record.data[this.props.name].records.map(r => {
            const data = { ...r.data, id: r.resId };
            // Извлекаем расширение из имени файла
            if (data.name) {
                const parts = data.name.split('.');
                data.extension = parts.length > 1 ? parts[parts.length - 1].toLowerCase() : '';
            }
            return data;
        });
    }

    url(id) { return `/web/content/${id}?download=true`; }

    async onUpload(res, files) {
        try {
            console.log("onUpload called with:", res);
            
            for (const attachment of res) {
                // Добавляем ID вложения к связанным записям Many2many поля
                await this.ops.saveRecord([attachment.id]);
            }
            
            // Если это поле assignment_attachments, запускаем автоматизацию
            if (this.props.name === 'assignment_attachments') {
                console.log("Triggering auto-signing for assignment_attachments");
                try {
                    // Вызываем метод автоматизации (только если есть текст Субагент/Subagent)
                    await this.orm.call(
                        this.props.record.resModel,
                        'auto_sign_assignment_with_stellar',
                        [this.props.record.resId]
                    );
                    console.log("Auto-signing triggered successfully");
                } catch (autoSignError) {
                    console.error("Auto-signing error:", autoSignError);
                    // Не показываем ошибку пользователю, так как файл уже загружен
                }
            }
            
            this.showNotification(_t(`${files.length} file(s) uploaded successfully`), "success");
        } catch (error) {
            console.error("Upload error in onUpload:", error);
            this.showNotification(_t("Upload failed: " + (error.message || error)), "danger");
        }
    }

    onRemoveClick(event) {
        const fileId = parseInt(event.currentTarget.dataset.fileId);
        console.log("onRemoveClick called with fileId:", fileId);
        if (fileId) {
            this.remove(fileId);
        } else {
            console.error("No fileId found in dataset:", event.currentTarget.dataset);
        }
    }

    async remove(id) {
        try {
            console.log("remove called with id:", id);
            const rec = this.props.record.data[this.props.name].records.find(r => r.resId === id);
            console.log("Found record:", rec);
            
            if (rec) {
                await this.ops.removeRecord(rec);
                this.showNotification(_t("File removed successfully"), "success");
            } else {
                console.error("Record not found for id:", id);
                this.showNotification(_t("File not found"), "danger");
            }
        } catch (error) {
            console.error("Error removing file:", error);
            this.showNotification(_t("Failed to remove file: " + (error.message || error)), "danger");
        }
    }

    async onSearchRelatedClick(event) {
        const attachmentId = parseInt(event.currentTarget.dataset.attachmentId);
        console.log("=== SEARCH RELATED ZAYAVKAS DEBUG ===");
        console.log("Field name:", this.props.name);
        console.log("Attachment ID:", attachmentId);
        console.log("Record ID:", this.props.record.resId);
        console.log("Record model:", this.props.record.resModel);
        
        // Попробуем найти информацию о файле
        const file = this.files.find(f => f.id === attachmentId);
        if (file) {
            console.log("File info:", file);
        } else {
            console.log("File not found in current files list");
        }
        
        if (!attachmentId) {
            console.error("No attachmentId found in dataset:", event.currentTarget.dataset);
            this.showNotification(_t("Ошибка: ID документа не найден"), "danger");
            return;
        }

        try {
            // Определяем, какой метод использовать в зависимости от поля
            let methodName;
            let methodArgs;
            let methodKwargs;
            
            // Для ВСЕХ полей используем универсальный поиск по attachment ID
            methodName = 'action_show_related_zayavkas_by_attachment';
            methodArgs = []; // Статический метод
            methodKwargs = {attachment_id: attachmentId};
            console.log("Using UNIVERSAL ATTACHMENT method for field:", this.props.name);
            
            // Логируем детали вызова
            console.log("=== CALLING SERVER METHOD ===");
            console.log("Method name:", methodName);
            console.log("Method args:", methodArgs); 
            console.log("Method kwargs:", methodKwargs);
            console.log("All files in current widget:", this.files);
            console.log("============================");
            
            // Вызываем выбранный метод
            const result = await this.orm.call(
                'amanat.zayavka',
                methodName,
                methodArgs,
                methodKwargs
            );
            
            // Выполняем полученный action
            console.log("=== RESULT FROM SERVER ===");
            console.log("Result:", result);
            console.log("Result type:", result?.type);
            console.log("Result name:", result?.name);
            console.log("Result domain:", result?.domain);
            console.log("=========================");
            
            if (result && result.type === 'ir.actions.act_window') {
                // Проверяем наличие необходимых полей
                if (!result.views) {
                    console.warn("Action result missing 'views' field, adding default views");
                    result.views = [[false, 'list'], [false, 'form']];
                }
                if (!result.res_model) {
                    console.error("Action result missing 'res_model' field");
                    this.showNotification(_t("Ошибка: неверная структура действия"), "danger");
                    return;
                }
                
                // Открываем новое окно со списком заявок
                await this.action.doAction(result);
                console.log("Action executed successfully");
                
                // Показываем успешное уведомление
                const fileName = file ? file.name : `ID${attachmentId}`;
                const foundCount = result.domain && result.domain[0] && result.domain[0][2] ? result.domain[0][2].length : 0;
                this.showNotification(`Найдено ${foundCount} заявок с документом "${fileName}"`, "success");
            } else if (result && result.type === 'ir.actions.client') {
                // Показываем уведомление
                if (result.params && result.params.message) {
                    this.showNotification(result.params.message, result.params.type || 'info');
                }
            } else {
                console.error("Unexpected result format:", result);
                this.showNotification(_t("Получен неожиданный результат от сервера"), "warning");
            }
            
        } catch (error) {
            console.error("Error searching related zayavkas:", error);
            
            // Разбираем различные типы ошибок для более понятного сообщения
            let errorMessage = "Ошибка при поиске связанных заявок";
            
            if (error.message) {
                if (error.message.includes("action.views is undefined")) {
                    errorMessage = "Ошибка в структуре ответа сервера. Обратитесь к администратору.";
                } else if (error.message.includes("NetworkError")) {
                    errorMessage = "Ошибка сети. Проверьте подключение к интернету.";
                } else if (error.message.includes("Permission")) {
                    errorMessage = "Недостаточно прав для выполнения операции.";
                } else {
                    errorMessage += ": " + error.message;
                }
            } else if (error.data && error.data.message) {
                errorMessage += ": " + error.data.message;
            } else {
                errorMessage += ". Попробуйте еще раз или обратитесь к администратору.";
            }
            
            this.showNotification(_t(errorMessage), "danger");
        }
    }
}

registry.category("fields").add("amanat_attachment", {
    component: AmanatAttachmentWidget,
    supportedTypes: ["many2many"],
    relatedFields: [
        { name: "name", type: "char" },
        { name: "mimetype", type: "char" },
    ],
});

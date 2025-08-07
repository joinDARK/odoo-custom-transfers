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
        this.url = this.url.bind(this);
    }

    get files() {
        return this.props.record.data[this.props.name].records.map(r => ({ ...r.data, id: r.resId }));
    }

    url(id) { return `/web/content/${id}?download=true`; }

    async onUpload(res, files) {
        try {
            console.log("onUpload called with:", res);
            
            for (const attachment of res) {
                // Добавляем ID вложения к связанным записям Many2many поля
                await this.ops.saveRecord([attachment.id]);
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
}

registry.category("fields").add("amanat_attachment", {
    component: AmanatAttachmentWidget,
    supportedTypes: ["many2many"],
    relatedFields: [
        { name: "name", type: "char" },
        { name: "mimetype", type: "char" },
    ],
});

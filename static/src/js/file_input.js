/** @odoo-module **/

import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class AmanatFileInput extends Component {
    static template = "amanat.FileInput";
    static defaultProps = {
        acceptedFileExtensions: "*",
        multiUpload: true,
        onUpload: () => {},
    };
    static props = {
        acceptedFileExtensions: { type: String, optional: true },
        multiUpload: { type: Boolean, optional: true },
        resId: { type: Number, optional: true },
        resModel: { type: String, optional: true },
        onUpload: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.fileInput = useRef("file-input");
        this.state = useState({ drag: false, uploading: false });
        onMounted(() => {
            const zone = this.fileInput.el.parentElement;
            zone.addEventListener("dragover", e => { 
                e.preventDefault(); 
                this.state.drag = true; 
            });
            zone.addEventListener("dragleave", e => { 
                e.preventDefault(); 
                this.state.drag = false; 
            });
            zone.addEventListener("drop", e => this._onDrop(e));
        });
    }

    async _onDrop(e) {
        e.preventDefault();
        this.state.drag = false;
        await this._upload(Array.from(e.dataTransfer.files));
    }

    async _upload(files) {
        if (this.state.uploading) return;
        
        try {
            this.state.uploading = true;
            console.log("Uploading files:", files);
            
            const results = [];
            
            for (const file of files) {
                const fileData = await this._fileToBase64(file);
                
                const [attachment] = await this.orm.create("ir.attachment", [{
                    name: file.name,
                    type: "binary",
                    datas: fileData,
                    res_model: this.props.resModel,
                    res_id: this.props.resId,
                    mimetype: file.type,
                }]);
                
                results.push({
                    id: attachment,
                    name: file.name,
                    mimetype: file.type,
                });
            }
            
            console.log("Upload results:", results);
            
            if (results.length && this.props.onUpload) {
                this.props.onUpload(results, files);
            }
        } catch (error) {
            console.error("Upload error in _upload:", error);
            throw error;
        } finally {
            this.state.uploading = false;
        }
    }

    _fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => {
                // Убираем префикс data:type;base64,
                const base64 = reader.result.split(',')[1];
                resolve(base64);
            };
            reader.onerror = error => reject(error);
        });
    }

    async onChange() {
        await this._upload(Array.from(this.fileInput.el.files));
        this.fileInput.el.value = "";
    }

    open() { 
        if (!this.state.uploading) {
            this.fileInput.el.click(); 
        }
    }
}

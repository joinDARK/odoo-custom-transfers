# -*- coding: utf-8 -*-
import io
import base64
from io import BytesIO

import pandas as pd
from docx import Document as DocxDocument
from odoo import api, fields, models


class IrAttachment(models.Model):
    """Extended Attachment Model for Amanat Sverka Files"""
    _inherit = 'ir.attachment'

    @api.model
    def decode_content(self, attach_id, doc_type):
        """Decode XLSX or DOC File Data.
        This method takes a binary file data from an attachment and decodes
        the content of the file for XLSX and DOC file formats.
        :param int attach_id: id of attachment.
        :param str doc_type: the type of the given attachment either 'xlsx' or
        'doc'
        :return: return the decoded data."""
        attachment = self.sudo().browse(attach_id)
        xlsx_data = base64.b64decode(attachment.datas)
        if doc_type in ['xlsx', 'xls', 'docx']:
            try:
                if doc_type == 'xlsx':
                    content = pd.read_excel(BytesIO(xlsx_data),
                                            engine='openpyxl',
                                            converters={'A': str})
                elif doc_type == 'xls':
                    content = pd.read_excel(BytesIO(xlsx_data), engine='xlrd',
                                            converters={'A': str})
                elif doc_type == 'docx':
                    doc = DocxDocument(io.BytesIO(xlsx_data))
                    paragraphs = [p.text for p in doc.paragraphs]
                    return paragraphs
                else:
                    raise ValueError("Unsupported file format")
                html_table = content.to_html(index=False)
                return html_table
            except TypeError:
                return ("<p style='padding-top:8px;color:red;'>"
                        "No preview available</p>")
        text = "Cant Preview"
        return text 
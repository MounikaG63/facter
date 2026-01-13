DOCUMENT_PICKER_TOOL = {
    "type": "function",
    "function": {
        "name": "pick_document",
        "description": "Select the most relevant document from the available documents and provide a friendly response",
        "parameters": {
            "type": "object",
            "properties": {
                "document_type": {
                    "type": "string",
                    "description": "Exact document key selected from documents object"
                },
                "document_url": {
                    "type": "string",
                    "description": "File path URL of the selected document"
                },
                "reply_message": {
                    "type": "string",
                    "description": "A friendly, natural response message to show the user along with the document"
                }
            },
            "required": ["document_type", "document_url", "reply_message"]
        }
    }
}

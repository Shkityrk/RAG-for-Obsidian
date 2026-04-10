interface VendorInfo {
    name: string,
    models: Array<string>
}


const VENDORS: Array<VendorInfo> = [
    {
        name: "GigaChat",
        models: [
            "GigaChat", "GigaChat-Pro", "GigaChat-Max"
        ]
    },
    {
        name: "Mistral AI",
        models: [
            "mistral-large-latest", "ministral-3b-latest", "ministral-8b-latest", 
            "mistral-small-latest", "codestral-latest"
        ]
    },
    {
        name: "Ollama",
        models: [
            "mistral-small3.2", "mistral-small3.2:latest", "mistral", "llama2", "llama3", "codellama", 
            "phi", "neural-chat", "starling-lm", "mistral-openorca", "dolphin-mixtral"
        ]
    }
]


export {VENDORS};
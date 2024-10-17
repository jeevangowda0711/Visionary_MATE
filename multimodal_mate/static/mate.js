document.addEventListener('DOMContentLoaded', () => {
    const fileUpload = document.getElementById('fileUpload');
    const uploadStatus = document.getElementById('uploadStatus');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const chatHistory = document.getElementById('chatHistory');

    fileUpload.addEventListener('change', async (event) => {
        const files = event.target.files;
        showUploadStatus('Uploading...');

        for (let file of files) {
            await handleFileUpload(file);
        }
    });

    async function handleFileUpload(file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/mate/upload', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            if (response.ok) {
                showUploadStatus(result.message);
                appendMessage('system', `File uploaded and processed: ${file.name}`);
            } else {
                console.error('Upload failed:', result.error);
                showUploadStatus(`Upload failed: ${result.error}`);
                appendMessage('system', `Upload failed: ${file.name} - ${result.error}`);
            }
        } catch (error) {
            console.error('Error:', error);
            showUploadStatus('Upload failed due to network error');
            appendMessage('system', `Upload failed: ${file.name} - Network error`);
        }
    }

    function showUploadStatus(message) {
        uploadStatus.textContent = message;
        uploadStatus.classList.remove('hidden');
        setTimeout(() => {
            uploadStatus.classList.add('hidden');
        }, 3000);
    }

    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    async function sendMessage() {
        const message = userInput.value.trim();
        const fileInput = document.getElementById('fileUpload');
        let fileData = null;
        let fileType = null;

        if (fileInput.files.length > 0) {
            const file = fileInput.files[0];
            fileType = file.type;
            
            if (fileType.startsWith('image/') || fileType.startsWith('audio/') || fileType.startsWith('video/')) {
                fileData = await fileToBase64(file);
            } else {
                await handleFileUpload(file);
                fileInput.value = '';
            }
        }

        if (message || fileData) {
            appendMessage('user', message, fileData);
            userInput.value = '';

            try {
                const response = await fetch('/mate/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ message, file: fileData, fileType })
                });
                const result = await response.json();
                if (response.ok) {
                    appendMessage('assistant', result.response, null, result.mode);
                } else {
                    console.error('Server error:', result);
                    appendMessage('assistant', `Error: ${result.error || 'Unknown error occurred'}`);
                }
            } catch (error) {
                console.error('Network error:', error);
                appendMessage('assistant', 'Sorry, an error occurred while processing your request.');
            }
        } else {
            appendMessage('assistant', 'Please enter a message or upload a file.');
        }
    }

    function appendMessage(sender, content, imageData = null, mode = null) {
        const messageElement = document.createElement('div');
        messageElement.className = `mb-4 ${sender === 'user' ? 'text-right' : 'text-left'}`;
        let bgColor = sender === 'user' ? 'bg-blue-600' : 'bg-gray-700';
        
        let formattedContent = content;
        if (sender === 'assistant') {
            formattedContent = marked.parse(content);
        }
        
        let modeIndicator = '';
        if (mode) {
            modeIndicator = `<span class="text-xs text-gray-400 ml-2">[${mode}]</span>`;
        }
        
        messageElement.innerHTML = `
            <div class="inline-block p-3 rounded-lg ${bgColor} max-w-full">
                <p class="text-sm text-gray-300 mb-1">${sender.charAt(0).toUpperCase() + sender.slice(1)}${modeIndicator}</p>
                <div class="text-white markdown-body message-content">${formattedContent}</div>
            </div>
        `;
        chatHistory.appendChild(messageElement);
        chatHistory.scrollTop = chatHistory.scrollHeight;

        messageElement.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightBlock(block);
        });

        if (imageData) {
            const imageElement = document.createElement('img');
            imageElement.src = `data:image/jpeg;base64,${imageData}`;
            imageElement.className = 'mt-2 rounded-lg max-w-full';
            messageElement.querySelector('.inline-block').appendChild(imageElement);
        }
    }

    function fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => resolve(reader.result.split(',')[1]);
            reader.onerror = error => reject(error);
        });
    }
});
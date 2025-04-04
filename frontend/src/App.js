// App.js
import React, { useRef, useState } from 'react';
import './styles/App.css';

import Sidebar from './components/Sidebar';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import LoadingIndicator from './components/LoadingIndicator';
import Modal from './components/Modal';

import useChat from './hooks/useChat';
import useDocuments from './hooks/useDocuments';

function App() {
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [urlModalOpen, setUrlModalOpen] = useState(false);
  const [urlInput, setUrlInput] = useState('');
  const [urlTitle, setUrlTitle] = useState('');
  const [fileTitle, setFileTitle] = useState('');
  const fileInputRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);

  const {
    messages,
    loading: chatLoading,
    input,
    setInput,
    sendMessage,
    addSystemMessage,
    messagesEndRef,
  } = useChat();

  const {
    documents,
    loading: documentsLoading,
    uploadFile,
    addUrl,
    deleteDocument,
  } = useDocuments();

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0] || event.dataTransfer?.files?.[0];
    if (!file) return;
    setSelectedFile(file);
  };

  const handleFileSubmit = async () => {
    if (!selectedFile) return;

    try {
      const result = await uploadFile(selectedFile, fileTitle);
      closeModals();
      addSystemMessage(`I've added "${result.title}" to my knowledge base. You can now ask questions about it!`);
    } catch (error) {
      alert(`Upload failed: ${error.message}`);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.add('dragging');
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.remove('dragging');
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.remove('dragging');
    handleFileUpload(e);
  };

  const handleUrlSubmit = async (e) => {
    e.preventDefault();
    if (!urlInput.trim()) return;

    try {
      const result = await addUrl(urlInput, urlTitle);
      closeModals();
      addSystemMessage(`I've added "${result.title}" to my knowledge base. You can now ask questions about it!`);
    } catch (error) {
      alert(`URL submission failed: ${error.message}`);
    }
  };

  const handleDeleteDocument = async (docId) => {
    // Find the document to get its title before deletion
    const documentToDelete = documents.find(doc => doc.id === docId);
    const documentTitle = documentToDelete ? documentToDelete.title : 'Unknown document';

    if (!window.confirm(`Are you sure you want to delete "${documentTitle}"?`)) {
      return;
    }

    try {
      await deleteDocument(docId);
      addSystemMessage(`I've removed "${documentTitle}" from my knowledge base.`);
    } catch (error) {
      alert(`Deletion failed: ${error.message}`);
    }
  };

  const openUploadModal = () => {
    setUrlModalOpen(false);
    setUploadModalOpen(true);
  };

  const openUrlModal = () => {
    setUploadModalOpen(false);
    setUrlModalOpen(true);
  };

  const closeModals = () => {
    setUploadModalOpen(false);
    setUrlModalOpen(false);
    setFileTitle('');
    setUrlInput('');
    setUrlTitle('');
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="app-container">
      <Sidebar
        documents={documents}
        onUpload={openUploadModal}
        onAddUrl={openUrlModal}
        onDeleteDocument={handleDeleteDocument}
      />

      <main className="chat-container">
        <div className="chat-header">
          <div className="header-content">
            <h1>NetBot</h1>
          </div>
        </div>

        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="welcome-message">
              <h1>Welcome to NetBot</h1>
              <p>Upload documents or add URLs to the knowledge base, then ask questions about them!</p>
            </div>
          ) : (
            <>
              {messages.map((message, index) => (
                <ChatMessage key={index} message={message} />
              ))}
              {chatLoading && <LoadingIndicator />}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        <ChatInput
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onSend={sendMessage}
          loading={chatLoading || documentsLoading}
        />
      </main>

      {/* File Upload Modal */}
      {uploadModalOpen && (
        <Modal title="Upload Document" onClose={closeModals}>
          <div className="modal-form">
            <div className="form-group">
              <label>Document Title (optional)</label>
              <input
                type="text"
                value={fileTitle}
                onChange={(e) => setFileTitle(e.target.value)}
                placeholder="Enter a title for this document"
              />
            </div>
            <div className="form-group">
              <label>Select File</label>
              <div
                className="file-input-container"
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <label className="file-input-label" htmlFor="file-upload">
                  <span>Choose a file or drag it here</span>
                </label>
                <input
                  id="file-upload"
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  accept=".pdf,.docx,.txt,.csv"
                />
                {(selectedFile || fileInputRef.current?.files[0]) && (
                  <div className="file-name">
                    Selected: {selectedFile?.name || fileInputRef.current?.files[0].name}
                  </div>
                )}
              </div>
            </div>
            <div className="modal-actions">
              <button type="button" onClick={closeModals}>Cancel</button>
              <button
                type="button"
                onClick={handleFileSubmit}
                disabled={!selectedFile}
              >
                Upload
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* URL Modal */}
      {urlModalOpen && (
        <Modal title="Add URL" onClose={closeModals}>
          <div className="modal-form">
            <div className="form-group">
              <label>Title (optional)</label>
              <input
                type="text"
                value={urlTitle}
                onChange={(e) => setUrlTitle(e.target.value)}
                placeholder="Enter a title for this URL"
              />
            </div>
            <div className="form-group">
              <label>URL</label>
              <input
                type="url"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="https://example.com"
                required
              />
            </div>
            <div className="modal-actions">
              <button type="button" onClick={closeModals}>Cancel</button>
              <button type="button" onClick={handleUrlSubmit} disabled={!urlInput.trim() || documentsLoading}>
                Add URL
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

export default App;
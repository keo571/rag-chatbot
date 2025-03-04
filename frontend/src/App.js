// App.js
import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { FiSend, FiUpload, FiLink, FiTrash2, FiInfo } from 'react-icons/fi';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [urlModalOpen, setUrlModalOpen] = useState(false);
  const [urlInput, setUrlInput] = useState('');
  const [urlTitle, setUrlTitle] = useState('');
  const [fileTitle, setFileTitle] = useState('');
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Fetch documents on component mount
  useEffect(() => {
    fetchDocuments();
  }, []);

  // Auto-scroll to the most recent message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchDocuments = async () => {
    try {
      const response = await fetch('http://localhost:8000/documents');
      const data = await response.json();
      setDocuments(data);
    } catch (error) {
      console.error('Error fetching documents:', error);
    }
  };

  const handleSendMessage = async () => {
    if (input.trim() === '') return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: input,
          history: messages.map(msg => ({
            role: msg.role,
            content: msg.content
          }))
        }),
      });

      const data = await response.json();
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        sources: data.sources
      }]);
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an error processing your request.'
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    if (fileTitle.trim()) {
      formData.append('title', fileTitle);
    }

    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/upload/file', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        console.log('File uploaded successfully:', result);
        await fetchDocuments();
        setUploadModalOpen(false);
        setFileTitle('');

        // Add system message about the upload
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: `I've added "${result.title}" to my knowledge base. You can now ask questions about it!`
          }
        ]);
      } else {
        const error = await response.json();
        console.error('Upload failed:', error);
        alert(`Upload failed: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      alert('Error uploading file.');
    } finally {
      setLoading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleUrlSubmit = async (e) => {
    e.preventDefault();
    if (!urlInput.trim()) return;

    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/upload/url', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: urlInput,
          title: urlTitle.trim() || null,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        console.log('URL added successfully:', result);
        await fetchDocuments();
        setUrlModalOpen(false);
        setUrlInput('');
        setUrlTitle('');

        // Add system message about the URL addition
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: `I've added "${result.title}" to my knowledge base. You can now ask questions about it!`
          }
        ]);
      } else {
        const error = await response.json();
        console.error('URL submission failed:', error);
        alert(`URL submission failed: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error submitting URL:', error);
      alert('Error submitting URL.');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteDocument = async (docId) => {
    if (!window.confirm('Are you sure you want to delete this document?')) {
      return;
    }

    try {
      const response = await fetch(`http://localhost:8000/documents/${docId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        await fetchDocuments();
        // Add system message about deletion
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: 'Document has been removed from my knowledge base.'
          }
        ]);
      } else {
        const error = await response.json();
        console.error('Deletion failed:', error);
        alert(`Deletion failed: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error deleting document:', error);
      alert('Error deleting document.');
    }
  };

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h2>Knowledge Base</h2>
          <div className="sidebar-actions">
            <button
              className="action-button"
              onClick={() => setUploadModalOpen(true)}
              title="Upload Document"
            >
              <FiUpload />
            </button>
            <button
              className="action-button"
              onClick={() => setUrlModalOpen(true)}
              title="Add URL"
            >
              <FiLink />
            </button>
          </div>
        </div>

        <div className="documents-list">
          {documents.length === 0 ? (
            <p className="no-documents">No documents added yet</p>
          ) : (
            documents.map(doc => (
              <div key={doc.id} className="document-item">
                <div className="document-info">
                  <span className="document-title">{doc.title}</span>
                  <span className="document-type">{doc.source_type}</span>
                </div>
                <button
                  className="delete-button"
                  onClick={() => handleDeleteDocument(doc.id)}
                  title="Delete Document"
                >
                  <FiTrash2 />
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      <main className="chat-container">
        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="welcome-message">
              <h1>RAG Chatbot</h1>
              <p>Upload documents or add URLs to the knowledge base, then ask questions about them!</p>
            </div>
          ) : (
            messages.map((message, index) => (
              <div key={index} className={`message ${message.role}`}>
                <div className="message-content">{message.content}</div>
                {message.sources && message.sources.length > 0 && (
                  <div className="sources-container">
                    <div className="sources-header">
                      <FiInfo /> Sources ({message.sources.length})
                    </div>
                    <div className="sources-list">
                      {message.sources.map((source, idx) => (
                        <div key={idx} className="source-item">
                          <div className="source-text">{source.text}</div>
                          <div className="source-metadata">
                            {Object.entries(source.metadata).map(([key, value], i) => (
                              <span key={i} className="metadata-item">
                                <strong>{key}:</strong> {value}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
          {loading && (
            <div className="message assistant">
              <div className="loading-indicator">
                <div className="loading-dot"></div>
                <div className="loading-dot"></div>
                <div className="loading-dot"></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-container">
          <input
            type="text"
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Ask a question..."
            disabled={loading}
          />
          <button
            className="send-button"
            onClick={handleSendMessage}
            disabled={loading || !input.trim()}
          >
            <FiSend />
          </button>
        </div>
      </main>

      {/* File Upload Modal */}
      {uploadModalOpen && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>Upload Document</h3>
            <div className="modal-form">
              <div className="form-group">
                <label>Document Title (optional):</label>
                <input
                  type="text"
                  value={fileTitle}
                  onChange={(e) => setFileTitle(e.target.value)}
                  placeholder="Enter a title for this document"
                />
              </div>
              <div className="form-group">
                <label>Select File:</label>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  accept=".pdf,.docx,.txt,.csv"
                />
              </div>
              <div className="modal-actions">
                <button onClick={() => setUploadModalOpen(false)}>Cancel</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* URL Modal */}
      {urlModalOpen && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>Add URL</h3>
            <form className="modal-form" onSubmit={handleUrlSubmit}>
              <div className="form-group">
                <label>URL:</label>
                <input
                  type="url"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="https://example.com"
                  required
                />
              </div>
              <div className="form-group">
                <label>Title (optional):</label>
                <input
                  type="text"
                  value={urlTitle}
                  onChange={(e) => setUrlTitle(e.target.value)}
                  placeholder="Enter a title for this URL"
                />
              </div>
              <div className="modal-actions">
                <button type="button" onClick={() => setUrlModalOpen(false)}>Cancel</button>
                <button type="submit" disabled={!urlInput.trim() || loading}>Add URL</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
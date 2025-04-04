import React from 'react';
import PropTypes from 'prop-types';
import { FiUpload, FiLink, FiTrash2 } from 'react-icons/fi';
import '../styles/Sidebar.css';

const Sidebar = ({ documents, onUpload, onAddUrl, onDeleteDocument }) => {
    const getDisplayTitle = (doc) => {
        // For URLs, just show the title
        if (doc.source_type === 'url') {
            return doc.title;
        }

        // For files
        // If there's a custom title, show "title (filename)"
        if (doc.title !== doc.source_path) {
            return `${doc.title} (${doc.source_path})`;
        }

        // If no custom title or title is same as filename, just show the filename
        return doc.source_path;
    };

    return (
        <aside className="sidebar">
            <div className="sidebar-header">
                <h2>Knowledge Base</h2>
                <div className="sidebar-actions">
                    <button
                        className="action-button"
                        onClick={onUpload}
                        title="Upload Document"
                    >
                        <FiUpload />
                        <span>Upload</span>
                    </button>
                    <button
                        className="action-button"
                        onClick={onAddUrl}
                        title="Add URL"
                    >
                        <FiLink />
                        <span>Add URL</span>
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
                                <span className="document-title">
                                    {getDisplayTitle(doc)}
                                </span>
                                <span className="document-type">
                                    {doc.source_type}
                                </span>
                            </div>
                            <button
                                className="delete-button"
                                onClick={() => onDeleteDocument(doc.id)}
                                title="Delete Document"
                            >
                                <FiTrash2 />
                            </button>
                        </div>
                    ))
                )}
            </div>
        </aside>
    );
};

Sidebar.propTypes = {
    documents: PropTypes.arrayOf(
        PropTypes.shape({
            id: PropTypes.string.isRequired,
            title: PropTypes.string.isRequired,
            source_type: PropTypes.string.isRequired,
            source_path: PropTypes.string.isRequired,
        })
    ).isRequired,
    onUpload: PropTypes.func.isRequired,
    onAddUrl: PropTypes.func.isRequired,
    onDeleteDocument: PropTypes.func.isRequired,
};

export default Sidebar; 
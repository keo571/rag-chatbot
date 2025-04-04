import React from 'react';
import PropTypes from 'prop-types';
import '../styles/ChatMessage.css';

const ChatMessage = ({ message }) => {
    const isUser = message.role === 'user';

    const renderSource = (source) => {
        const isUrl = source.source_type === 'url';
        const sourceUrl = isUrl ? source.source_path : null;

        return (
            <div className="source-item">
                <div className="source-header">
                    <div className="source-title">{source.title || "Untitled Source"}</div>
                    {sourceUrl && (
                        <a
                            href={sourceUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="source-link"
                        >
                            View Source
                        </a>
                    )}
                </div>
                <div className="source-text">{source.text}</div>
            </div>
        );
    };

    return (
        <div className={`message ${message.role}`}>
            <div className="message-content">
                {message.content}
            </div>
            {message.sources && message.sources.length > 0 && (
                <div className="sources-container">
                    <div className="sources-title">Sources:</div>
                    {message.sources.map((source, index) => (
                        <div key={index}>
                            {renderSource(source)}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

ChatMessage.propTypes = {
    message: PropTypes.shape({
        role: PropTypes.oneOf(['user', 'assistant']).isRequired,
        content: PropTypes.string.isRequired,
        sources: PropTypes.arrayOf(
            PropTypes.shape({
                text: PropTypes.string,
                title: PropTypes.string,
                source_type: PropTypes.string,
                source_path: PropTypes.string
            })
        )
    }).isRequired
};

export default ChatMessage; 
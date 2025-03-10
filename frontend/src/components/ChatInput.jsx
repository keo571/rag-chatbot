import React from 'react';
import PropTypes from 'prop-types';
import { FiSend } from 'react-icons/fi';
import '../styles/ChatInput.css';

const ChatInput = ({ value, onChange, onSend, loading }) => {
    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            onSend();
        }
    };

    return (
        <div className="input-container">
            <div className="input-wrapper">
                <textarea
                    className="message-input"
                    value={value}
                    onChange={onChange}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask a question..."
                    rows={1}
                    disabled={loading}
                />
                <button
                    className="send-button"
                    onClick={onSend}
                    disabled={loading || !value.trim()}
                >
                    <FiSend />
                </button>
            </div>
        </div>
    );
};

ChatInput.propTypes = {
    value: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
    onSend: PropTypes.func.isRequired,
    loading: PropTypes.bool.isRequired,
};

export default ChatInput; 
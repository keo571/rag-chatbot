import React from 'react';
import '../styles/LoadingIndicator.css';

const LoadingIndicator = () => (
    <div className="loading-indicator">
        Thinking
        <div className="loading-dots">
            <div className="dot"></div>
            <div className="dot"></div>
            <div className="dot"></div>
        </div>
    </div>
);

export default LoadingIndicator; 
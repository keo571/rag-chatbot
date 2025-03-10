import { useState, useRef, useEffect } from 'react';

const useChat = () => {
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(false);
    const [input, setInput] = useState('');
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const sendMessage = async () => {
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

    const addSystemMessage = (content) => {
        setMessages(prev => [
            ...prev,
            {
                role: 'assistant',
                content
            }
        ]);
    };

    return {
        messages,
        loading,
        input,
        setInput,
        sendMessage,
        addSystemMessage,
        messagesEndRef,
    };
};

export default useChat; 
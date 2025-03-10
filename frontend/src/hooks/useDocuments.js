import { useState, useEffect } from 'react';

const useDocuments = () => {
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(false);

    const fetchDocuments = async () => {
        try {
            const response = await fetch('http://localhost:8000/documents');
            const data = await response.json();
            setDocuments(data);
        } catch (error) {
            console.error('Error fetching documents:', error);
        }
    };

    const uploadFile = async (file, title) => {
        const formData = new FormData();
        formData.append('file', file);
        if (title?.trim()) {
            formData.append('title', title);
        }

        try {
            setLoading(true);
            const response = await fetch('http://localhost:8000/documents/upload/file', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail);
            }

            const result = await response.json();
            await fetchDocuments();
            return result;
        } finally {
            setLoading(false);
        }
    };

    const addUrl = async (url, title) => {
        try {
            setLoading(true);
            const response = await fetch('http://localhost:8000/documents/upload/url', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url,
                    title: title?.trim() || null,
                }),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail);
            }

            const result = await response.json();
            await fetchDocuments();
            return result;
        } finally {
            setLoading(false);
        }
    };

    const deleteDocument = async (docId) => {
        try {
            const response = await fetch(`http://localhost:8000/documents/${docId}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail);
            }

            await fetchDocuments();
            return true;
        } catch (error) {
            console.error('Error deleting document:', error);
            throw error;
        }
    };

    useEffect(() => {
        fetchDocuments();
    }, []);

    return {
        documents,
        loading,
        uploadFile,
        addUrl,
        deleteDocument,
    };
};

export default useDocuments; 
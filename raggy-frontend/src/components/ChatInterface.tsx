'use client';

import React, { useState, useRef, useEffect, FormEvent } from 'react';
import apiClient from '@/lib/apiClient';

// Define the ChatMessage interface
interface ChatMessage {
  sender: 'user' | 'raggy';
  text: string;
}

const ChatInterface: React.FC = () => {
  // State for the current input message
  const [input, setInput] = useState<string>('');
  
  // State for the conversation history
  const [history, setHistory] = useState<ChatMessage[]>([]);
  
  // State for loading status
  const [isLoading, setIsLoading] = useState<boolean>(false);
  
  // State for error handling
  const [error, setError] = useState<string | null>(null);
  
  // Ref for the chat container to enable auto-scrolling
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the bottom when new messages are added
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [history]);

  // Handle form submission
  const handleSendQuery = async (e: FormEvent) => {
    e.preventDefault();
    
    // Don't submit if input is empty or already loading
    if (!input.trim() || isLoading) return;
    
    // Create user message
    const userMessage: ChatMessage = { 
      sender: 'user', 
      text: input 
    };
    
    // Update history with user message
    setHistory(prev => [...prev, userMessage]);
    
    // Clear input and set loading state
    setInput('');
    setIsLoading(true);
    setError(null);
    
    try {
      // Make API request
      const response = await apiClient.post('/query', { 
        query: userMessage.text 
      });
      
      // Create Raggy message from response
      const raggyMessage: ChatMessage = { 
        sender: 'raggy', 
        text: response.data.answer || "Sorry, I couldn't get a response." 
      };
      
      // Update history with Raggy message
      setHistory(prev => [...prev, raggyMessage]);
    } catch (err: any) {
      console.error('Error sending query:', err);
      
      // Set error message
      setError(err.response?.data?.error || 'Failed to get response.');
      
      // Add error message to chat
      const errorMessage: ChatMessage = { 
        sender: 'raggy', 
        text: 'Sorry, an error occurred while processing your query.' 
      };
      
      setHistory(prev => [...prev, errorMessage]);
    } finally {
      // Reset loading state
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto p-4 bg-white rounded-lg shadow-md">
      {/* Chat history container */}
      <div 
        ref={chatContainerRef}
        className="flex-1 overflow-y-auto mb-4 p-4 border border-gray-200 rounded-lg"
        style={{ maxHeight: '60vh' }}
      >
        {history.length === 0 ? (
          <div className="text-center text-gray-500 my-8">
            <p>Start a conversation with Raggy!</p>
          </div>
        ) : (
          history.map((message, index) => (
            <div 
              key={index} 
              className={`mb-4 ${
                message.sender === 'user' 
                  ? 'flex justify-end' 
                  : 'flex justify-start'
              }`}
            >
              <div 
                className={`max-w-[80%] p-3 rounded-lg ${
                  message.sender === 'user' 
                    ? 'bg-blue-500 text-white rounded-br-lg' 
                    : 'bg-gray-200 text-gray-800 rounded-bl-lg'
                }`}
              >
                <p className="whitespace-pre-wrap">{message.text}</p>
              </div>
            </div>
          ))
        )}
        
        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start mb-4">
            <div className="bg-gray-200 text-gray-800 p-3 rounded-lg rounded-bl-lg">
              <p>Raggy is thinking...</p>
            </div>
          </div>
        )}
      </div>
      
      {/* Error message */}
      {error && (
        <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-lg">
          <p>{error}</p>
        </div>
      )}
      
      {/* Input form */}
      <form onSubmit={handleSendQuery} className="flex gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your question here..."
          className="flex-1 p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          rows={2}
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className={`px-4 py-2 rounded-lg font-medium ${
            isLoading || !input.trim()
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-blue-500 text-white hover:bg-blue-600'
          }`}
        >
          Send
        </button>
      </form>
    </div>
  );
};

export default ChatInterface; 
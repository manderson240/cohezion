import { useState, useRef, useEffect } from 'react';

interface Message {
  role: 'user' | 'assistant';
  text: string;
  audio_b64?: string;
  images_b64?: string[];
  tool_calls?: Array<{
    tool_name: string;
    arguments: string;
    artefact_kind: string;
  }>;
}

export default function AskOmni({ journeyId }: { journeyId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      role: 'user',
      text: input.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch(`/api/journey-nexus/omni/${journeyId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: userMessage.text }),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.json();

      const assistantMessage: Message = {
        role: 'assistant',
        text: data.text || '',
        audio_b64: data.audio_b64,
        images_b64: data.images_b64,
        tool_calls: data.tool_calls,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error fetching response:', error);
      // Optionally add an error message to the UI
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full max-h-[80vh] border rounded-lg shadow-sm bg-white">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                msg.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-200 text-gray-900'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.text}</p>

              {msg.audio_b64 && (
                <audio controls src={`data:audio/mpeg;base64,${msg.audio_b64}`} className="mt-2 w-full" />
              )}

              {msg.images_b64 && msg.images_b64.length > 0 && (
                <div className="mt-2 space-y-2">
                  {msg.images_b64.map((img, imgIndex) => (
                    // eslint-disable-next-line @next/next/no-img-element -- data: URI, no LCP impact
                    <img
                      key={imgIndex}
                      src={`data:image/png;base64,${img}`}
                      alt="Generated"
                      className="max-w-full rounded"
                    />
                  ))}
                </div>
              )}

              {msg.tool_calls && msg.tool_calls.length > 0 && (
                <details className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                  <summary className="cursor-pointer font-medium">Tool Calls</summary>
                  <ul className="mt-1 space-y-1 pl-4 list-disc">
                    {msg.tool_calls.map((tc, tcIndex) => (
                      <li key={tcIndex}>
                        <strong>{tc.tool_name}</strong>: {tc.arguments} ({tc.artefact_kind})
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-200 rounded-lg p-3">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-100"></div>
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-200"></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t bg-gray-50">
        <div className="flex space-x-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            className="flex-1 resize-none border rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={2}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

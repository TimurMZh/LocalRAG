import { useState, useRef, useEffect } from 'react';
import { Send, Bot, RefreshCw, Sparkles, FileText, ChevronDown, ChevronUp, Download } from 'lucide-react';

const ChatBubbleInterface = () => {
  const [conversation, setConversation] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [expandedSources, setExpandedSources] = useState({});
  const [selectedModel, setSelectedModel] = useState('openai'); // 'openai' или 'roberta'
  
  const messagesContainerRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  }, [conversation]);

  // Автоматическое изменение высоты текстового поля
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [inputValue]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!inputValue.trim() || isProcessing) return;
    
    const userMessage = {
      type: 'user',
      content: inputValue.trim(),
      timestamp: new Date().toISOString()
    };
    
    setConversation(prev => [...prev, userMessage]);
    setInputValue('');
    setIsProcessing(true);
    
    // Добавляем индикатор загрузки
    setConversation(prev => [...prev, { type: 'thinking' }]);
    
    try {
      const response = await fetch('http://localhost:8080/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: userMessage.content,
          model: selectedModel,
          history: conversation
            .filter(msg => msg.type !== 'thinking')
            .map(msg => ({
              role: msg.type === 'user' ? 'user' : 'assistant',
              content: msg.content
            }))
        }),
      });
      
      // Удаляем индикатор загрузки
      setConversation(prev => prev.filter(msg => msg.type !== 'thinking'));
      
      if (response.ok) {
        const data = await response.json();
        
        const aiMessage = {
          type: 'assistant',
          content: data.answer,
          timestamp: new Date().toISOString(),
          sources: data.sources || []
        };
        
        setConversation(prev => [...prev, aiMessage]);
      } else {
        const errorData = await response.text();
        setConversation(prev => [...prev, {
          type: 'error',
          content: `Произошла ошибка: ${errorData || 'Не удалось получить ответ'}`,
          timestamp: new Date().toISOString()
        }]);
      }
    } catch (error) {
      console.error('Ошибка при отправке запроса:', error);
      
      // Удаляем индикатор загрузки
      setConversation(prev => prev.filter(msg => msg.type !== 'thinking'));
      
      setConversation(prev => [...prev, {
        type: 'error',
        content: 'Ошибка соединения с сервером. Пожалуйста, проверьте ваше подключение к интернету.',
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleKeyDown = (e) => {
    // Отправка формы по Ctrl+Enter или Cmd+Enter
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      handleSubmit(e);
    }
  };

  const resetConversation = () => {
    if (window.confirm('Вы уверены, что хотите начать новый разговор?')) {
      setConversation([]);
    }
  };

  const toggleSourceExpansion = (messageIndex) => {
    setExpandedSources(prev => ({
      ...prev,
      [messageIndex]: !prev[messageIndex]
    }));
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const handleModelChange = (e) => {
    setSelectedModel(e.target.value);
    resetConversation();
  };

  return (
    <div className="flex flex-col h-[calc(100vh-6rem)] bg-gray-50">
      {/* Шапка чата */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-700 text-white shadow-md">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Bot className="h-6 w-6" />
            <h1 className="text-lg font-semibold">Ассистент по документам</h1>
          </div>
          
          <div className="flex items-center space-x-3">
            <div className="relative">
              <select
                id="model-select"
                value={selectedModel}
                onChange={handleModelChange}
                className="appearance-none bg-white text-blue-900 px-4 py-1.5 pr-8 rounded-md font-medium text-sm cursor-pointer hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-white/50"
              >
                <option value="openai">OpenAI</option>
                <option value="t5">T5</option>
              </select>
              <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none">
                <ChevronDown size={16} className="text-blue-900" />
              </div>
            </div>
            
            {conversation.length > 0 && (
              <button 
                className="p-1.5 rounded-full hover:bg-white/20 transition-colors"
                onClick={resetConversation}
                title="Начать новый разговор"
              >
                <RefreshCw size={18} />
              </button>
            )}
          </div>
        </div>
      </div>
      
      {/* Основная область чата */}
      <div 
        className="flex-1 overflow-y-auto p-4"
        ref={messagesContainerRef}
      >
        <div className="max-w-4xl mx-auto space-y-4">
        {conversation.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="bg-blue-100 text-blue-800 p-3 rounded-full mb-4">
              <Sparkles size={32} />
            </div>
            <h2 className="text-xl font-semibold text-gray-800 mb-2">
              Спросите меня о ваших документах
            </h2>
            <p className="text-gray-600 max-w-md">
              Я помогу найти информацию из ваших загруженных документов и отвечу на ваши вопросы.
            </p>
            <p className="text-sm mt-2 text-gray-500">
              Выбрана модель: {selectedModel === 'openai' ? 'OpenAI' : 'T5'}
            </p>
            <div className="mt-8 grid grid-cols-2 gap-3 max-w-lg">
              {["Что содержится в моих документах?", 
                "Найди информацию о...", 
                "Сравни данные из...", 
                "Объясни концепцию..."].map(suggestion => (
                  <button
                    key={suggestion}
                    className="p-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 text-left hover:bg-gray-50 shadow-sm"
                    onClick={() => setInputValue(suggestion)}
                  >
                    "{suggestion}"
                  </button>
                )
              )}
            </div>
          </div>
        ) : (
          <>
            {conversation.map((message, index) => {
              if (message.type === 'thinking') {
                return (
                  <div key="thinking" className="flex justify-start">
                    <div className="bg-white rounded-2xl rounded-tl-none border border-gray-200 shadow-sm px-4 py-3 inline-block max-w-3xl">
                      <div className="flex items-center space-x-2">
                        <div className="flex space-x-1">
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                        </div>
                        <span className="text-gray-500 text-sm">Думаю...</span>
                      </div>
                    </div>
                  </div>
                );
              }
              
              return (
                <div 
                  key={index} 
                  className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div 
                    className={`rounded-2xl px-4 py-3 inline-block max-w-3xl ${
                      message.type === 'user' 
                        ? 'bg-blue-600 text-white rounded-tr-none' 
                        : message.type === 'error'
                          ? 'bg-red-50 text-red-800 border border-red-200 rounded-tl-none'
                          : 'bg-white rounded-tl-none border border-gray-200 shadow-sm'
                    }`}
                  >
                    <div className="mb-1 flex items-center justify-between space-x-2">
                      <span className={`text-xs ${message.type === 'user' ? 'text-blue-200' : 'text-gray-500'}`}>
                        {message.type === 'user' ? 'Вы' : 'Ассистент'} • {formatTime(message.timestamp)}
                      </span>
                    </div>
                    
                    <div className="text-base whitespace-pre-wrap">
                      {message.content}
                    </div>
                    
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-3 pt-2 border-t border-gray-200">
                        <button 
                          className="flex items-center text-xs font-medium text-gray-600 hover:text-gray-900"
                          onClick={() => toggleSourceExpansion(index)}
                        >
                          <span>Источники ({message.sources.length})</span>
                          {expandedSources[index] 
                            ? <ChevronUp size={14} className="ml-1" />
                            : <ChevronDown size={14} className="ml-1" />
                          }
                        </button>
                        
                        {expandedSources[index] && (
                          <div className="mt-2 space-y-2">
                            {message.sources.map((source, sourceIdx) => (
                              <div key={sourceIdx} className="bg-gray-50 rounded-lg p-2 text-xs">
                                <div className="flex items-start">
                                  <FileText size={14} className="text-gray-500 mt-0.5 mr-1.5 flex-shrink-0" />
                                  <div>
                                    <div className="font-medium text-gray-900">
                                      {source.title || source.document_id || `Документ ${sourceIdx + 1}`}
                                    </div>
                                    {source.excerpt && (
                                      <div className="mt-1 text-gray-700">
                                        {source.excerpt}
                                      </div>
                                    )}
                                    {source.document_id && (
                                      <div className="mt-1 flex items-center">
                                        <button className="text-blue-600 hover:underline flex items-center">
                                          <Download size={12} className="mr-1" />
                                          <span>Скачать документ</span>
                                        </button>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </>
        )}
        </div>
      </div>
      
      {/* Форма ввода */}
      <div className="bg-white border-t border-gray-200 p-3">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSubmit} className="relative flex items-end rounded-lg border border-gray-300 bg-white focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500 overflow-hidden">
            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Задайте вопрос о ваших документах..."
              className="flex-grow pl-4 pr-12 py-3 max-h-32 min-h-[48px] resize-none overflow-auto focus:outline-none"
              rows={1}
              disabled={isProcessing}
            />
            
            <button
              type="submit"
              disabled={!inputValue.trim() || isProcessing}
              className={`absolute right-2 bottom-2 p-2 rounded-full ${
                !inputValue.trim() || isProcessing 
                  ? 'bg-gray-100 text-gray-400' 
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              } transition-colors duration-150`}
            >
              <Send size={18} className={isProcessing ? 'opacity-70' : ''} />
            </button>
          </form>
          
          <div className="mt-2 text-xs text-gray-500 text-center">
            <span>Нажмите Enter для новой строки или Ctrl+Enter для отправки</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatBubbleInterface;
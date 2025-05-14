import { useState } from 'react';
import { Search, FileText, BookOpen, FileCode, SortDesc, SortAsc, ArrowDown, ArrowUp, ExternalLink, ChevronDown } from 'lucide-react';

const DocumentSearchTable = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [sortField, setSortField] = useState('score');
  const [sortDirection, setSortDirection] = useState('desc'); // 'asc' или 'desc'
  const [expandedRows, setExpandedRows] = useState({});
  const [selectedModel, setSelectedModel] = useState('openai');

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsLoading(true);
    setHasSearched(true);
    setExpandedRows({});

    try {
      const response = await fetch('http://localhost:8080/documents/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: searchQuery,
          model: selectedModel
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setSearchResults(data.results || []);
      } else {
        console.error('Ошибка поиска:', await response.text());
        setSearchResults([]);
      }
    } catch (error) {
      console.error('Ошибка при выполнении запроса:', error);
      setSearchResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortResults = (results) => {
    return [...results].sort((a, b) => {
      let aValue, bValue;

      if (sortField === 'category') {
        aValue = a.category || '';
        bValue = b.category || '';
      } else if (sortField === 'created_at') {
        aValue = new Date(a.created_at || 0).getTime();
        bValue = new Date(b.created_at || 0).getTime();
      } else { // 'score'
        aValue = parseFloat(a.score) || 0;
        bValue = parseFloat(b.score) || 0;
      }

      if (typeof aValue === 'string') {
        const comparison = aValue.localeCompare(bValue);
        return sortDirection === 'asc' ? comparison : -comparison;
      } else {
        return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
      }
    });
  };

  const toggleRowExpansion = (id) => {
    setExpandedRows(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  const highlightMatches = (text, query) => {
    if (!query || !text) return text;
    
    const regex = new RegExp(`(${query.split(' ').join('|')})`, 'gi');
    const parts = text.split(regex);
    
    return parts.map((part, i) => 
      regex.test(part) ? <mark key={i} className="bg-yellow-200 px-0.5">{part}</mark> : part
    );
  };

  const getPreviewText = (text, query) => {
    if (!text) return '';
    
    const maxLength = 120;
    if (text.length <= maxLength) return text;
    
    const lowerText = text.toLowerCase();
    const lowerQuery = query.toLowerCase();
    const matchIndex = lowerText.indexOf(lowerQuery);
    
    if (matchIndex === -1) {
      return text.substring(0, maxLength) + '...';
    }
    
    let start = Math.max(0, matchIndex - 30);
    let end = Math.min(text.length, matchIndex + query.length + 60);
    
    while (start > 0 && text[start] !== ' ') start--;
    while (end < text.length && text[end] !== ' ') end++;
    
    return (start > 0 ? '...' : '') + 
           text.substring(start, end) + 
           (end < text.length ? '...' : '');
  };

  const formatSimilarity = (similarity) => {
    if (similarity === undefined || similarity === null) return '';
    // return `${Math.round(similarity * 100)}%`;
    return `${Math.round(similarity * 1)}`;
  };

  const getDocumentIcon = (filename) => {
    if (!filename) return <FileText className="h-4 w-4 text-gray-500" />;
    
    const extension = filename.split('.').pop()?.toLowerCase();
    if (extension === 'pdf') {
      return <FileText className="h-4 w-4 text-red-500" />;
    } else if (extension === 'docx') {
      return <BookOpen className="h-4 w-4 text-blue-500" />;
    } else if (extension === 'txt') {
      return <FileCode className="h-4 w-4 text-green-500" />;
    }
    
    return <FileText className="h-4 w-4 text-gray-500" />;
  };

  return (
    <div className="w-full">
      <div className="max-w-6xl mx-auto p-4">
        <div className="flex flex-col md:flex-row items-start md:items-end justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Поиск по документам</h1>
            <p className="text-gray-600">Найдите нужную информацию в загруженных документах</p>
          </div>
          
          <div className="flex flex-col md:flex-row items-end gap-4">
            <div className="relative">
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="appearance-none bg-blue-600 text-white px-4 py-2 pr-8 rounded-lg font-medium text-sm cursor-pointer hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="openai">OpenAI</option>
                <option value="roberta">RoBERTa</option>
              </select>
              <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none">
                <ChevronDown size={16} className="text-white" />
              </div>
            </div>
          </div>
        </div>

        <form onSubmit={handleSearch} className="mb-6">
          <div className="flex gap-4">
            <div className="flex-grow relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Введите поисковый запрос..."
                className="w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={isLoading}
              />
              {isLoading && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
                </div>
              )}
            </div>
            <button
              type="submit"
              disabled={!searchQuery.trim() || isLoading}
              className={`px-6 py-2 rounded-lg font-medium text-white transition-colors duration-150 ${
                !searchQuery.trim() || isLoading
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50'
              }`}
            >
              <Search size={20} />
            </button>
          </div>
        </form>
        
        {hasSearched && !isLoading && (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            {searchResults.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-xl text-gray-600">По вашему запросу ничего не найдено</p>
                <p className="text-gray-500 mt-2">Попробуйте изменить запрос или загрузить больше документов</p>
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="w-8 px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase"></th>
                        <th 
                          className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer"
                          onClick={() => toggleSort('category')}
                        >
                          <div className="flex items-center">
                            <span>Документ</span>
                            {sortField === 'category' && (
                              <span className="ml-1">
                                {sortDirection === 'asc' ? <SortAsc className="h-3 w-3" /> : <SortDesc className="h-3 w-3" />}
                              </span>
                            )}
                          </div>
                        </th>
                        <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          Фрагмент
                        </th>
                        <th 
                          className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer whitespace-nowrap"
                          onClick={() => toggleSort('created_at')}
                        >
                          <div className="flex items-center">
                            <span>Дата</span>
                            {sortField === 'created_at' && (
                              <span className="ml-1">
                                {sortDirection === 'asc' ? <SortAsc className="h-3 w-3" /> : <SortDesc className="h-3 w-3" />}
                              </span>
                            )}
                          </div>
                        </th>
                        <th 
                          className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer whitespace-nowrap"
                          onClick={() => toggleSort('score')}
                        >
                          <div className="flex items-center">
                            <span>Сходство</span>
                            {sortField === 'score' && (
                              <span className="ml-1">
                                {sortDirection === 'asc' ? <SortAsc className="h-3 w-3" /> : <SortDesc className="h-3 w-3" />}
                              </span>
                            )}
                          </div>
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {sortResults(searchResults).map((result, index) => {
                        const isExpanded = expandedRows[result.id || index];
                        
                        return (
                          <>
                            <tr key={result.id || index} className={`hover:bg-gray-50 ${isExpanded ? 'bg-blue-50' : ''}`}>
                              <td className="px-3 py-4 whitespace-nowrap">
                                <button 
                                  onClick={() => toggleRowExpansion(result.id || index)}
                                  className="text-gray-500 hover:text-gray-700"
                                >
                                  {isExpanded ? 
                                    <ArrowUp className="h-4 w-4" /> : 
                                    <ArrowDown className="h-4 w-4" />
                                  }
                                </button>
                              </td>
                              <td className="px-3 py-4 whitespace-nowrap">
                                <div className="flex items-center">
                                  {getDocumentIcon(result.category)}
                                  <span className="ml-2 text-sm font-medium text-gray-900 truncate max-w-[150px]">
                                    {result.category || 'Без имени'}
                                  </span>
                                </div>
                              </td>
                              <td className="px-3 py-4">
                                <p className="text-sm text-gray-700 truncate max-w-xs">
                                  {highlightMatches(getPreviewText(result.contents, searchQuery), searchQuery)}
                                </p>
                              </td>
                              <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500">
                                {result.created_at ? 
                                  new Date(result.created_at).toLocaleDateString('ru-RU') : 
                                  '—'
                                }
                              </td>
                              <td className="px-3 py-4 whitespace-nowrap">
                                <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                  parseFloat(result.distance) > 0.8 
                                    ? 'bg-green-100 text-green-800' 
                                    : parseFloat(result.distance) > 0.5 
                                      ? 'bg-yellow-100 text-yellow-800' 
                                      : 'bg-gray-100 text-gray-800'
                                }`}>
                                  {formatSimilarity(result.distance)}
                                </span>
                              </td>
                            </tr>
                            
                            {isExpanded && (
                              <tr className="bg-gray-50">
                                <td colSpan={5} className="px-6 py-4">
                                  <div className="text-sm text-gray-700 border-l-4 border-blue-500 pl-4 py-1">
                                    <div className="mb-3">
                                      {result.contents || 'Содержимое недоступно'}
                                    </div>
                                    <div className="flex justify-between text-xs text-gray-500 pt-2 border-t border-gray-200">
                                      <div>ID: {result.id || 'Нет ID'}</div>
                                      <div>
                                        <button className="text-blue-600 hover:text-blue-800 flex items-center">
                                          <span className="mr-1">Открыть документ</span>
                                          <ExternalLink className="h-3 w-3" />
                                        </button>
                                      </div>
                                    </div>
                                  </div>
                                </td>
                              </tr>
                            )}
                          </>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                
                <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 text-sm text-gray-500">
                  Всего найдено: {searchResults.length}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentSearchTable;
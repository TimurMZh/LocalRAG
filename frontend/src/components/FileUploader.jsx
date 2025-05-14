import { useState, useRef } from 'react';
import { Upload, X, Check, FileText, AlertCircle, ChevronDown } from 'lucide-react';

const FileUploader = () => {
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState(null); // 'success', 'error', null
  const [errorMessage, setErrorMessage] = useState('');
  const [selectedModel, setSelectedModel] = useState('openai');
  const fileInputRef = useRef(null);
  
  const allowedExts = ['txt','pdf','docx','json','xml'];
  // Поддерживаемые типы файлов
  const acceptedFileTypes = [
    'text/plain',           // .txt
    'application/pdf',      // .pdf
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // .docx
    'application/json', // .json
    'application/xml', // .xml
  ];
  
    // replaced handleFileChange
    const handleFileChange = (e) => {
      setErrorMessage('');
      const f = e.target.files[0];
      if (!f) return;
  
      const ext = f.name.split('.').pop().toLowerCase();
      const okMime = acceptedFileTypes.includes(f.type);
      const okExt  = allowedExts.includes(ext);
  
      console.log('File name:', f.name);
      console.log('File extension:', ext);
      console.log('File MIME type:', f.type);
      console.log('okMime:', okMime, 'okExt:', okExt);
  
      if (!okMime && !okExt) {
        console.log('Setting error: Unsupported file type:', ext);
        setErrorMessage(`Unsupported file type: ${ext}`);
        setUploadStatus('error');
        setFile(null);
        return;
      }
  
      setFile(f);
      setUploadStatus(null);
    };
  
  
  const handleUpload = async () => {
    if (!file) return;
    
    setIsUploading(true);
    setUploadProgress(0);
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('model', selectedModel);
    
    try {
      // Имитация загрузки с XMLHttpRequest для отслеживания прогресса
      const xhr = new XMLHttpRequest();
      
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const progress = Math.round((event.loaded / event.total) * 100);
          setUploadProgress(progress);
        }
      });
      
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText);
            if (response.error) {
              setUploadStatus('error');
              setErrorMessage(response.error);
            } else {
              setUploadStatus('success');
            }
          } catch (e) {
            setUploadStatus('error');
            setErrorMessage('Ошибка при обработке ответа сервера');
          }
        } else {
          setUploadStatus('error');
          try {
            const response = JSON.parse(xhr.responseText);
            setErrorMessage(response.detail || response.error || 'Ошибка загрузки файла');
          } catch (e) {
            setErrorMessage(`Ошибка загрузки: ${xhr.statusText}`);
          }
        }
        setIsUploading(false);
      });
      
      xhr.addEventListener('error', () => {
        setUploadStatus('error');
        setErrorMessage('Произошла ошибка при загрузке файла');
        setIsUploading(false);
      });
      
      xhr.open('POST', 'http://localhost:8080/documents/upload');
      xhr.send(formData);
      
    } catch (error) {
      setUploadStatus('error');
      setErrorMessage('Произошла ошибка при загрузке файла');
      setIsUploading(false);
    }
  };
  
  const triggerFileInput = () => {
    fileInputRef.current.click();
  };
  
  const resetUpload = () => {
    setFile(null);
    setUploadStatus(null);
    setErrorMessage('');
    setUploadProgress(0);
  };
  
  // Получение имени файла с расширением
  const getFileExtension = (filename) => {
    return filename.split('.').pop().toUpperCase();
  };
  
  // Получение имени файла без пути
  const getFileName = (filepath) => {
    return filepath.split('\\').pop();
  };
  
  return (
    <div className="w-full max-w-md mx-auto p-6 bg-white rounded-lg shadow-md">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-gray-800">Загрузка документа</h2>
        <div className="relative">
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="appearance-none bg-blue-600 text-white px-4 py-1.5 pr-8 rounded-md font-medium text-sm cursor-pointer hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="openai">OpenAI</option>
            <option value="roberta">RoBERTa</option>
          </select>
          <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none">
            <ChevronDown size={16} className="text-white" />
          </div>
        </div>
      </div>
      
      <div className="mb-4">
        <div 
          className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors duration-300 ${
            file ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50'
          }`}
          onClick={triggerFileInput}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".txt,.pdf,.docx,.json,.xml"
            className="hidden"
          />
          
          <Upload className="mx-auto h-12 w-12 text-gray-400" />
          
          <p className="mt-2 text-sm font-medium text-gray-700">
            {file ? getFileName(file.name) : 'Нажмите для выбора файла или перетащите его сюда'}
          </p>
          
          {file && (
            <div className="mt-2 inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
              <FileText className="w-4 h-4 mr-1" />
              {getFileExtension(file.name)}
            </div>
          )}
          
          <p className="mt-1 text-xs text-gray-500">
            Поддерживаемые форматы: TXT, DOCX, PDF, JSON, XML
          </p>
        </div>
      </div>
      
      {/* Индикатор прогресса */}
      {file && !uploadStatus && (
        <div className="mb-4">
          {isUploading && (
            <div className="mt-2">
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div 
                  className="bg-blue-600 h-2.5 rounded-full transition-all duration-300" 
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
              <p className="text-xs text-right mt-1 text-gray-600">{uploadProgress}%</p>
            </div>
          )}
          
          <button
            onClick={handleUpload}
            disabled={isUploading}
            className={`w-full mt-3 py-2 px-4 rounded-md font-medium text-white transition-colors duration-300 ${
              isUploading 
                ? 'bg-blue-400 cursor-not-allowed' 
                : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50'
            }`}
          >
            {isUploading ? 'Загрузка...' : 'Загрузить файл'}
          </button>
        </div>
      )}
      
      {/* Сообщение об успешной загрузке */}
      {uploadStatus === 'success' && (
        <div className="mb-4 p-3 bg-green-100 border border-green-200 rounded-md flex items-center">
          <Check className="h-5 w-5 text-green-500 mr-2" />
          <span className="text-green-800 text-sm font-medium">Файл успешно загружен</span>
          <button 
            onClick={resetUpload} 
            className="ml-auto p-1 rounded-full hover:bg-green-200 focus:outline-none"
          >
            <X className="h-4 w-4 text-green-500" />
          </button>
        </div>
      )}
      
      {/* Сообщение об ошибке */}
      {uploadStatus === 'error' && (
        <div className="mb-4 p-3 bg-red-100 border border-red-200 rounded-md flex items-center">
          <AlertCircle className="h-5 w-5 text-red-500 mr-2" />
          <span className="text-red-800 text-sm font-medium">{errorMessage}</span>
          <button 
            onClick={resetUpload} 
            className="ml-auto p-1 rounded-full hover:bg-red-200 focus:outline-none"
          >
            <X className="h-4 w-4 text-red-500" />
          </button>
        </div>
      )}
    </div>
  );
};

export default FileUploader;
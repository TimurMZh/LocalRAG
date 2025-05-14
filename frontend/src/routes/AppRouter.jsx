import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import UploadPage from '../pages/UploadPage';
import SearchPage from '../pages/SearchPage';
import ChatPage from '../pages/ChatPage';


const AppRouter = () => {
    return (
        <BrowserRouter>
            <Routes>
            <Route path="/" element={<Navigate to="/upload" replace />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="*" element={<Navigate to="/upload" replace />} />
            </Routes>
        </BrowserRouter>
    );
  };
  
  export default AppRouter;
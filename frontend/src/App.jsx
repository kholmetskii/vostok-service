import { Routes, Route, Navigate } from 'react-router-dom';
import WarehousesListPage from './pages/WarehousesListPage.jsx';
import WarehousePage from './pages/WarehousePage.jsx';
import CreateWarehousePage from "./pages/CreateWarehousePage.jsx";

function App() {
    return (
        <Routes>
            <Route path="/" element={<Navigate to="/warehouse" />} />
            <Route path="/warehouse" element={<WarehousesListPage />} />
            <Route path="/warehouse/:id" element={<WarehousePage />} />
            <Route path="/createwarehouse" element={<CreateWarehousePage />} />
        </Routes>
    );
}

export default App;

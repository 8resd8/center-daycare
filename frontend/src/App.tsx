import { Routes, Route } from "react-router-dom";
import Layout from "@/components/Layout";
import ProtectedRoute from "@/components/ProtectedRoute";
import LoginPage from "@/pages/LoginPage";
import CareRecordsPage from "@/pages/CareRecordsPage";
import CustomerManagePage from "@/pages/CustomerManagePage";
import EmployeeManagePage from "@/pages/EmployeeManagePage";
import DashboardPage from "@/pages/DashboardPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<CareRecordsPage />} />
                <Route path="/customers" element={<CustomerManagePage />} />
                <Route path="/employees" element={<EmployeeManagePage />} />
                <Route path="/dashboard" element={<DashboardPage />} />
              </Routes>
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

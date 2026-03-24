import { Routes, Route } from "react-router-dom";
import Layout from "@/components/Layout";
import CareRecordsPage from "@/pages/CareRecordsPage";
import CustomerManagePage from "@/pages/CustomerManagePage";
import EmployeeManagePage from "@/pages/EmployeeManagePage";
import DashboardPage from "@/pages/DashboardPage";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<CareRecordsPage />} />
        <Route path="/customers" element={<CustomerManagePage />} />
        <Route path="/employees" element={<EmployeeManagePage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
      </Routes>
    </Layout>
  );
}

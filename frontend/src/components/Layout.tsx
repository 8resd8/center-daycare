import { useState } from "react";
import type { ReactNode } from "react";
import Sidebar from "./Sidebar";

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {sidebarOpen && <Sidebar onClose={() => setSidebarOpen(false)} />}
      <main className="flex-1 overflow-y-auto">
        {!sidebarOpen && (
          <button
            onClick={() => setSidebarOpen(true)}
            className="fixed top-4 left-4 z-10 p-2 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50"
            title="사이드바 열기"
          >
            ☰
          </button>
        )}
        <div className="p-6">{children}</div>
      </main>
    </div>
  );
}

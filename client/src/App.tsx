import { useState } from "react";
import { ChatPageAgent } from "./pages/ChatPageAgent";
import { PromptsPage } from "./pages/PromptsPage";
import { TracesPage } from "./pages/TracesPage";
import { RegistryPage } from "./pages/RegistryPage";
import { ArchitecturePage } from "./pages/ArchitecturePage";
import { MessageSquare, FileCode, Moon, Sun, Activity, Database, Layers } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useTheme } from "./components/theme-provider";

function App() {
  const [activeTab, setActiveTab] = useState("chat");
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const { theme, setTheme } = useTheme();

  // Shared state for warehouse and catalog/schema selection
  const [selectedWarehouse, setSelectedWarehouse] = useState<string>("");
  const [selectedCatalogSchema, setSelectedCatalogSchema] = useState<string>("");

  const isDark = theme === "dark";

  const handleViewTrace = (traceId: string) => {
    setSelectedTraceId(traceId);
    setActiveTab("traces");
  };

  return (
    <div className={`h-screen flex flex-col ${isDark ? "bg-[#1C3D42]" : "bg-gray-50"}`}>
      {/* Universal Top Banner */}
      <div className={`flex items-center justify-between px-6 py-3 ${
        isDark ? "bg-[#16343A]" : "bg-white"
      } border-b ${isDark ? "border-white/10" : "border-gray-200"}`}>
        {/* Tab Navigation */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => setActiveTab("chat")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
              activeTab === "chat"
                ? isDark
                  ? "bg-white/10 text-white"
                  : "bg-gray-100 text-gray-900"
                : isDark
                ? "text-white/60 hover:text-white/80 hover:bg-white/5"
                : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
            }`}
          >
            <MessageSquare className="h-4 w-4" />
            Chat Playground
          </button>
          <button
            onClick={() => setActiveTab("mcp-info")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
              activeTab === "mcp-info"
                ? isDark
                  ? "bg-white/10 text-white"
                  : "bg-gray-100 text-gray-900"
                : isDark
                ? "text-white/60 hover:text-white/80 hover:bg-white/5"
                : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
            }`}
          >
            <FileCode className="h-4 w-4" />
            MCP Info
          </button>
          <button
            onClick={() => setActiveTab("traces")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
              activeTab === "traces"
                ? isDark
                  ? "bg-white/10 text-white"
                  : "bg-gray-100 text-gray-900"
                : isDark
                ? "text-white/60 hover:text-white/80 hover:bg-white/5"
                : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
            }`}
          >
            <Activity className="h-4 w-4" />
            Traces
          </button>
          <button
            onClick={() => setActiveTab("registry")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
              activeTab === "registry"
                ? isDark
                  ? "bg-white/10 text-white"
                  : "bg-gray-100 text-gray-900"
                : isDark
                ? "text-white/60 hover:text-white/80 hover:bg-white/5"
                : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
            }`}
          >
            <Database className="h-4 w-4" />
            API Registry
          </button>
          <button
            onClick={() => setActiveTab("architecture")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
              activeTab === "architecture"
                ? isDark
                  ? "bg-white/10 text-white"
                  : "bg-gray-100 text-gray-900"
                : isDark
                ? "text-white/60 hover:text-white/80 hover:bg-white/5"
                : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
            }`}
          >
            <Layers className="h-4 w-4" />
            App Architecture
          </button>
        </div>

        {/* Theme Selector */}
        <Select value={theme} onValueChange={setTheme}>
          <SelectTrigger className={`w-[140px] ${
            isDark
              ? "bg-white/5 border-white/10 text-white hover:bg-white/10"
              : "bg-gray-50 border-gray-300 text-gray-900 hover:bg-gray-100"
          }`}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="dark">
              <div className="flex items-center gap-2">
                <Moon className="h-4 w-4" />
                <span>Dark</span>
              </div>
            </SelectItem>
            <SelectItem value="light">
              <div className="flex items-center gap-2">
                <Sun className="h-4 w-4" />
                <span>Light</span>
              </div>
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Tab Content - Keep all tabs rendered to preserve state */}
      <div className="flex-1 overflow-hidden">
        <div className={activeTab === "chat" ? "h-full" : "hidden"}>
          <ChatPageAgent
            onViewTrace={handleViewTrace}
            selectedWarehouse={selectedWarehouse}
            setSelectedWarehouse={setSelectedWarehouse}
            selectedCatalogSchema={selectedCatalogSchema}
            setSelectedCatalogSchema={setSelectedCatalogSchema}
          />
        </div>
        <div className={activeTab === "mcp-info" ? "h-full" : "hidden"}>
          <PromptsPage />
        </div>
        <div className={activeTab === "traces" ? "h-full" : "hidden"}>
          <TracesPage initialTraceId={selectedTraceId} />
        </div>
        <div className={activeTab === "registry" ? "h-full" : "hidden"}>
          <RegistryPage
            selectedWarehouse={selectedWarehouse}
            selectedCatalogSchema={selectedCatalogSchema}
          />
        </div>
        <div className={activeTab === "architecture" ? "h-full" : "hidden"}>
          <ArchitecturePage />
        </div>
      </div>
    </div>
  );
}

export default App;

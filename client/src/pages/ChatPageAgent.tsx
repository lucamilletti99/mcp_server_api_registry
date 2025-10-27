import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Send,
  Loader2,
  Sparkles,
  Database,
  Search,
  TestTube,
  FileJson,
  Home,
  Plus,
  Wrench,
  HelpCircle,
} from "lucide-react";
import { useTheme } from "@/components/theme-provider";
import DOMPurify from "dompurify";
import { marked } from "marked";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

interface Model {
  id: string;
  name: string;
  provider: string;
  supports_tools: boolean;
  context_window: number;
  type: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  tool_calls?: Array<{
    tool: string;
    args: any;
    result: any;
  }>;
}

export function ChatPageAgent() {
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [systemPrompt, setSystemPrompt] = useState<string>("");
  const [showSystemPrompt, setShowSystemPrompt] = useState(false);
  const [tempSystemPrompt, setTempSystemPrompt] = useState<string>("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { theme } = useTheme();

  useEffect(() => {
    fetchModels();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const fetchModels = async () => {
    try {
      const response = await fetch("/api/chat/models");
      const data = await response.json();
      setModels(data.models);
      setSelectedModel(data.default);
    } catch (error) {
      console.error("Failed to fetch models:", error);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      role: "user",
      content: input,
    };

    // Add user message and a temporary "thinking" message
    setMessages((prev) => [...prev, userMessage, {
      role: "assistant",
      content: "Thinking...",
    }]);
    setInput("");
    setLoading(true);

    try {
      // Call the NEW agent endpoint - it does all the orchestration!
      const response = await fetch("/api/agent/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: [...messages.map(m => ({ role: m.role, content: m.content })), userMessage],
          model: selectedModel,
          system_prompt: systemPrompt || undefined, // Include custom system prompt if set
        }),
      });

      const data = await response.json();

      // Remove the temporary "thinking" message
      setMessages((prev) => prev.slice(0, -1));

      // Check for API errors
      if (data.detail) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `Error: ${data.detail}`,
          },
        ]);
        return;
      }

      // Add the assistant's response
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.response,
          tool_calls: data.tool_calls, // Show which tools were used
        },
      ]);

    } catch (error) {
      console.error("Failed to send message:", error);
      // Remove thinking message
      setMessages((prev) => prev.slice(0, -1));
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I encountered an error processing your request.",
        },
      ]);
    } finally {
      setLoading(false);
      textareaRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const resetChat = () => {
    setMessages([]);
    setInput("");
  };

  const handleOpenSystemPrompt = () => {
    setTempSystemPrompt(systemPrompt);
    setShowSystemPrompt(true);
  };

  const handleSaveSystemPrompt = () => {
    setSystemPrompt(tempSystemPrompt);
    setShowSystemPrompt(false);
  };

  const handleCancelSystemPrompt = () => {
    setTempSystemPrompt(systemPrompt);
    setShowSystemPrompt(false);
  };

  const handleResetSystemPrompt = () => {
    setTempSystemPrompt("");
  };

  const suggestedActions = [
    {
      icon: <Search className="h-4 w-4" />,
      label: "Discover",
      prompt: "Discover the Alpha Vantage API for stock data",
    },
    {
      icon: <Database className="h-4 w-4" />,
      label: "Register",
      prompt: "Help me register a new API in the registry",
    },
    {
      icon: <FileJson className="h-4 w-4" />,
      label: "Query",
      prompt: "Show me all registered APIs in the registry",
    },
    {
      icon: <TestTube className="h-4 w-4" />,
      label: "Test",
      prompt: "Test if my registered API is still healthy",
    },
    {
      icon: <Wrench className="h-4 w-4" />,
      label: "Tools",
      prompt: "What tools do I have available?",
    },
  ];

  const isDark = theme === "dark";

  return (
    <div
      className={`flex flex-col h-full ${
        isDark
          ? "bg-gradient-to-br from-[#0f2027] via-[#203a43] to-[#2c5364]"
          : "bg-gradient-to-br from-gray-50 via-blue-50 to-indigo-50"
      } transition-all duration-500`}
    >
      {/* Top Bar */}
      <div className={`flex items-center justify-between p-4 ${
        isDark ? "bg-black/20" : "bg-white/60"
      } backdrop-blur-sm border-b ${
        isDark ? "border-white/10" : "border-gray-200"
      }`}>
        <div className="flex items-center gap-3">
          <Sparkles className={`h-5 w-5 ${isDark ? "text-blue-400" : "text-blue-600"}`} />
          <span className={`font-semibold ${isDark ? "text-white" : "text-gray-900"}`}>
            API Registry Agent
          </span>
          <span className={`text-xs px-2 py-1 rounded ${isDark ? "bg-blue-500/20 text-blue-300" : "bg-blue-100 text-blue-700"}`}>
            MCP Powered
          </span>
          {messages.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={resetChat}
              className={`gap-2 ${
                isDark
                  ? "bg-white/5 border-white/20 text-white hover:bg-white/10"
                  : "bg-white border-gray-300 text-gray-900 hover:bg-gray-100"
              }`}
            >
              <Home className="h-4 w-4" />
              New Chat
            </Button>
          )}
        </div>
        <div>
          <Select value={selectedModel} onValueChange={setSelectedModel}>
            <SelectTrigger className={`w-[240px] ${
              isDark
                ? "bg-black/20 border-white/20 text-white"
                : "bg-white border-gray-300 text-gray-900"
            } backdrop-blur-sm`}>
              <SelectValue placeholder="Select model">
                {models.find((m) => m.id === selectedModel)?.name || "Select model"}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {models.map((model) => (
                <SelectItem
                  key={model.id}
                  value={model.id}
                  disabled={!model.supports_tools}
                >
                  <div className="flex flex-col">
                    <div className="flex items-center gap-2">
                      <span className={`font-medium ${!model.supports_tools ? 'text-muted-foreground' : ''}`}>
                        {model.name}
                      </span>
                      {!model.supports_tools && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                          Not tool-enabled
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {model.provider} • {model.context_window.toLocaleString()} tokens
                    </span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>


      {/* Main Content */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          /* Empty State */
          <div className="flex flex-col items-center justify-center min-h-full px-6 py-20">
            <div className="max-w-3xl w-full space-y-8">
              <div className="text-center space-y-4">
                <h1 className={`text-5xl font-bold ${
                  isDark ? "text-white" : "text-gray-900"
                }`}>
                  What can I help you with today?
                </h1>
                <p className={`text-lg ${
                  isDark ? "text-white/80" : "text-gray-600"
                }`}>
                  I can help you discover, register, and manage API endpoints
                </p>
              </div>

              {/* Search Input */}
              <div className="relative">
                <Textarea
                  ref={textareaRef}
                  placeholder="Explore APIs, register endpoints, or query the registry..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className={`min-h-[100px] text-lg ${
                    isDark
                      ? "bg-white/10 border-white/20 text-white placeholder:text-white/60"
                      : "bg-white border-gray-300 text-gray-900 placeholder:text-gray-500"
                  } backdrop-blur-md resize-none focus:ring-2 ${
                    isDark ? "focus:ring-blue-400" : "focus:ring-blue-500"
                  } transition-all shadow-lg`}
                  disabled={loading}
                />
                <Button
                  onClick={sendMessage}
                  disabled={loading || !input.trim()}
                  size="lg"
                  className="absolute bottom-4 right-4 rounded-full bg-blue-500 hover:bg-blue-600 text-white shadow-lg"
                >
                  {loading ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <Send className="h-5 w-5" />
                  )}
                </Button>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-3 flex-wrap justify-center">
                {suggestedActions.map((action) => (
                  <Button
                    key={action.label}
                    variant="outline"
                    className={`gap-2 ${
                      isDark
                        ? "bg-white/10 border-white/20 text-white hover:bg-white/20"
                        : "bg-white border-gray-300 text-gray-900 hover:bg-gray-100"
                    } backdrop-blur-sm shadow-md transition-all`}
                    onClick={() => setInput(action.prompt)}
                  >
                    {action.icon}
                    {action.label}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* Conversation View */
          <div className="max-w-4xl mx-auto py-8 px-6 space-y-6">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-6 py-4 shadow-lg ${
                    message.role === "user"
                      ? "bg-blue-500 text-white"
                      : isDark
                      ? "bg-white/10 backdrop-blur-md text-white border border-white/20"
                      : "bg-white text-gray-900 border border-gray-200"
                  }`}
                >
                  <div
                    className={`prose prose-invert max-w-none ${message.content === "Thinking..." ? "typing-indicator" : ""}`}
                    dangerouslySetInnerHTML={{
                      __html: DOMPurify.sanitize(
                        marked.parse(message.content, { breaks: true, gfm: true }) as string,
                        {
                          ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'a', 'code', 'pre', 'blockquote', 'span', 'div', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'hr', 'del', 'input'],
                          ALLOWED_ATTR: ['href', 'target', 'class', 'style', 'type', 'checked', 'disabled']
                        }
                      )
                    }}
                  />
                  {message.tool_calls && message.tool_calls.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {message.tool_calls.map((toolCall, tcIndex) => (
                        <span
                          key={tcIndex}
                          className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium ${
                            message.role === "user"
                              ? "bg-white/20"
                              : isDark
                              ? "bg-blue-500/20 text-blue-300"
                              : "bg-blue-100 text-blue-700"
                          }`}
                        >
                          <Sparkles className="h-3 w-3" />
                          {toolCall.tool}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className={`max-w-[80%] rounded-2xl px-6 py-4 shadow-lg ${
                  isDark
                    ? "bg-white/10 backdrop-blur-md border border-white/20"
                    : "bg-white border border-gray-200"
                }`}>
                  <div className={`flex items-center gap-2 ${
                    isDark ? "text-white/80" : "text-gray-600"
                  }`}>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="text-sm font-medium">Agent is thinking and using tools...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* System Prompt Trigger Button - Fixed on Right Edge */}
      <button
        onClick={handleOpenSystemPrompt}
        onMouseEnter={() => setShowSystemPrompt(true)}
        className={`fixed right-0 top-1/2 -translate-y-1/2 z-20 px-2 py-6 rounded-l-lg shadow-lg transition-all duration-300 ${
          isDark
            ? "bg-white/10 border-l border-t border-b border-white/20 text-white hover:bg-white/20"
            : "bg-white border-l border-t border-b border-gray-200 text-gray-900 hover:bg-gray-50"
        } backdrop-blur-md flex items-center gap-2 text-sm writing-mode-vertical`}
        style={{ writingMode: 'vertical-rl' }}
      >
        <Plus className="h-4 w-4" />
        <span>{systemPrompt ? "Edit System Prompt" : "Add System Prompt"}</span>
      </button>

      {/* System Prompt Panel - Slides from Right */}
      <div
        className={`fixed right-0 top-0 h-full w-96 z-30 transition-transform duration-300 ${
          showSystemPrompt ? "translate-x-0" : "translate-x-full"
        } ${
          isDark ? "bg-black/90" : "bg-white/95"
        } backdrop-blur-lg border-l ${
          isDark ? "border-white/20" : "border-gray-200"
        } shadow-2xl`}
        onMouseLeave={() => !tempSystemPrompt && setShowSystemPrompt(false)}
      >
        <div className="flex flex-col h-full p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className={`text-lg font-semibold ${
              isDark ? "text-white" : "text-gray-900"
            }`}>
              System Prompt
            </h3>
            <button
              onClick={handleCancelSystemPrompt}
              className={`p-2 rounded-lg transition-colors ${
                isDark
                  ? "hover:bg-white/10 text-white"
                  : "hover:bg-gray-100 text-gray-900"
              }`}
            >
              <span className="text-xl">&times;</span>
            </button>
          </div>

          <div className="flex-1 flex flex-col gap-4">
            <label className={`text-sm font-medium ${
              isDark ? "text-white/80" : "text-gray-700"
            }`}>
              Customize the agent's behavior and role:
            </label>
            <Textarea
              value={tempSystemPrompt}
              onChange={(e) => setTempSystemPrompt(e.target.value)}
              placeholder="Optionally override the system prompt. Define the agent's role, capabilities, and behavior here..."
              className={`flex-1 ${
                isDark
                  ? "bg-white/5 border-blue-400/50 text-white placeholder:text-white/40 focus:border-blue-400"
                  : "bg-white border-blue-500/50 text-gray-900 placeholder:text-gray-400 focus:border-blue-500"
              } resize-none`}
            />
          </div>

          <div className={`flex items-center justify-end gap-2 mt-6 pt-6 border-t ${
            isDark ? "border-white/20" : "border-gray-200"
          }`}>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleResetSystemPrompt}
              className={isDark ? "text-blue-400 hover:text-blue-300 hover:bg-white/10" : "text-blue-600 hover:text-blue-700"}
            >
              Reset
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleCancelSystemPrompt}
              className={isDark ? "border-white/20 text-white hover:bg-white/10" : ""}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleSaveSystemPrompt}
              className="bg-blue-500 hover:bg-blue-600 text-white"
            >
              Save
            </Button>
          </div>
        </div>
      </div>

      {/* Bottom Input (shown when in conversation) */}
      {messages.length > 0 && (
        <div className={`p-4 ${
          isDark ? "bg-black/20" : "bg-white/60"
        } backdrop-blur-sm border-t ${
          isDark ? "border-white/10" : "border-gray-200"
        }`}>
          <div className="max-w-4xl mx-auto">
            {/* Quick Action Buttons - Horizontal row above input */}
            <div className="flex items-center gap-2 mb-3 overflow-x-auto pb-2">
              {suggestedActions.map((action, index) => (
                <button
                  key={action.label}
                  onClick={() => setInput(action.prompt)}
                  className={`group flex items-center gap-2 px-4 py-2 rounded-full transition-all duration-300 hover:scale-105 whitespace-nowrap ${
                    isDark
                      ? "bg-white/10 border border-white/20 text-white hover:bg-white/20"
                      : "bg-white border border-gray-200 text-gray-900 hover:bg-gray-50"
                  } backdrop-blur-md shadow-md`}
                  style={{
                    animation: `fadeInRight 0.3s ease-out ${index * 0.1}s both`,
                  }}
                >
                  {action.icon}
                  <span className="text-sm font-medium">{action.label}</span>
                </button>
              ))}
            </div>

            <div className="relative">
              <Textarea
                ref={textareaRef}
                placeholder="Continue the conversation..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                className={`min-h-[60px] pr-14 ${
                  isDark
                    ? "bg-white/10 border-white/20 text-white placeholder:text-white/60"
                    : "bg-white border-gray-300 text-gray-900 placeholder:text-gray-500"
                } backdrop-blur-md resize-none shadow-lg`}
                disabled={loading}
              />
              <Button
                onClick={sendMessage}
                disabled={loading || !input.trim()}
                size="icon"
                className="absolute bottom-3 right-3 rounded-full bg-blue-500 hover:bg-blue-600 text-white shadow-lg"
              >
                {loading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Send className="h-5 w-5" />
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* FAQ/Help Button - Bottom Left */}
      <Dialog>
        <DialogTrigger asChild>
          <button
            className={`fixed bottom-6 left-6 z-20 w-14 h-14 rounded-full shadow-lg transition-all duration-300 hover:scale-110 ${
              isDark
                ? "bg-white/10 border border-white/20 text-white hover:bg-white/20"
                : "bg-white border border-gray-200 text-gray-900 hover:bg-gray-50"
            } backdrop-blur-md flex items-center justify-center`}
            title="Help & FAQ"
          >
            <HelpCircle className="h-6 w-6" />
          </button>
        </DialogTrigger>
        <DialogContent className={`max-w-2xl max-h-[80vh] overflow-y-auto ${
          isDark ? "bg-gray-900 text-white border-white/20" : "bg-white text-gray-900"
        }`}>
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold">How to Use the API Registry Agent</DialogTitle>
            <DialogDescription className={isDark ? "text-gray-400" : "text-gray-600"}>
              Your AI-powered assistant for managing and testing APIs
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-6 mt-4">
            <section>
              <h3 className="text-lg font-semibold mb-2">🚀 Getting Started</h3>
              <p className={isDark ? "text-gray-300" : "text-gray-700"}>
                The API Registry Agent uses MCP (Model Context Protocol) tools to help you discover, register, query, and test API endpoints. Simply chat with the agent using natural language!
              </p>
            </section>

            <section>
              <h3 className="text-lg font-semibold mb-2">🎯 Quick Actions</h3>
              <p className={isDark ? "text-gray-300 mb-2" : "text-gray-700 mb-2"}>
                Use the quick action buttons for common tasks:
              </p>
              <ul className={`list-disc list-inside space-y-1 ${isDark ? "text-gray-300" : "text-gray-700"}`}>
                <li><strong>Discover:</strong> Find and explore new APIs from the web</li>
                <li><strong>Register:</strong> Add APIs to your centralized registry</li>
                <li><strong>Query:</strong> Check what APIs are in your registry</li>
                <li><strong>Test:</strong> Verify API health and functionality</li>
                <li><strong>Tools:</strong> See all available MCP tools</li>
              </ul>
            </section>

            <section>
              <h3 className="text-lg font-semibold mb-2">💬 Example Prompts</h3>
              <ul className={`list-disc list-inside space-y-1 ${isDark ? "text-gray-300" : "text-gray-700"}`}>
                <li>"Discover APIs related to weather data"</li>
                <li>"Register the API at https://api.example.com"</li>
                <li>"What APIs are in my registry?"</li>
                <li>"Test if my weather API is healthy"</li>
                <li>"Execute a SQL query to count all registered APIs"</li>
              </ul>
            </section>

            <section>
              <h3 className="text-lg font-semibold mb-2">🛠️ Available Tools</h3>
              <ul className={`list-disc list-inside space-y-1 ${isDark ? "text-gray-300" : "text-gray-700"}`}>
                <li><strong>discover_api_endpoint:</strong> Search and discover new APIs</li>
                <li><strong>register_api_in_registry:</strong> Add APIs to the registry</li>
                <li><strong>check_api_registry:</strong> View registered APIs</li>
                <li><strong>call_api_endpoint:</strong> Make requests to APIs</li>
                <li><strong>execute_dbsql:</strong> Run SQL queries on Databricks</li>
                <li><strong>list_warehouses:</strong> List SQL warehouses</li>
                <li><strong>list_dbfs_files:</strong> Browse DBFS files</li>
              </ul>
            </section>

            <section>
              <h3 className="text-lg font-semibold mb-2">⚙️ Custom System Prompt</h3>
              <p className={isDark ? "text-gray-300" : "text-gray-700"}>
                Click the "Add System Prompt" button on the right edge to customize the agent's behavior and role for your specific use case.
              </p>
            </section>

            <section>
              <h3 className="text-lg font-semibold mb-2">✨ Features</h3>
              <ul className={`list-disc list-inside space-y-1 ${isDark ? "text-gray-300" : "text-gray-700"}`}>
                <li>Markdown rendering for formatted responses</li>
                <li>Real-time tool execution tracking</li>
                <li>Model selection (Claude, Llama, etc.)</li>
                <li>Dark/Light theme toggle</li>
                <li>Conversation history management</li>
              </ul>
            </section>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

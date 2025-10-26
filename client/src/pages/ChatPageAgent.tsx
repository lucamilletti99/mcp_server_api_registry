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
} from "lucide-react";
import { useTheme } from "@/components/theme-provider";

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
        <div className="flex items-center gap-2">
          <Sparkles className={`h-5 w-5 ${isDark ? "text-blue-400" : "text-blue-600"}`} />
          <span className={`font-semibold ${isDark ? "text-white" : "text-gray-900"}`}>
            API Registry Agent
          </span>
          <span className={`text-xs px-2 py-1 rounded ${isDark ? "bg-blue-500/20 text-blue-300" : "bg-blue-100 text-blue-700"}`}>
            MCP Powered
          </span>
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
                  <div className={`whitespace-pre-wrap break-words ${message.content === "Thinking..." ? "typing-indicator" : ""}`}>
                    {message.content}
                  </div>
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

      {/* Bottom Input (shown when in conversation) */}
      {messages.length > 0 && (
        <div className={`p-4 ${
          isDark ? "bg-black/20" : "bg-white/60"
        } backdrop-blur-sm border-t ${
          isDark ? "border-white/10" : "border-gray-200"
        }`}>
          <div className="max-w-4xl mx-auto relative">
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
      )}
    </div>
  );
}

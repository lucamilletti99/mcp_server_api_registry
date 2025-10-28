/**
 * TracesPage - Clean trace visualization for agent execution
 */

import { useState, useEffect } from 'react';
import { TracesService } from '@/fastapi_client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Clock, ChevronRight, ChevronDown, Activity, ArrowLeft, RefreshCw } from 'lucide-react';
import { useTheme } from '@/components/theme-provider';
import ReactMarkdown from 'react-markdown';

interface TraceSpan {
  span_id: string;
  name: string;
  start_time_ms: number;
  end_time_ms?: number;
  duration_ms?: number;
  parent_id?: string;
  attributes?: Record<string, any>;
  inputs?: Record<string, any>;
  outputs?: Record<string, any>;
  span_type: string;
  status: string;
}

interface Trace {
  request_id: string;
  trace_id: string;
  timestamp_ms: number;
  execution_time_ms?: number;
  status: string;
  spans: TraceSpan[];
  request_metadata?: Record<string, any>;
}

interface TracesPageProps {
  initialTraceId?: string | null;
}

export function TracesPage({ initialTraceId }: TracesPageProps = {}) {
  const [traces, setTraces] = useState<Trace[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<Trace | null>(null);
  const [selectedSpan, setSelectedSpan] = useState<TraceSpan | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedSpans, setExpandedSpans] = useState<Set<string>>(new Set());
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  useEffect(() => {
    loadTraces();
  }, []);

  useEffect(() => {
    if (initialTraceId) {
      loadTraceDetail(initialTraceId);
    }
  }, [initialTraceId]);

  useEffect(() => {
    // Auto-select first span when trace loads
    if (selectedTrace && selectedTrace.spans.length > 0 && !selectedSpan) {
      setSelectedSpan(selectedTrace.spans[0]);
      // Auto-expand all spans by default
      const allSpanIds = new Set(selectedTrace.spans.map(s => s.span_id));
      setExpandedSpans(allSpanIds);
    }
  }, [selectedTrace]);

  const loadTraces = async () => {
    try {
      setLoading(true);
      const response = await TracesService.listTracesApiTracesListGet(50, 0);
      setTraces(response.traces || []);
    } catch (error) {
      console.error('Failed to load traces:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadTraceDetail = async (traceId: string) => {
    try {
      setLoading(true);
      const trace = await TracesService.getTraceApiTracesTraceIdGet(traceId);
      setSelectedTrace(trace);
      setSelectedSpan(null);
    } catch (error) {
      console.error('Failed to load trace detail:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleSpan = (spanId: string) => {
    const newExpanded = new Set(expandedSpans);
    if (newExpanded.has(spanId)) {
      newExpanded.delete(spanId);
    } else {
      newExpanded.add(spanId);
    }
    setExpandedSpans(newExpanded);
  };

  const formatDuration = (ms?: number) => {
    if (!ms) return '0ms';
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const formatTime = (timestampMs: number) => {
    return new Date(timestampMs).toLocaleString();
  };

  const getSpanIcon = (spanType: string) => {
    switch (spanType) {
      case 'AGENT':
        return '🤖';
      case 'LLM':
        return '🧠';
      case 'TOOL':
        return '🔧';
      default:
        return '📦';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'SUCCESS':
        return isDark ? 'bg-green-500/20 text-green-300' : 'bg-green-100 text-green-700';
      case 'ERROR':
        return isDark ? 'bg-[#FF3621]/20 text-[#FF8A80]' : 'bg-red-100 text-red-700';
      case 'RUNNING':
        return isDark ? 'bg-[#FF3621]/20 text-[#FF8A80]' : 'bg-[#FF3621]/10 text-[#FF3621]';
      default:
        return isDark ? 'bg-gray-500/20 text-gray-300' : 'bg-gray-100 text-gray-700';
    }
  };

  const buildSpanTree = (spans: TraceSpan[]) => {
    const rootSpans = spans.filter(s => !s.parent_id);

    const getChildren = (parentId: string): TraceSpan[] => {
      return spans.filter(s => s.parent_id === parentId);
    };

    const renderSpan = (span: TraceSpan, depth: number = 0) => {
      const children = getChildren(span.span_id);
      const hasChildren = children.length > 0;
      const isExpanded = expandedSpans.has(span.span_id);
      const isSelected = selectedSpan?.span_id === span.span_id;

      return (
        <div key={span.span_id}>
          <div
            className={`flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors ${
              isSelected
                ? isDark ? 'bg-[#FF3621]/20 border-l-2 border-[#FF3621]' : 'bg-[#FF3621]/10 border-l-2 border-[#FF3621]'
                : isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'
            }`}
            style={{ paddingLeft: `${depth * 20 + 12}px` }}
            onClick={() => {
              setSelectedSpan(span);
              if (hasChildren) toggleSpan(span.span_id);
            }}
          >
            {hasChildren ? (
              isExpanded ? <ChevronDown className="h-4 w-4 flex-shrink-0" /> : <ChevronRight className="h-4 w-4 flex-shrink-0" />
            ) : (
              <div className="w-4" />
            )}
            <span className="text-base flex-shrink-0">{getSpanIcon(span.span_type)}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className={`text-sm font-medium truncate ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {span.name}
                </span>
                <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>was called</span>
              </div>
            </div>
            <span className={`text-xs flex-shrink-0 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              {formatDuration(span.duration_ms)}
            </span>
          </div>

          {isExpanded && children.map(child => renderSpan(child, depth + 1))}
        </div>
      );
    };

    return rootSpans.map(span => renderSpan(span));
  };

  const renderSpanDetails = (span: TraceSpan) => {
    // Extract the actual output content
    const getOutputContent = () => {
      if (!span.outputs) return null;

      // For agent span - show the final response
      if (span.span_type === 'AGENT' && span.outputs.response) {
        return { type: 'markdown', content: span.outputs.response };
      }

      // For LLM spans - show the assistant message
      if (span.span_type === 'LLM' && span.outputs.response?.choices?.[0]?.message) {
        const message = span.outputs.response.choices[0].message;
        if (message.content) {
          return { type: 'markdown', content: message.content };
        }
        if (message.tool_calls) {
          return { type: 'json', content: message.tool_calls };
        }
      }

      // For TOOL spans - show the result
      if (span.span_type === 'TOOL' && span.outputs.result) {
        try {
          const parsed = JSON.parse(span.outputs.result);
          return { type: 'json', content: parsed };
        } catch {
          return { type: 'text', content: span.outputs.result };
        }
      }

      return { type: 'json', content: span.outputs };
    };

    const outputContent = getOutputContent();

    return (
      <div className="h-full flex flex-col">
        <Tabs defaultValue="outputs" className="flex-1 flex flex-col">
          <TabsList className={isDark ? 'bg-white/5' : 'bg-gray-100'}>
            <TabsTrigger value="outputs">Output</TabsTrigger>
            <TabsTrigger value="inputs">Input</TabsTrigger>
            <TabsTrigger value="info">Info</TabsTrigger>
          </TabsList>

          <TabsContent value="outputs" className="flex-1 mt-4">
            <ScrollArea className="h-[600px]">
              <div className={`p-4 rounded-lg ${isDark ? 'bg-white/5' : 'bg-gray-50'}`}>
                {outputContent ? (
                  outputContent.type === 'markdown' ? (
                    <div className={`prose prose-sm max-w-none ${isDark ? 'prose-invert' : ''}`}>
                      <ReactMarkdown>{outputContent.content}</ReactMarkdown>
                    </div>
                  ) : outputContent.type === 'json' ? (
                    <pre className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'} whitespace-pre-wrap`}>
                      {JSON.stringify(outputContent.content, null, 2)}
                    </pre>
                  ) : (
                    <p className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'} whitespace-pre-wrap`}>
                      {outputContent.content}
                    </p>
                  )
                ) : (
                  <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>No output</p>
                )}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="inputs" className="flex-1 mt-4">
            <ScrollArea className="h-[600px]">
              <div className={`p-4 rounded-lg ${isDark ? 'bg-white/5' : 'bg-gray-50'}`}>
                {span.inputs && Object.keys(span.inputs).length > 0 ? (
                  <pre className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'} whitespace-pre-wrap`}>
                    {JSON.stringify(span.inputs, null, 2)}
                  </pre>
                ) : (
                  <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>No input</p>
                )}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="info" className="flex-1 mt-4">
            <ScrollArea className="h-[600px]">
              <div className="space-y-4">
                <div className={`p-4 rounded-lg ${isDark ? 'bg-white/5' : 'bg-gray-50'}`}>
                  <h3 className={`text-sm font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>Span Details</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Name:</span>
                      <span className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{span.name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Type:</span>
                      <Badge className={getStatusColor(span.span_type)}>{span.span_type}</Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Status:</span>
                      <Badge className={getStatusColor(span.status)}>{span.status}</Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Duration:</span>
                      <span className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{formatDuration(span.duration_ms)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Span ID:</span>
                      <span className={`text-xs font-mono ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{span.span_id.substring(0, 8)}</span>
                    </div>
                  </div>
                </div>

                {span.attributes && Object.keys(span.attributes).length > 0 && (
                  <div className={`p-4 rounded-lg ${isDark ? 'bg-white/5' : 'bg-gray-50'}`}>
                    <h3 className={`text-sm font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>Attributes</h3>
                    <pre className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'} whitespace-pre-wrap`}>
                      {JSON.stringify(span.attributes, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </div>
    );
  };

  if (loading && !selectedTrace) {
    return (
      <div className={`flex items-center justify-center h-screen ${isDark ? 'bg-[#1C3D42]' : 'bg-gray-50'}`}>
        <div className="text-center">
          <Activity className="h-8 w-8 animate-spin mx-auto mb-2" />
          <p className={isDark ? 'text-white' : 'text-gray-900'}>Loading traces...</p>
        </div>
      </div>
    );
  }

  if (!selectedTrace) {
    return (
      <div className={`h-full ${isDark ? 'bg-[#1C3D42]' : 'bg-gray-50'}`}>
        <div className="container mx-auto p-6">
          <div className="mb-6">
            <h1 className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Traces</h1>
            <p className={`mt-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              View execution traces from agent conversations
            </p>
          </div>

          <Card className={isDark ? 'bg-white/5 border-white/10' : 'bg-white'}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className={isDark ? 'text-white' : 'text-gray-900'}>Recent Traces</CardTitle>
                <Button
                  onClick={loadTraces}
                  variant="outline"
                  size="sm"
                  className={isDark ? 'bg-white/5 border-white/20 text-white hover:bg-white/10' : ''}
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh
                </Button>
              </div>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                {traces.length} trace{traces.length !== 1 ? 's' : ''} found
              </p>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {traces.map((trace) => (
                  <div
                    key={trace.trace_id}
                    className={`p-4 rounded-lg cursor-pointer transition-all border ${
                      isDark
                        ? 'bg-white/5 hover:bg-white/10 border-white/10'
                        : 'bg-gray-50 hover:bg-gray-100 border-gray-200'
                    }`}
                    onClick={() => loadTraceDetail(trace.trace_id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <span className={`text-xs font-mono ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                            {trace.trace_id.substring(0, 8)}
                          </span>
                          <Badge className={getStatusColor(trace.status)}>
                            {trace.status}
                          </Badge>
                        </div>
                        <p className={`text-sm truncate ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                          {trace.request_metadata?.current_user_message || 'No message'}
                        </p>
                      </div>
                      <div className="text-right ml-4">
                        <div className={`flex items-center gap-2 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                          <Clock className="h-4 w-4" />
                          {formatDuration(trace.execution_time_ms)}
                        </div>
                        <p className={`text-xs mt-1 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                          {formatTime(trace.timestamp_ms)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className={`h-full ${isDark ? 'bg-[#1C3D42]' : 'bg-gray-50'}`}>
      <div className="container mx-auto p-6 h-full flex flex-col">
        <div className="mb-6">
          <Button
            onClick={() => {
              setSelectedTrace(null);
              setSelectedSpan(null);
            }}
            variant="outline"
            className={`mb-4 ${isDark ? 'bg-white/5 border-white/20 text-white hover:bg-white/10' : ''}`}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Traces
          </Button>
          <div className="flex items-center justify-between">
            <div>
              <h1 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Trace Details</h1>
              <p className={`text-sm font-mono mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                ID: {selectedTrace.trace_id.substring(0, 16)}...
              </p>
            </div>
            <div className="text-right">
              <div className="flex items-center gap-2 mb-1">
                <Clock className="h-5 w-5" />
                <span className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {formatDuration(selectedTrace.execution_time_ms)}
                </span>
              </div>
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                {formatTime(selectedTrace.timestamp_ms)}
              </p>
            </div>
          </div>
        </div>

        <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-0">
          {/* Left panel - Trace breakdown */}
          <Card className={`lg:col-span-1 ${isDark ? 'bg-white/5 border-white/10' : 'bg-white'}`}>
            <CardHeader className="pb-3">
              <CardTitle className={`text-lg ${isDark ? 'text-white' : 'text-gray-900'}`}>
                Execution Timeline
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <ScrollArea className="h-[calc(100vh-300px)]">
                {buildSpanTree(selectedTrace.spans)}
              </ScrollArea>
            </CardContent>
          </Card>

          {/* Right panel - Span details */}
          <Card className={`lg:col-span-2 ${isDark ? 'bg-white/5 border-white/10' : 'bg-white'}`}>
            <CardHeader className="pb-3">
              <CardTitle className={`text-lg ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {selectedSpan ? (
                  <div className="flex items-center gap-2">
                    <span>{getSpanIcon(selectedSpan.span_type)}</span>
                    <span>{selectedSpan.name}</span>
                  </div>
                ) : (
                  'Select a span to view details'
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {selectedSpan ? (
                renderSpanDetails(selectedSpan)
              ) : (
                <div className={`text-center py-12 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  <Activity className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>Click on a span in the timeline to view its details</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

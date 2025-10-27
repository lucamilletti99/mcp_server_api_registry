"""Trace manager for storing and retrieving MCP tool execution traces."""

import json
import time
import uuid
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class TraceSpan(BaseModel):
  """Model for a trace span."""

  span_id: str
  name: str
  start_time_ms: int
  end_time_ms: Optional[int] = None
  duration_ms: Optional[float] = None
  parent_id: Optional[str] = None
  attributes: Dict[str, Any] = {}
  inputs: Optional[Dict[str, Any]] = None
  outputs: Optional[Dict[str, Any]] = None
  span_type: str = 'TOOL'  # TOOL, LLM, AGENT, etc.
  status: str = 'RUNNING'  # RUNNING, SUCCESS, ERROR

  def complete(self, outputs: Optional[Dict[str, Any]] = None, status: str = 'SUCCESS'):
    """Mark span as complete."""
    self.end_time_ms = int(time.time() * 1000)
    self.duration_ms = self.end_time_ms - self.start_time_ms
    if outputs is not None:
      self.outputs = outputs
    self.status = status


class Trace(BaseModel):
  """Model for a complete trace."""

  request_id: str
  trace_id: str
  timestamp_ms: int
  execution_time_ms: Optional[float] = None
  status: str = 'RUNNING'
  spans: List[TraceSpan] = []
  request_metadata: Dict[str, Any] = {}

  def complete(self, status: str = 'SUCCESS'):
    """Mark trace as complete."""
    self.status = status
    if self.spans:
      # Calculate total execution time from first to last span
      start_times = [s.start_time_ms for s in self.spans if s.start_time_ms]
      end_times = [
        s.end_time_ms for s in self.spans if s.end_time_ms and s.end_time_ms > 0
      ]
      if start_times and end_times:
        self.execution_time_ms = max(end_times) - min(start_times)


class TraceManager:
  """Manager for storing and retrieving traces."""

  def __init__(self, max_traces: int = 100):
    """Initialize trace manager.

    Args:
        max_traces: Maximum number of traces to keep in memory
    """
    self.max_traces = max_traces
    self.traces: Dict[str, Trace] = {}
    self.active_traces: Dict[str, Trace] = {}  # Currently running traces
    self.trace_order: List[str] = []  # For maintaining chronological order

  def create_trace(self, request_metadata: Optional[Dict[str, Any]] = None) -> str:
    """Create a new trace.

    Args:
        request_metadata: Metadata about the request

    Returns:
        The trace_id for the new trace
    """
    trace_id = str(uuid.uuid4())
    trace = Trace(
      request_id=trace_id,
      trace_id=trace_id,
      timestamp_ms=int(time.time() * 1000),
      request_metadata=request_metadata or {}
    )

    self.traces[trace_id] = trace
    self.active_traces[trace_id] = trace
    self.trace_order.append(trace_id)

    # Trim old traces if we exceed max
    if len(self.trace_order) > self.max_traces:
      old_trace_id = self.trace_order.pop(0)
      self.traces.pop(old_trace_id, None)
      self.active_traces.pop(old_trace_id, None)

    return trace_id

  def add_span(
    self,
    trace_id: str,
    name: str,
    inputs: Optional[Dict[str, Any]] = None,
    parent_id: Optional[str] = None,
    span_type: str = 'TOOL',
    attributes: Optional[Dict[str, Any]] = None
  ) -> str:
    """Add a span to a trace.

    Args:
        trace_id: The trace to add the span to
        name: Name of the span (e.g., tool name)
        inputs: Input parameters
        parent_id: Parent span ID for nested calls
        span_type: Type of span (TOOL, LLM, AGENT)
        attributes: Additional attributes

    Returns:
        The span_id
    """
    if trace_id not in self.traces:
      raise ValueError(f'Trace {trace_id} not found')

    span_id = str(uuid.uuid4())
    span = TraceSpan(
      span_id=span_id,
      name=name,
      start_time_ms=int(time.time() * 1000),
      parent_id=parent_id,
      inputs=inputs,
      span_type=span_type,
      attributes=attributes or {}
    )

    self.traces[trace_id].spans.append(span)
    return span_id

  def complete_span(
    self,
    trace_id: str,
    span_id: str,
    outputs: Optional[Dict[str, Any]] = None,
    status: str = 'SUCCESS'
  ):
    """Mark a span as complete.

    Args:
        trace_id: The trace ID
        span_id: The span ID to complete
        outputs: Output data
        status: Final status (SUCCESS or ERROR)
    """
    if trace_id not in self.traces:
      raise ValueError(f'Trace {trace_id} not found')

    trace = self.traces[trace_id]
    for span in trace.spans:
      if span.span_id == span_id:
        span.complete(outputs, status)
        break

  def complete_trace(self, trace_id: str, status: str = 'SUCCESS'):
    """Mark a trace as complete.

    Args:
        trace_id: The trace ID
        status: Final status
    """
    if trace_id not in self.traces:
      raise ValueError(f'Trace {trace_id} not found')

    self.traces[trace_id].complete(status)
    self.active_traces.pop(trace_id, None)

  def get_trace(self, trace_id: str) -> Optional[Trace]:
    """Get a trace by ID.

    Args:
        trace_id: The trace ID

    Returns:
        The trace or None if not found
    """
    return self.traces.get(trace_id)

  def list_traces(self, limit: int = 50, offset: int = 0) -> List[Trace]:
    """List traces in reverse chronological order.

    Args:
        limit: Maximum number of traces to return
        offset: Number of traces to skip

    Returns:
        List of traces
    """
    # Return in reverse chronological order (newest first)
    trace_ids = list(reversed(self.trace_order))
    selected_ids = trace_ids[offset:offset + limit]
    return [self.traces[tid] for tid in selected_ids if tid in self.traces]

  @contextmanager
  def trace_span(
    self,
    trace_id: str,
    name: str,
    inputs: Optional[Dict[str, Any]] = None,
    parent_id: Optional[str] = None,
    span_type: str = 'TOOL'
  ):
    """Context manager for tracing a span.

    Args:
        trace_id: The trace ID
        name: Name of the span
        inputs: Input parameters
        parent_id: Parent span ID
        span_type: Type of span

    Yields:
        A dict to store outputs
    """
    span_id = self.add_span(trace_id, name, inputs, parent_id, span_type)
    outputs = {}
    status = 'SUCCESS'

    try:
      yield outputs
    except Exception as e:
      status = 'ERROR'
      outputs['error'] = str(e)
      raise
    finally:
      self.complete_span(trace_id, span_id, outputs, status)


# Global trace manager instance
_trace_manager = TraceManager(max_traces=100)


def get_trace_manager() -> TraceManager:
  """Get the global trace manager instance."""
  return _trace_manager

"""Traces router for MCP tool execution trace visualization."""

from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.trace_manager import Trace, TraceSpan, get_trace_manager

router = APIRouter()


class TraceListResponse(BaseModel):
  """Response model for trace list."""

  traces: List[Trace]
  total: int


@router.get('/list', response_model=TraceListResponse)
async def list_traces(limit: int = 50, offset: int = 0) -> TraceListResponse:
  """List recent traces.

  Args:
      limit: Maximum number of traces to return (default: 50)
      offset: Number of traces to skip (default: 0)

  Returns:
      List of traces with metadata
  """
  try:
    trace_manager = get_trace_manager()
    traces = trace_manager.list_traces(limit=limit, offset=offset)

    return TraceListResponse(traces=traces, total=len(trace_manager.traces))

  except Exception as e:
    print(f'❌ Error listing traces: {str(e)}')
    raise HTTPException(status_code=500, detail=f'Error listing traces: {str(e)}')


@router.get('/{trace_id}', response_model=Trace)
async def get_trace(trace_id: str) -> Trace:
  """Get detailed trace information by ID.

  Args:
      trace_id: The trace ID to retrieve

  Returns:
      Complete trace with all spans and metadata
  """
  try:
    trace_manager = get_trace_manager()
    trace = trace_manager.get_trace(trace_id)

    if not trace:
      raise HTTPException(status_code=404, detail=f'Trace {trace_id} not found')

    return trace

  except HTTPException:
    raise
  except Exception as e:
    print(f'❌ Error getting trace: {str(e)}')
    raise HTTPException(status_code=500, detail=f'Error getting trace: {str(e)}')

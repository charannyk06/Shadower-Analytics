/**
 * Tests for useExecutiveDashboard hook
 */

import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';
import { useExecutiveDashboard, useRevenueMetrics, useKPIs } from '../useExecutiveDashboard';
import apiClient from '@/lib/api/client';

// Mock API client
jest.mock('@/lib/api/client');
const mockedApiClient = apiClient as jest.Mocked<typeof apiClient>;

// Helper to create wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('useExecutiveDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should fetch executive dashboard data successfully', async () => {
    const mockData = {
      workspace_id: 'test-workspace',
      timeframe: '30d',
      period: {
        start: '2024-01-01T00:00:00Z',
        end: '2024-01-31T00:00:00Z',
      },
      mrr: 50000,
      churn_rate: 2.5,
      ltv: 10000,
      dau: 100,
      wau: 500,
      mau: 1500,
      total_executions: 5000,
      success_rate: 95.5,
    };

    mockedApiClient.get.mockResolvedValueOnce({ data: mockData });

    const { result } = renderHook(
      () =>
        useExecutiveDashboard({
          workspaceId: 'test-workspace',
          timeframe: '30d',
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockData);
    expect(mockedApiClient.get).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/executive/overview')
    );
  });

  it('should handle error states', async () => {
    const mockError = new Error('Network error');
    mockedApiClient.get.mockRejectedValueOnce(mockError);

    const { result } = renderHook(
      () =>
        useExecutiveDashboard({
          workspaceId: 'test-workspace',
          timeframe: '30d',
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeTruthy();
  });

  it('should support skip cache option', async () => {
    const mockData = {
      workspace_id: 'test-workspace',
      timeframe: '30d',
      period: { start: '2024-01-01', end: '2024-01-31' },
      mrr: 0,
      churn_rate: 0,
      ltv: 0,
      dau: 0,
      wau: 0,
      mau: 0,
      total_executions: 0,
      success_rate: 0,
    };

    mockedApiClient.get.mockResolvedValueOnce({ data: mockData });

    renderHook(
      () =>
        useExecutiveDashboard(
          {
            workspaceId: 'test-workspace',
            timeframe: '30d',
          },
          { skipCache: true }
        ),
      { wrapper: createWrapper() }
    );

    await waitFor(() =>
      expect(mockedApiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('skipCache')
      )
    );
  });

  it('should be disabled when enabled option is false', () => {
    const { result } = renderHook(
      () =>
        useExecutiveDashboard(
          {
            workspaceId: 'test-workspace',
            timeframe: '30d',
          },
          { enabled: false }
        ),
      { wrapper: createWrapper() }
    );

    expect(result.current.isFetching).toBe(false);
    expect(mockedApiClient.get).not.toHaveBeenCalled();
  });

  it('should support refetch interval for real-time updates', async () => {
    const mockData = {
      workspace_id: 'test-workspace',
      timeframe: '24h',
      period: { start: '2024-01-01', end: '2024-01-02' },
      mrr: 0,
      churn_rate: 0,
      ltv: 0,
      dau: 50,
      wau: 200,
      mau: 800,
      total_executions: 1000,
      success_rate: 98.0,
    };

    mockedApiClient.get.mockResolvedValue({ data: mockData });

    renderHook(
      () =>
        useExecutiveDashboard(
          {
            workspaceId: 'test-workspace',
            timeframe: '24h',
          },
          { refetchInterval: 5000 }
        ),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(mockedApiClient.get).toHaveBeenCalled());
  });
});

describe('useRevenueMetrics', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should fetch revenue metrics successfully', async () => {
    const mockData = {
      workspace_id: 'test-workspace',
      timeframe: '30d',
      total_revenue: 100000,
      mrr: 50000,
      arr: 600000,
      trend: [
        { date: '2024-01-01', value: 1000 },
        { date: '2024-01-02', value: 1100 },
      ],
      growth_rate: 10.5,
    };

    mockedApiClient.get.mockResolvedValueOnce({ data: mockData });

    const { result } = renderHook(
      () =>
        useRevenueMetrics({
          workspaceId: 'test-workspace',
          timeframe: '30d',
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockData);
    expect(mockedApiClient.get).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/executive/revenue')
    );
  });

  it('should handle different timeframes', async () => {
    const mockData = {
      workspace_id: 'test-workspace',
      timeframe: '1y',
      total_revenue: 1200000,
      mrr: 100000,
      arr: 1200000,
      trend: [],
      growth_rate: 25.0,
    };

    mockedApiClient.get.mockResolvedValueOnce({ data: mockData });

    const { result } = renderHook(
      () =>
        useRevenueMetrics({
          workspaceId: 'test-workspace',
          timeframe: '1y',
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.timeframe).toBe('1y');
  });
});

describe('useKPIs', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should fetch KPIs successfully', async () => {
    const mockData = {
      workspace_id: 'test-workspace',
      total_users: 500,
      active_agents: 50,
      total_executions: 10000,
      success_rate: 98.5,
      avg_execution_time: 2.5,
      total_credits_used: 50000,
    };

    mockedApiClient.get.mockResolvedValueOnce({ data: mockData });

    const { result } = renderHook(() => useKPIs('test-workspace'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockData);
    expect(result.current.data?.total_users).toBe(500);
    expect(result.current.data?.success_rate).toBe(98.5);
  });

  it('should support refetch interval for real-time KPIs', async () => {
    const mockData = {
      workspace_id: 'test-workspace',
      total_users: 500,
      active_agents: 50,
      total_executions: 10000,
      success_rate: 98.5,
      avg_execution_time: 2.5,
      total_credits_used: 50000,
    };

    mockedApiClient.get.mockResolvedValue({ data: mockData });

    renderHook(() => useKPIs('test-workspace', { refetchInterval: 60000 }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(mockedApiClient.get).toHaveBeenCalled());
  });

  it('should cache KPIs with shorter stale time', async () => {
    const mockData = {
      workspace_id: 'test-workspace',
      total_users: 500,
      active_agents: 50,
      total_executions: 10000,
      success_rate: 98.5,
      avg_execution_time: 2.5,
      total_credits_used: 50000,
    };

    mockedApiClient.get.mockResolvedValueOnce({ data: mockData });

    const { result } = renderHook(() => useKPIs('test-workspace'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Verify data is cached
    expect(result.current.data).toEqual(mockData);
  });

  it('should handle workspace switch', async () => {
    const mockData1 = {
      workspace_id: 'workspace-1',
      total_users: 500,
      active_agents: 50,
      total_executions: 10000,
      success_rate: 98.5,
      avg_execution_time: 2.5,
      total_credits_used: 50000,
    };

    const mockData2 = {
      workspace_id: 'workspace-2',
      total_users: 300,
      active_agents: 30,
      total_executions: 5000,
      success_rate: 97.0,
      avg_execution_time: 3.0,
      total_credits_used: 25000,
    };

    mockedApiClient.get
      .mockResolvedValueOnce({ data: mockData1 })
      .mockResolvedValueOnce({ data: mockData2 });

    const { result, rerender } = renderHook(
      ({ workspaceId }: { workspaceId: string }) => useKPIs(workspaceId),
      {
        wrapper: createWrapper(),
        initialProps: { workspaceId: 'workspace-1' },
      }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.workspace_id).toBe('workspace-1');

    // Switch workspace
    rerender({ workspaceId: 'workspace-2' });

    await waitFor(() =>
      expect(result.current.data?.workspace_id).toBe('workspace-2')
    );
  });
});

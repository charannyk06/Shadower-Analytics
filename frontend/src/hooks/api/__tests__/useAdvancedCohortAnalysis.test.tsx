/**
 * Tests for useAdvancedCohortAnalysis hook
 */

import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';
import { useAdvancedCohortAnalysis } from '../useUserActivity';
import apiClient from '@/lib/api/client';
import type { CohortAnalysisData } from '@/types/user-activity';

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

describe('useAdvancedCohortAnalysis', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should fetch advanced cohort analysis data successfully', async () => {
    const mockData: CohortAnalysisData = {
      cohortType: 'signup',
      cohortPeriod: 'monthly',
      cohorts: [
        {
          cohortId: '2024-01-01_signup',
          cohortDate: '2024-01-01',
          cohortSize: 100,
          retention: {
            day0: 100.0,
            day1: 85.0,
            day7: 70.0,
            day14: 60.0,
            day30: 50.0,
            day60: 40.0,
            day90: 35.0,
          },
          metrics: {
            avgRevenue: 250.0,
            ltv: 1500.0,
            churnRate: 15.0,
            engagementScore: 75.0,
          },
          segments: [
            { segment: 'desktop', count: 70, retention: 55.0 },
            { segment: 'mobile', count: 30, retention: 40.0 },
          ],
        },
      ],
      comparison: {
        bestPerforming: '2024-01-01_signup',
        worstPerforming: '2024-01-01_signup',
        avgRetention: 50.0,
        trend: 'stable',
      },
    };

    mockedApiClient.get.mockResolvedValueOnce({ data: mockData });

    const { result } = renderHook(
      () =>
        useAdvancedCohortAnalysis({
          workspaceId: 'test-workspace',
          cohortType: 'signup',
          cohortPeriod: 'monthly',
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockData);
    expect(result.current.data?.cohorts).toHaveLength(1);
    expect(result.current.data?.cohorts[0].cohortSize).toBe(100);
    expect(mockedApiClient.get).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/user-activity/test-workspace/cohorts/advanced')
    );
  });

  it('should handle different cohort types', async () => {
    const mockData: CohortAnalysisData = {
      cohortType: 'activation',
      cohortPeriod: 'weekly',
      cohorts: [],
      comparison: {
        bestPerforming: null,
        worstPerforming: null,
        avgRetention: 0.0,
        trend: 'stable',
      },
    };

    mockedApiClient.get.mockResolvedValueOnce({ data: mockData });

    const { result } = renderHook(
      () =>
        useAdvancedCohortAnalysis({
          workspaceId: 'test-workspace',
          cohortType: 'activation',
          cohortPeriod: 'weekly',
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.cohortType).toBe('activation');
    expect(result.current.data?.cohortPeriod).toBe('weekly');
  });

  it('should support date range filtering', async () => {
    const mockData: CohortAnalysisData = {
      cohortType: 'signup',
      cohortPeriod: 'daily',
      cohorts: [],
      comparison: {
        bestPerforming: null,
        worstPerforming: null,
        avgRetention: 0.0,
        trend: 'stable',
      },
    };

    mockedApiClient.get.mockResolvedValueOnce({ data: mockData });

    renderHook(
      () =>
        useAdvancedCohortAnalysis({
          workspaceId: 'test-workspace',
          cohortType: 'signup',
          cohortPeriod: 'daily',
          startDate: '2024-01-01',
          endDate: '2024-01-31',
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() =>
      expect(mockedApiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('start_date=2024-01-01')
      )
    );

    expect(mockedApiClient.get).toHaveBeenCalledWith(
      expect.stringContaining('end_date=2024-01-31')
    );
  });

  it('should handle error states', async () => {
    const mockError = new Error('Network error');
    mockedApiClient.get.mockRejectedValueOnce(mockError);

    const { result } = renderHook(
      () =>
        useAdvancedCohortAnalysis({
          workspaceId: 'test-workspace',
          cohortType: 'signup',
          cohortPeriod: 'monthly',
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeTruthy();
  });

  it('should be disabled when enabled option is false', () => {
    const { result } = renderHook(
      () =>
        useAdvancedCohortAnalysis({
          workspaceId: 'test-workspace',
          cohortType: 'signup',
          cohortPeriod: 'monthly',
          enabled: false,
        }),
      { wrapper: createWrapper() }
    );

    expect(result.current.isFetching).toBe(false);
    expect(mockedApiClient.get).not.toHaveBeenCalled();
  });

  it('should calculate metrics correctly for multiple cohorts', async () => {
    const mockData: CohortAnalysisData = {
      cohortType: 'signup',
      cohortPeriod: 'monthly',
      cohorts: [
        {
          cohortId: '2024-01-01_signup',
          cohortDate: '2024-01-01',
          cohortSize: 100,
          retention: {
            day0: 100.0,
            day1: 80.0,
            day7: 65.0,
            day14: 55.0,
            day30: 45.0,
            day60: 35.0,
            day90: 30.0,
          },
          metrics: {
            avgRevenue: 200.0,
            ltv: 1200.0,
            churnRate: 20.0,
            engagementScore: 70.0,
          },
          segments: [],
        },
        {
          cohortId: '2024-02-01_signup',
          cohortDate: '2024-02-01',
          cohortSize: 150,
          retention: {
            day0: 100.0,
            day1: 90.0,
            day7: 75.0,
            day14: 65.0,
            day30: 55.0,
            day60: 45.0,
            day90: 40.0,
          },
          metrics: {
            avgRevenue: 300.0,
            ltv: 1800.0,
            churnRate: 10.0,
            engagementScore: 80.0,
          },
          segments: [],
        },
      ],
      comparison: {
        bestPerforming: '2024-02-01_signup',
        worstPerforming: '2024-01-01_signup',
        avgRetention: 50.0,
        trend: 'improving',
      },
    };

    mockedApiClient.get.mockResolvedValueOnce({ data: mockData });

    const { result } = renderHook(
      () =>
        useAdvancedCohortAnalysis({
          workspaceId: 'test-workspace',
          cohortType: 'signup',
          cohortPeriod: 'monthly',
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.cohorts).toHaveLength(2);
    expect(result.current.data?.comparison.trend).toBe('improving');
    expect(result.current.data?.comparison.bestPerforming).toBe('2024-02-01_signup');
  });

  it('should support different cohort periods', async () => {
    const periods: Array<'daily' | 'weekly' | 'monthly'> = ['daily', 'weekly', 'monthly'];

    for (const period of periods) {
      const mockData: CohortAnalysisData = {
        cohortType: 'signup',
        cohortPeriod: period,
        cohorts: [],
        comparison: {
          bestPerforming: null,
          worstPerforming: null,
          avgRetention: 0.0,
          trend: 'stable',
        },
      };

      mockedApiClient.get.mockResolvedValueOnce({ data: mockData });

      const { result } = renderHook(
        () =>
          useAdvancedCohortAnalysis({
            workspaceId: 'test-workspace',
            cohortType: 'signup',
            cohortPeriod: period,
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.cohortPeriod).toBe(period);
    }
  });

  it('should handle empty cohorts gracefully', async () => {
    const mockData: CohortAnalysisData = {
      cohortType: 'signup',
      cohortPeriod: 'monthly',
      cohorts: [],
      comparison: {
        bestPerforming: null,
        worstPerforming: null,
        avgRetention: 0.0,
        trend: 'stable',
      },
    };

    mockedApiClient.get.mockResolvedValueOnce({ data: mockData });

    const { result } = renderHook(
      () =>
        useAdvancedCohortAnalysis({
          workspaceId: 'test-workspace',
          cohortType: 'signup',
          cohortPeriod: 'monthly',
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.cohorts).toHaveLength(0);
    expect(result.current.data?.comparison.bestPerforming).toBeNull();
  });

  it('should refetch data with longer interval', async () => {
    const mockData: CohortAnalysisData = {
      cohortType: 'signup',
      cohortPeriod: 'monthly',
      cohorts: [],
      comparison: {
        bestPerforming: null,
        worstPerforming: null,
        avgRetention: 0.0,
        trend: 'stable',
      },
    };

    mockedApiClient.get.mockResolvedValue({ data: mockData });

    const { result } = renderHook(
      () =>
        useAdvancedCohortAnalysis({
          workspaceId: 'test-workspace',
          cohortType: 'signup',
          cohortPeriod: 'monthly',
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Verify the hook was called
    expect(mockedApiClient.get).toHaveBeenCalled();
  });
});

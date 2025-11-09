/**
 * User activity tracking types
 */

export type TimeFrame = '7d' | '30d' | '90d' | '1y'

export interface ActivityByDate {
  date: string
  activeUsers: number
  sessions: number
  events: number
}

export interface ActivityMetrics {
  dau: number
  wau: number
  mau: number
  newUsers: number
  returningUsers: number
  reactivatedUsers: number
  churnedUsers: number
  avgSessionsPerUser: number
  avgSessionDuration: number
  bounceRate: number
  engagementScore: number
  activityByHour: number[]
  activityByDayOfWeek: number[]
  activityByDate: ActivityByDate[]
}

export interface SessionLengthDistribution {
  '0-30s': number
  '30s-2m': number
  '2m-5m': number
  '5m-15m': number
  '15m-30m': number
  '30m+': number
}

export interface DeviceBreakdown {
  desktop: number
  mobile: number
  tablet: number
}

export interface LocationData {
  users: number
  sessions: number
}

export interface SessionAnalytics {
  totalSessions: number
  avgSessionLength: number
  medianSessionLength: number
  sessionLengthDistribution: SessionLengthDistribution
  deviceBreakdown: DeviceBreakdown
  browserBreakdown: Record<string, number>
  locationBreakdown: Record<string, LocationData>
}

export interface FeatureData {
  featureName: string
  category: string
  usageCount: number
  uniqueUsers: number
  avgTimeSpent: number
  adoptionRate: number
  retentionRate: number
}

export interface AdoptionFunnelStage {
  stage: string
  users: number
  dropoffRate: number
}

export interface TopFeature {
  feature: string
  usage: number
  trend: 'increasing' | 'stable' | 'decreasing'
}

export interface UnusedFeature {
  feature: string
  lastUsed: string | null
}

export interface FeatureUsage {
  features: FeatureData[]
  adoptionFunnel: AdoptionFunnelStage[]
  topFeatures: TopFeature[]
  unusedFeatures: UnusedFeature[]
}

export interface DropoffPoint {
  step: string
  dropoffRate: number
}

export interface CommonPath {
  path: string[]
  frequency: number
  avgCompletion: number
  dropoffPoints: DropoffPoint[]
}

export interface EntryPoint {
  page: string
  count: number
  bounceRate: number
}

export interface ExitPoint {
  page: string
  count: number
  avgTimeBeforeExit: number
}

export interface ConversionPathData {
  steps: string[]
  conversions: number
  conversionRate: number
}

export interface ConversionPath {
  goal: string
  paths: ConversionPathData[]
}

export interface UserJourney {
  commonPaths: CommonPath[]
  entryPoints: EntryPoint[]
  exitPoints: ExitPoint[]
  conversionPaths: ConversionPath[]
}

export interface RetentionCurvePoint {
  day: number
  retentionRate: number
  activeUsers: number
}

export interface CohortRetention {
  day1: number
  day7: number
  day14: number
  day30: number
  day60: number
  day90: number
}

export interface Cohort {
  cohortDate: string
  cohortSize: number
  retention: CohortRetention
}

export interface RiskSegment {
  segment: string
  users: number
  churnProbability: number
  characteristics: string[]
}

export interface ChurnAnalysis {
  churnRate: number
  avgLifetime: number
  riskSegments: RiskSegment[]
}

export interface Retention {
  retentionCurve: RetentionCurvePoint[]
  cohorts: Cohort[]
  churnAnalysis: ChurnAnalysis
}

export type SegmentType = 'behavioral' | 'demographic' | 'technographic'

export interface UserSegmentData {
  segmentName: string
  segmentType: SegmentType
  userCount: number
  characteristics: string[]
  avgEngagement: number
  avgRevenue: number
}

export interface UserActivityData {
  userId?: string
  workspaceId: string
  timeframe: TimeFrame
  activityMetrics: ActivityMetrics
  sessionAnalytics: SessionAnalytics
  featureUsage: FeatureUsage
  userJourney: UserJourney
  retention: Retention
  segments: UserSegmentData[]
}

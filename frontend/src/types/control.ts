export interface SiteSettings {
  whitelist_mode_enabled: boolean
  signup_disabled: boolean
  updated_at: string
}

export interface UserStatus {
  value: 'pending' | 'approved' | 'suspended' | 'banned'
  label: string
}

export interface User {
  id: number
  email: string
  username: string | null
  display_name: string
  status: 'pending' | 'approved' | 'suspended' | 'banned'
  status_display?: string
  is_email_verified: boolean
  is_staff: boolean
  is_active: boolean
  created_at: string
  updated_at: string
  last_login: string | null
}

export interface UserAnalytics {
  total_users: number
  users_last_week: number
  pending_users: number
  approved_users: number
  suspended_users: number
  banned_users: number
  recent_signups: Array<{
    date: string
    count: number
  }>
}

export interface QuickStats {
  total_users: number
  users_last_week: number
  pending_users: number
}

export interface ControlPanelOverview {
  site_settings: SiteSettings
  quick_stats: QuickStats
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export const USER_STATUS_CHOICES: UserStatus[] = [
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'suspended', label: 'Suspended' },
  { value: 'banned', label: 'Banned' }
]

export const USER_STATUS_COLORS = {
  pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  approved: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  suspended: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  banned: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
}
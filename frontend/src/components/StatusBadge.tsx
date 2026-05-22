import clsx from 'clsx'

const STATUS_STYLES: Record<string, string> = {
  // Job statuses
  discovered:   'bg-parchment-200 text-gray-700',
  saved:        'bg-blue-100 text-blue-700',
  applying:     'bg-yellow-100 text-yellow-700',
  applied:      'bg-purple-100 text-purple-700',
  dropped:      'bg-red-100 text-red-700',
  // Application statuses
  pending:      'bg-parchment-200 text-gray-700',
  in_review:    'bg-blue-100 text-blue-700',
  phone_screen: 'bg-cyan-100 text-cyan-700',
  interview:    'bg-indigo-100 text-indigo-700',
  offer:        'bg-emerald-100 text-emerald-700',
  rejected:     'bg-red-100 text-red-700',
  withdrawn:    'bg-gray-200 text-gray-700',
  // Automation
  running:      'bg-green-100 text-green-700',
  paused:       'bg-yellow-100 text-yellow-700',
  done:         'bg-emerald-100 text-emerald-700',
  error:        'bg-red-100 text-red-700',
}

const LABELS: Record<string, string> = {
  discovered: 'Discovered',
  saved: 'Saved',
  applying: 'Applying',
  applied: 'Applied',
  dropped: 'Dropped',
  pending: 'Pending',
  in_review: 'In Review',
  phone_screen: 'Phone Screen',
  interview: 'Interview',
  offer: 'Offer',
  rejected: 'Rejected',
  withdrawn: 'Withdrawn',
  running: 'Running',
  paused: 'Paused',
  done: 'Done',
  error: 'Error',
}

interface Props {
  status: string
  size?: 'sm' | 'md'
}

export function StatusBadge({ status, size = 'md' }: Props) {
  return (
    <span className={clsx(
      'badge',
      STATUS_STYLES[status] ?? 'bg-parchment-200 text-gray-700',
      size === 'sm' && 'text-[10px] px-2 py-0',
    )}>
      {LABELS[status] ?? status}
    </span>
  )
}

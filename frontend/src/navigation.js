import {
  AtSign,
  BarChart3,
  Bot,
  Briefcase,
  CalendarClock,
  Crown,
  FileText,
  FolderKanban,
  Gauge,
  Inbox as InboxIcon,
  Mail,
  MessageSquare,
  Reply,
  Send,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Users,
  Workflow,
  Zap,
} from 'lucide-react'

export const getNavigationGroups = (isAdmin) => {
  const groups = [
    { name: 'Inbox', icon: InboxIcon, expanded: false, items: [{ id: 'inbox', name: 'Inbox', icon: Mail }] },
    {
      name: 'Intelligence',
      icon: Sparkles,
      expanded: false,
      items: [
        { id: 'insights', name: 'Insights', icon: BarChart3 },
        { id: 'relationships', name: 'Relationships', icon: Users },
        { id: 'executive', name: 'Executive AI', icon: Crown },
      ],
    },
    {
      name: 'Automation',
      icon: Workflow,
      expanded: false,
      items: [
        { id: 'workflows', name: 'Workflows', icon: Workflow },
        { id: 'agents', name: 'Agents', icon: Bot },
        { id: 'campaigns', name: 'Campaigns', icon: Send },
        { id: 'auto-reply', name: 'Auto-Reply', icon: Zap },
        { id: 'followups', name: 'Follow-Ups', icon: Reply },
      ],
    },
    {
      name: 'Operations',
      icon: Briefcase,
      expanded: false,
      items: [
        { id: 'briefings', name: 'Daily Briefing', icon: CalendarClock },
        { id: 'shared-inbox', name: 'Shared Inbox', icon: InboxIcon },
        { id: 'deliverability', name: 'Deliverability', icon: Gauge },
        { id: 'hosted-email', name: 'Hosted Email', icon: AtSign },
      ],
    },
    {
      name: 'Workspace',
      icon: FolderKanban,
      expanded: false,
      items: [
        { id: 'email-accounts', name: 'Email Accounts', icon: Mail },
        { id: 'agent', name: 'Email Agent', icon: MessageSquare },
        { id: 'drafts', name: 'Drafts', icon: FileText },
        { id: 'prompts', name: 'Prompt Brain', icon: Settings },
      ],
    },
  ]

  if (isAdmin) {
    groups.push({
      name: 'Admin',
      icon: ShieldCheck,
      expanded: false,
      items: [
        { id: 'admin-dashboard', name: 'Dashboard', icon: BarChart3 },
        { id: 'admin-llm', name: 'LLM Ops', icon: Settings },
        { id: 'admin-user-access', name: 'User Access', icon: ShieldCheck },
        { id: 'admin-feature-rules', name: 'Feature Rules', icon: SlidersHorizontal },
      ],
    })
  }

  return groups
}

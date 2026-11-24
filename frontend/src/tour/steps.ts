import { api } from '../api'

export type Step = {
  id: string
  title: string
  body: string
  /** CSS selector of the element to spotlight. Omit for a centred card. */
  target?: string
  /** Page to show for this step (a function may look up a real record first). */
  route?: string | (() => Promise<string>)
  /** Only shown to roles that can access this section (see ACCESS in auth.tsx). */
  section?: string
}

const topIssue = async () => {
  const rows = await api('/issues')
  return rows.length ? `/issues/${rows[0].id}` : '/issues'
}

const criticalComplaint = async () => {
  const r = await api('/complaints?severity=critical&page_size=1')
  return r.items.length ? `/complaints/${r.items[0].id}` : '/complaints'
}

export const STEPS: Step[] = [
  {
    id: 'welcome',
    route: '/',
    title: 'Welcome to the Quality AI Platform',
    body:
      'A tour of how customer complaints become decisions: AI triage, recurring-failure detection, escalation rules, ' +
      'drafted replies and an operations assistant. Everything here uses fictional data. Use the arrow keys or the buttons below.',
  },
  {
    id: 'nav',
    route: '/',
    target: '[data-tour="nav"]',
    title: 'Role-based access',
    body:
      'The menu adapts to your role: Quality sees complaints, issues and reports; Finance does not. The API enforces the same ' +
      'rules, so hiding a menu item is never the only protection.',
  },
  {
    id: 'kpis',
    route: '/',
    target: '[data-tour="kpis"]',
    title: 'Executive overview',
    body:
      'Live KPIs: critical complaints still waiting for a reply, open escalations, recurring quality issues, and the share of ' +
      'complaints triaged by AI without human effort.',
  },
  {
    id: 'chart-days',
    route: '/',
    target: '[data-tour="chart-days"]',
    title: 'Volume over time, by severity',
    body:
      'Complaints per day, stacked by severity. A growing orange or red band is an early warning: you see a problem forming ' +
      'before anyone has to read individual emails.',
  },
  {
    id: 'chart-category',
    route: '/',
    target: '[data-tour="chart-category"]',
    title: 'What customers complain about',
    body:
      'The AI classifies every complaint into one of ten categories (foreign object, allergen, spoilage, cold chain, packaging, ' +
      'billing and more). The ranking shows where the volume is, so the team knows what to fix first.',
  },
  {
    id: 'top-issues',
    route: '/',
    target: '[data-tour="top-issues"]',
    title: 'Recurring failures, ranked',
    body:
      'Similar complaints are grouped into one quality issue, with the product, the lot codes involved and the worst severity ' +
      'seen. Open one to see its complaints and the related production records.',
  },
  {
    id: 'top-lots',
    route: '/',
    target: '[data-tour="top-lots"]',
    title: 'Which production lots are involved',
    body:
      'Complaints that mention a lot code are counted per lot. Three or more on the same lot within 30 days escalates ' +
      'automatically, and a lot like this is a candidate for a stock hold.',
  },
  {
    id: 'ops-snapshot',
    section: 'ops-snapshot',
    route: '/',
    target: '[data-tour="ops-snapshot"]',
    title: 'Manufacturing and supply chain at a glance',
    body:
      'Defect rate and yield over 14 days, late purchase orders, and every inventory item below its reorder point. Quality ' +
      'problems can be read next to production and supply risk, in one place.',
  },
  {
    id: 'finance-snapshot',
    section: 'finance-snapshot',
    route: '/',
    target: '[data-tour="finance-snapshot"]',
    title: 'Finance snapshot',
    body:
      'Overdue receivables across customers. The operations assistant can list the individual invoices, but only for roles that ' +
      'are allowed to see finance data.',
  },
  {
    id: 'issue',
    section: 'issues',
    route: topIssue,
    target: '[data-tour="lot-production"]',
    title: 'A recurring failure, traced to a production lot',
    body:
      'Complaints are clustered by meaning, product and lot. This cluster points to specific lots, and their production records ' +
      'show a defect rate well above the plant’s normal ~1%. Linking customer complaints to manufacturing data is what turns ' +
      'support tickets into a quality investigation.',
  },
  {
    id: 'escalation',
    section: 'complaints',
    route: criticalComplaint,
    target: '[data-tour="escalation"]',
    title: 'Escalation by rules, not by opinion',
    body:
      'The model suggests a severity, but deterministic business rules decide. Health risk, foreign objects, undeclared allergens, ' +
      'legal language or several complaints on the same lot all force escalation, and the model can never lower the result.',
  },
  {
    id: 'draft',
    section: 'complaints',
    route: criticalComplaint,
    target: '[data-tour="draft"]',
    title: 'A grounded reply, with human approval',
    body:
      'The draft is written from the company’s own policies (sources are listed under it) and checked by guardrails: no ' +
      'admitting liability, no money amounts, no recall talk. High and critical replies are never sent automatically: only the ' +
      'Quality role can approve them.',
  },
  {
    id: 'bell',
    target: '[data-tour="bell"]',
    title: 'Notifications by role',
    body:
      'Escalations and newly detected recurring issues notify the owning team (here, Quality). Critical cases also notify executives.',
  },
  {
    id: 'assistant',
    route: '/assistant',
    target: '[data-tour="assistant"]',
    title: 'Operations assistant',
    body:
      'A tool-using agent answers questions from inventory, production, sales and finance data. It never writes SQL: it calls a ' +
      'fixed set of read-only tools, filtered by your role and re-checked on every call. Try a suggestion, for example the ' +
      'items below reorder point.',
  },
  {
    id: 'reports',
    section: 'reports',
    route: '/reports',
    target: '[data-tour="generate"], [data-tour="report"]',
    title: 'Weekly management report',
    body:
      'Numbers are computed in code and the AI only writes the narrative, so figures cannot be invented. A report is generated ' +
      'every Monday; click Generate to create one now.',
  },
  {
    id: 'channels',
    section: 'intake',
    route: '/intake',
    target: '[data-tour="channels"]',
    title: 'Many ways in, one pipeline',
    body:
      'Complaints arrive through the website form, an email webhook, .eml uploads or the simulator, and all of them share the ' +
      'same queue and agents. Try Simulate and watch new complaints get triaged live.',
  },
  {
    id: 'finish',
    route: '/',
    title: 'That is the tour',
    body:
      'Under the hood: FastAPI, a background job queue, NVIDIA Nemotron behind a provider-agnostic wrapper, RAG over policy ' +
      'documents, audit logging, rate limits and automated tests. Architecture notes and source are in the README on GitHub. ' +
      'You can restart this tour anytime from the top bar.',
  },
]

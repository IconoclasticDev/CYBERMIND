export type Severity = 'High' | 'Medium' | 'Low';

export interface NetworkNode {
  id: string;
  name: string;
  ip: string;
  type: 'internet' | 'firewall' | 'web-server' | 'app-server' | 'db-server' | 'file-server' | 'workstation' | 'domain-controller';
  status: 'compromised' | 'high-risk' | 'medium-risk' | 'normal';
  x: number;
  y: number;
  role: string;
  os: string;
  openPorts: number[];
  threatScore: number;
  activeAlerts: string[];
  lastActivity: string;
  mac: string;
  zone: string;
}

export interface NetworkLink {
  id: string;
  source: string;
  target: string;
  type: 'traffic' | 'suspicious';
  protocol: string;
  port?: number;
  label?: string;
  animated?: boolean;
}

export interface LiveEvent {
  id: string;
  time: string;
  source: string;
  event: string;
  severity: Severity;
  destination?: string;
  protocol?: string;
  pid?: number;
  process?: string;
  commandLine?: string;
  mitreTactic?: string;
  user?: string;
  details?: string;
}

export interface RecentEvent {
  id: string;
  time: string;
  event: string;
  sourceDestination: string;
  severity: Severity;
  details?: string;
}

export interface AttackMilestone {
  id: string;
  time: string;
  stage: string;
  detail: string;
  status: 'completed' | 'current' | 'predicted';
  color: string;
  description: string;
  iocs: string[];
  mitreId: string;
}

export interface MitreTechnique {
  id: string;
  name: string;
  tactic: string;
  description: string;
  detection: string;
  mitigation: string;
  severity: Severity;
}

export type SidebarTab =
  | 'command-center'
  | 'live-monitor'
  | 'threat-forecast'
  | 'attack-graph'
  | 'scenario-lab'
  | 'replay-analysis'
  | 'reports'
  | 'knowledge-base'
  | 'settings';

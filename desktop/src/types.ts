export type Owner = {
  username: string;
  mfa_enabled: boolean;
};

export type PublicConfig = {
  version: string;
  rustdesk_server: string;
};

export type Device = {
  id: string;
  rustdesk_id: string;
  alias: string;
  hostname: string;
  platform: string;
  architecture: string;
  tags: string[];
  online: boolean;
  last_seen: string | null;
  rustdesk_version?: string;
  credential_rotation_pending?: boolean;
};

export type Stats = {
  total_devices: number;
  online_devices: number;
  offline_devices: number;
  revoked_devices: number;
};

export type AuditEvent = {
  id: string;
  action: string;
  actor_type: string;
  created_at: string;
};

export type Dashboard = {
  owner: Owner;
  config: PublicConfig;
  devices: Device[];
  stats: Stats;
  audit: AuditEvent[];
};

export type WorkstationStatus = {
  mode: "integrated" | "remote";
  deskflow_unit: string;
  deskflow: string;
  rustdesk: string;
};

export type EnrollmentToken = {
  token: string;
  expires_at: string;
};

export type MfaSetup = {
  secret: string;
  provisioning_uri: string;
};

export type MfaEnable = {
  recovery_codes: string[];
};

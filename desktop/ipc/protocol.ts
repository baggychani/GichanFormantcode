/**
 * GichanFormant sidecar IPC contract.
 * Keep in sync with `core/ipc/protocol.py` (enforced by tests/test_ipc_contract.py).
 */

export const PROTOCOL_VERSION = 1 as const;
export const MAX_MESSAGE_BYTES = 32 * 1024 * 1024;

import { COMMAND_SPECS } from "./command-specs";

export type CommandName = keyof typeof COMMAND_SPECS;
export const COMMANDS = Object.keys(COMMAND_SPECS) as CommandName[];

export const EVENTS = [
  "state_changed",
  "files_changed",
  "operation_progress",
  "project_saved",
  "project_loaded",
  "preview_ready",
  "preview_cleared",
  "preview_failed",
  "window_requested",
  "operation_failed",
  "sidecar_ready",
  "sidecar_shutting_down",
] as const;

export type EventName = (typeof EVENTS)[number];

export type AnalysisSettings = {
  type: string;
  f1_scale: string;
  f2_scale: string;
  origin: string;
  use_bark_units: boolean;
  outlier_mode: string | null;
  outlier_scope: string | null;
  normalization: string | null;
};

export type SourceInfo = {
  index: number;
  name: string;
  path: string | null;
  has_f3: boolean;
  is_combined: boolean;
  is_pre_lobanov: boolean;
};

export type ApplicationState = {
  analysis: AnalysisSettings;
  current_index: number;
  sources: SourceInfo[];
  capabilities: {
    can_plot: boolean;
    can_compare: boolean;
    can_save_project: boolean;
  };
};

export type ApplicationError = {
  code: string;
  message: string;
  details: Record<string, unknown>;
};

export type HealthStatus = {
  ok: boolean;
  pid: number;
  uptime_ms: number;
  version: string;
  protocol_version: number;
  headless: boolean;
  commands: string[];
};

export type IpcRequest = {
  v: typeof PROTOCOL_VERSION;
  id: string;
  method: CommandName;
  params: Record<string, unknown>;
};

export type IpcResponse = {
  v: typeof PROTOCOL_VERSION;
  id: string;
  result: unknown;
};

export type IpcErrorMessage = {
  v: typeof PROTOCOL_VERSION;
  id?: string;
  error: ApplicationError;
};

export type IpcEventMessage = {
  v: typeof PROTOCOL_VERSION;
  event: EventName;
  payload: Record<string, unknown>;
};

export type IpcMessage = IpcRequest | IpcResponse | IpcErrorMessage | IpcEventMessage;

type ParamToken = "object" | "string" | "string|null" | "int" | "string[]" | "int[][]";
type ParamValue<Token extends ParamToken> = Token extends "object"
  ? Record<string, unknown>
  : Token extends "string"
    ? string
    : Token extends "string|null"
      ? string | null
      : Token extends "int"
        ? number
        : Token extends "string[]"
          ? string[]
          : Token extends "int[][]"
            ? number[][]
            : never;

type CommandSpec = {
  readonly params: Readonly<Record<string, ParamToken>>;
  readonly required?: readonly string[];
};

type RequiredKeys<Spec extends CommandSpec> = Spec["required"] extends readonly (
  infer Key
)[]
  ? Extract<Key, keyof Spec["params"]>
  : never;

type ParamsFor<Spec extends CommandSpec> = keyof Spec["params"] extends never
  ? Record<string, never>
  : {
      [Key in RequiredKeys<Spec>]: ParamValue<Spec["params"][Key]>;
    } & {
      [Key in Exclude<keyof Spec["params"], RequiredKeys<Spec>>]?: ParamValue<
        Spec["params"][Key]
      >;
    };

export type CommandParams = {
  [Method in CommandName]: ParamsFor<(typeof COMMAND_SPECS)[Method]>;
};

import { invoke } from "@tauri-apps/api/core";
import type { CommandName, CommandParams } from "../ipc/protocol";

/** Single typed boundary for all renderer → sidecar requests. */
export function callSidecar<Result = unknown, Method extends CommandName = CommandName>(
  method: Method,
  params?: CommandParams[Method],
): Promise<Result> {
  return invoke<Result>("sidecar_call", {
    method,
    params: (params ?? {}) as Record<string, unknown>,
  });
}
